"""T047 - optional packs (DDR-0008 §4, FR-053) and the healthcare pack
(areas #9 and #28, FR-052).

AC1 a pack is active only when ``.easy-verifier.toml`` lists it or the
agent picks it (``agent_input.packs``); nothing else activates it. AC2 the
healthcare rules: PHI-shaped values (SSN / MRN / DOB) in test data and in log
statements count against #9 (HIPAA §164.514 cited, documented placeholders
excluded, matched values never echoed); retention, BAA, data classification
and residency are documentation rules. AC3 an inactive pack contributes
nothing: no slot, no metric, no area, no warning (the T068 under-cap snapshot
stays byte-identical). AC4 pack results carry their area labels and the
overall disclosure names the active pack.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    COVERAGE_FLOORS,
    DOCUMENTATION_RULES,
    PACK_FLOORS,
    RATING_RULES,
    areas_without_rule,
)
from easy_verifier.core.models import to_json_dict
from easy_verifier.core.registry import PACK_FIELDS, load_pack
from easy_verifier.core.roles import RoleInputError, active_packs, load_repo_packs
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import PACKS, dimension_names

# Assembled at runtime: no realistic identifier is committed as a literal.
SSN = "-".join(("512", "44", "8812"))
DOB = "-".join(("1984", "07", "23"))
MRN = "".join(("48", "1297", "3"))
TEST_DATA = "phi_values_in_test_data_observed"
LOGS = "phi_values_in_log_statements_observed"
PHI_AREA = AREAS[8]
VENDOR_AREA = AREAS[27]


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _repo(tmp_path: Path, *, config: str | None, ssn: str = SSN) -> Path:
    files = {
        "README.md": "# Clinic\n\nA small service.\n",
        "src/app.py": (
            "import logging\n\nlog = logging.getLogger(__name__)\n\n\n"
            "def admit(patient):\n    log.info('admitted %s', patient.id)\n"
            "    return patient\n"
        ),
        "tests/test_app.py": "def test_admit():\n    assert True\n",
        "tests/fixtures/patient.json": f'{{"name": "Jane", "ssn": "{ssn}"}}\n',
    }
    if config is not None:
        files[".easy-verifier.toml"] = config
    return _write(tmp_path / "repo", files)


def _rating(result, name: str) -> dict:
    return next(r for r in result.to_dict()["ratings"] if r["dimension"] == name)


def _metric(result, name: str) -> dict:
    return next(
        m
        for m in result.to_dict()["metrics"]["metrics"]
        if m["dimension"] == "healthcare" and m["name"] == name
    )


# ---------------------------------------------------------------------------
# AC1 activation


def test_config_packs_key_activates_and_is_shape_checked(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    assert load_repo_packs(repo) == ("healthcare",)
    (repo / ".easy-verifier.toml").write_text('packs = "healthcare"\n')
    with pytest.raises(RoleInputError, match="packs: must be a list"):
        load_repo_packs(repo)


def test_unknown_pack_is_a_note_and_ignored(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare", "dentistry"]\n')
    names, notes = active_packs(repo, None)
    assert names == ("healthcare",)
    assert len(notes) == 1 and "dentistry" in notes[0] and "healthcare" in notes[0]


def test_agent_pick_activates_without_config(tmp_path) -> None:
    repo = _repo(tmp_path, config=None)
    result = score_repository(
        repo, scope="project", agent_input={"packs": ["healthcare"]}
    )
    assert "healthcare" in [r["dimension"] for r in result.to_dict()["ratings"]]


def test_agent_pick_must_be_a_list_of_names(tmp_path) -> None:
    repo = _repo(tmp_path, config=None)
    with pytest.raises(RoleInputError, match="packs: must be a list"):
        score_repository(repo, scope="project", agent_input={"packs": "healthcare"})


def test_nothing_else_activates_a_pack(tmp_path) -> None:
    # A repository full of healthcare words, PHI and BAA documents: never guessed.
    repo = _repo(tmp_path, config=None)
    _write(repo, {"docs/BAA.md": "# Business associate agreement\n"})
    payload = score_repository(repo, scope="project").serialize()
    assert "healthcare" not in payload
    assert "phi_values" not in payload


def test_packs_are_not_dimensions(tmp_path) -> None:
    assert set(PACKS) == set(PACK_FLOORS) == {"healthcare"}
    assert not set(PACKS) & set(dimension_names())
    assert not set(PACK_FLOORS) & set(COVERAGE_FLOORS)
    with pytest.raises(ValueError, match="unknown dimension"):
        combined_pack(("healthcare",), repo_path=_repo(tmp_path, config=None))


# ---------------------------------------------------------------------------
# AC2 rules, citations, placeholders, redaction


def test_healthcare_rules_are_cited_and_labelled() -> None:
    rules = RATING_RULES["healthcare"]
    assert set(rules) == {TEST_DATA, LOGS}
    assert sum(rule.weight for rule in rules.values()) == 100
    for rule in rules.values():
        assert rule.area == PHI_AREA
        assert rule.comparison == "at_most" and rule.threshold == 0
        assert any("164.514" in c.label for c in rule.metric_citation)
    docs = DOCUMENTATION_RULES["healthcare"]
    assert [d.area for d in docs] == [PHI_AREA, VENDOR_AREA, VENDOR_AREA, VENDOR_AREA]
    assert PACK_FLOORS["healthcare"].value == 0.25


def test_pack_patterns_live_in_the_registry_with_citations() -> None:
    entry = load_pack("healthcare")
    assert set(entry.fields) == set(PACK_FIELDS["healthcare"])
    for items in entry.fields.values():
        for item in items:
            assert item.citation_url.startswith("https://")
            assert item.source_tag == "curated"
    kinds = {v.split("=", 1)[0] for c in entry.fields["phi_values"] for v in c.value}
    assert kinds == {"ssn", "mrn", "dob"}
    source = Path("src/easy_verifier/packs/healthcare.py").read_text(encoding="utf-8")
    assert r"\d{3}" not in source and "ssn=" not in source


def test_ssn_in_fixture_fails_the_rule_cited_and_redacted(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    result = score_repository(repo, scope="project")
    metric = _metric(result, TEST_DATA)
    assert metric["outcome"] == {"abstained": False, "value": 1}
    assert "tests/fixtures/patient.json:1 (ssn)" in metric["derivation"]
    rating = _rating(result, "healthcare")
    entry = next(i for i in rating["inputs"] if i["metric_name"] == TEST_DATA)
    assert entry["passed"] is False and entry["area"] == PHI_AREA
    assert any("164.514" in c["label"] for c in entry["metric_citation"])
    assert SSN not in result.serialize()


def test_pack_excerpts_mask_the_value(tmp_path) -> None:
    repo = _repo(tmp_path, config=None)
    packs = combined_pack(
        (*dimension_names(), "healthcare"),
        repo_path=repo,
        scope="project",
        packs=("healthcare",),
    )
    slot = next(s for s in packs.slots if s.dimension == "healthcare")
    text = json.dumps(to_json_dict(slot.pack))
    assert SSN not in text
    assert "[PHI ssn redacted" in text


@pytest.mark.parametrize(
    "value", ["000-00-0000", "123-45-6789", "111-11-1111", "666-12-3456", "912-34-5678"]
)
def test_documented_placeholders_do_not_count(tmp_path, value) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n', ssn=value)
    assert _metric(score_repository(repo, scope="project"), TEST_DATA)["outcome"] == {
        "abstained": False,
        "value": 0,
    }


def test_phi_in_a_log_statement_counts(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    _write(
        repo,
        {
            "src/audit.py": (
                "import logging\n\n\ndef audit():\n"
                f"    logging.info('dob={DOB} mrn: {MRN}')\n"
                "    logging.info('dob=1900-01-01')\n"
            )
        },
    )
    result = score_repository(repo, scope="project")
    metric = _metric(result, LOGS)
    assert metric["outcome"] == {"abstained": False, "value": 2}
    assert "src/audit.py:5 (dob)" in metric["derivation"]
    assert "src/audit.py:5 (mrn)" in metric["derivation"]
    assert DOB not in result.serialize() and MRN not in result.serialize()


def test_log_rule_abstains_without_a_log_statement(tmp_path) -> None:
    repo = _write(
        tmp_path / "r",
        {
            ".easy-verifier.toml": 'packs = ["healthcare"]\n',
            "src/app.py": "def f():\n    return 1\n",
            "tests/test_app.py": "def test_f():\n    assert True\n",
        },
    )
    result = score_repository(repo, scope="project")
    assert _metric(result, LOGS)["outcome"]["abstained"] is True
    assert _metric(result, TEST_DATA)["outcome"] == {"abstained": False, "value": 0}
    assert _rating(result, "healthcare")["kind"] == "rating"


def test_documentation_rules_report_present_or_missing(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    _write(repo, {"docs/BAA.md": "# Business associate agreement\n"})
    rating = _rating(score_repository(repo, scope="project"), "healthcare")
    docs = rating["documentation"]
    assert [d["area"] for d in docs] == [
        PHI_AREA,
        VENDOR_AREA,
        VENDOR_AREA,
        VENDOR_AREA,
    ]
    assert [d["status"] for d in docs] == ["missing", "present", "missing", "missing"]
    assert docs[1]["file"] == "docs/BAA.md"
    assert all("value" not in d and "weight" not in d for d in docs)


# ---------------------------------------------------------------------------
# AC3 inactive pack contributes nothing; AC4 areas and disclosure


def test_inactive_pack_leaves_no_trace_and_areas_stay_unruled(tmp_path) -> None:
    result = score_repository(_repo(tmp_path, config=None), scope="project")
    payload = result.to_dict()
    assert PHI_AREA in payload["areas_without_rule"]
    assert VENDOR_AREA in payload["areas_without_rule"]
    assert "healthcare" not in result.serialize()
    assert areas_without_rule() == tuple(payload["areas_without_rule"])


def test_active_pack_names_its_areas_and_the_disclosure(tmp_path) -> None:
    result = score_repository(
        _repo(tmp_path, config='packs = ["healthcare"]\n'), scope="project"
    )
    payload = result.to_dict()
    assert PHI_AREA not in payload["areas_without_rule"]
    assert VENDOR_AREA not in payload["areas_without_rule"]
    assert PHI_AREA in payload["areas_measured"]
    assert VENDOR_AREA in payload["areas_measured"]
    overall = payload["overall"]
    assert "packs active: healthcare" in overall["disclosure"]
    assert overall["total_dimension_count"] == len(COVERAGE_FLOORS) + 1
    assert [r["dimension"] for r in payload["ratings"]][-1] == "healthcare"


def test_replay_with_a_pack_is_byte_equal(tmp_path) -> None:
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    first = score_repository(repo, scope="project").serialize()
    assert score_repository(repo, scope="project").serialize() == first


def test_cli_score_with_config_pack(tmp_path) -> None:
    import subprocess
    import sys

    repo = _repo(tmp_path, config='packs = ["healthcare", "nope"]\n')
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "score",
            "--repo",
            str(repo),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert re.search(r"unknown pack.*nope", done.stderr)
    payload = json.loads(done.stdout)
    assert "healthcare" in [r["dimension"] for r in payload["ratings"]]
    assert SSN not in done.stdout


def test_report_renders_the_pack_card_and_disclosure(tmp_path) -> None:
    import subprocess
    import sys

    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    findings = tmp_path / "findings.json"
    findings.write_text("[]", encoding="utf-8")
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            "--repo",
            str(repo),
            "--findings",
            str(findings),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    html = (repo / json.loads(done.stdout)["path"]).read_text(encoding="utf-8")
    assert "packs active: healthcare" in html
    assert "phi_values_in_test_data_observed" in html
    assert PHI_AREA in html and VENDOR_AREA in html
    assert SSN not in html


def test_report_without_the_pack_has_no_pack_card(tmp_path) -> None:
    import subprocess
    import sys

    repo = _repo(tmp_path, config=None)
    findings = tmp_path / "findings.json"
    findings.write_text("[]", encoding="utf-8")
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            "--repo",
            str(repo),
            "--findings",
            str(findings),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    html = (repo / json.loads(done.stdout)["path"]).read_text(encoding="utf-8")
    assert "phi_values" not in html and "packs active" not in html


def test_class_held_logger_calls_count(tmp_path) -> None:
    # coffee-shop-api (2026-10-06): NestJS logs through this.logger.log(...);
    # missing it made the log rule abstain on a repository that has logging.
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    _write(
        repo,
        {
            "src/hook.ts": (
                "export class Hook {\n  run() {\n"
                f"    this.logger.log(`dob: {DOB}`);\n  }}\n}}\n"
            ),
            "src/svc.py": (
                f"class S:\n    def f(self):\n        self.logger.info('dob={DOB}')\n"
            ),
        },
    )
    metric = _metric(score_repository(repo, scope="project"), LOGS)
    assert metric["outcome"] == {"abstained": False, "value": 2}
    assert "src/hook.ts:3 (dob)" in metric["derivation"]
    assert "src/svc.py:3 (dob)" in metric["derivation"]


def test_cited_paths_are_redacted_like_files_read(tmp_path) -> None:
    # coffee-shop-api (2026-10-06): a migration name whose digits redact as a
    # secret made the metric cite a path the pack's files_read never held.
    repo = _repo(tmp_path, config='packs = ["healthcare"]\n')
    _write(
        repo,
        {
            "src/migrations/Migration20260824081651.ts": (
                "export class M {\n  up() {\n    console.log('up');\n  }\n}\n"
            )
        },
    )
    metric = _metric(score_repository(repo, scope="project"), LOGS)
    assert metric["outcome"] == {"abstained": False, "value": 0}
