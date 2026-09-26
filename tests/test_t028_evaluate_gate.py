"""T028 — MCP evaluate gate: gate evaluations, capped blend, rating provenance.

Every acceptance criterion in ``tasks/TASK_GUIDE_T028.md`` has at least one
test here. Unit tests build ratings through the real ``rate()`` so every
number is the declared arithmetic, never a hand-typed value.
"""

from __future__ import annotations

import asyncio
import json
import math
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from easy_verifier.core.findings import ValidationError
from easy_verifier.core.gate import (
    MAX_EVIDENCE_REFS_PER_GATE,
    apply_gate_evaluations,
    detect_evaluate_gates,
    gate_requests,
)
from easy_verifier.core.judge import (
    RATING_RULES,
    GatedRating,
    Rating,
    RatingAbstention,
    blend,
    rate,
    rate_overall,
    within_band,
)
from easy_verifier.core.metrics import WHOLE_SET, Metric, MetricAbstention, MetricSet
from easy_verifier.core.models import CoverageSummary, SourceMiss
from easy_verifier.core.report import write_report
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import dimension_names

DIMENSIONS = dimension_names()
REF = "README.md:1-3"


# ---------------------------------------------------------------------------
# fixtures built through the real rating arithmetic
# ---------------------------------------------------------------------------


def _far(name: str) -> float:
    """A value clearly outside the ±10% band of the rule's threshold."""
    rule = RATING_RULES[name]
    if rule.comparison == "at_least":
        return rule.threshold + 10
    return rule.threshold + 5  # fails an at_most-0 rule, far from 0


def _rating(dimension: str, values: dict[str, object] | None = None):
    values = values or {}
    metrics = tuple(
        Metric(
            name=name,
            family="fixture",
            kind=WHOLE_SET,
            dimension=dimension,
            outcome=values.get(name, _far(name)),
            computed_from=("src/app.py",)
            if not isinstance(values.get(name), MetricAbstention)
            else (),
            derivation="fixture",
        )
        for name in RATING_RULES
    )
    coverage = CoverageSummary(
        per_dimension=((dimension, 1.0),),
        combined=1.0,
        method="fixture",
        misses=((dimension, ()),),
    )
    return rate(MetricSet(metrics), coverage)


def _abstention(dimension: str) -> RatingAbstention:
    return RatingAbstention(
        dimension=dimension,
        reason_code="below_coverage_floor",
        coverage_floor=_floor(dimension),
        achieved_coverage=0.0,
        sources_missing=(SourceMiss("ARCHITECTURE.md", "not found in target"),),
    )


def _floor(dimension: str) -> float:
    from easy_verifier.core.judge import COVERAGE_FLOORS

    return COVERAGE_FLOORS[dimension].value


def _rating_68(dimension: str) -> Rating:
    """R = round(100 * 65 / 95) = 68: one 5-weight metric unavailable."""
    failing = {
        "excerpts_observed": 0,
        "declared_source_coverage": 0.1,
        "evidence_lines_observed": 0,
        "source_file_share": 0.0,
    }
    passing = {
        "test_to_source_ratio": 5.0,
        "source_files_without_covering_test": 0,
        "assertion_density_per_test": 5.0,
        "assertions_observed": 1,  # exactly on threshold 1.0 → borderline
        "redaction_hits_observed": 0,
        "redacted_file_share": 0.0,
    }
    rating = _rating(
        dimension,
        {
            **failing,
            **passing,
            "mean_excerpt_lines": MetricAbstention("no excerpts"),
        },
    )
    assert type(rating) is Rating and rating.value == 68
    return rating


def _packs(refs: tuple[str, ...] = (REF,), truncated: bool = False) -> dict:
    pack = SimpleNamespace(
        excerpts=tuple(SimpleNamespace(ref=ref) for ref in refs), truncated=truncated
    )
    return {name: pack for name in DIMENSIONS}


def _ratings(**overrides) -> tuple:
    """Seven results, canonical order: rated far from any threshold unless
    overridden (at_most-0 rules fail at 5, so none sit exactly on 0)."""
    return tuple(overrides.get(name) or _rating(name) for name in DIMENSIONS)


def _ev(score=88, confidence=0.6, refs=(REF,), **extra) -> dict:
    return {
        "score": score,
        "confidence": confidence,
        "evidence_refs": list(refs),
        **extra,
    }


# ---------------------------------------------------------------------------
# AC1 — gate detection, band edges
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "threshold", "expected"),
    [
        (1.099, 1.0, True),  # 9.9%
        (1.1, 1.0, True),  # 10% — inclusive
        (1.101, 1.0, False),  # 10.1%
        (0.901, 1.0, True),
        (0.9, 1.0, True),
        (0.899, 1.0, False),
        (0.66, 0.60, True),
        (0.6606, 0.60, False),
        (0, 0.0, False),  # threshold 0 → never borderline (Stage 4)
        (0.0, 0, False),
        (0.0001, 0.0, False),
        (-0.0001, 0.0, False),
    ],
)
def test_borderline_band_edges(value, threshold, expected) -> None:
    assert within_band(value, threshold) is expected


def test_detect_gates_abstained_and_borderline_only() -> None:
    borderline = _rating("code-quality", {"test_to_source_ratio": 1.05})
    ratings = _ratings(
        architecture=_abstention("architecture"), **{"code-quality": borderline}
    )
    gates = detect_evaluate_gates(ratings)
    assert gates == {
        "architecture": "abstained",
        "code-quality": "borderline: test_to_source_ratio",
    }


def test_detect_gates_names_every_borderline_metric() -> None:
    rating = _rating(
        "security", {"test_to_source_ratio": 0.95, "assertion_density_per_test": 1.08}
    )
    gates = detect_evaluate_gates(_ratings(security=rating))
    assert gates == {
        "security": "borderline: test_to_source_ratio, assertion_density_per_test"
    }


def test_threshold_zero_rules_at_zero_never_gate() -> None:
    """Stage 4 decision: every at_most-0 rule at its best value (0) is not
    borderline, so a dimension clean on them is not asked about."""
    zeros = {name: 0 for name, rule in RATING_RULES.items() if rule.threshold == 0}
    assert zeros  # the at_most-0 rules exist, so this pins something
    assert detect_evaluate_gates(_ratings(security=_rating("security", zeros))) == {}


# ---------------------------------------------------------------------------
# AC4 — blend arithmetic (Decimal, ROUND_HALF_UP, clamp)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rules", "agent", "confidence", "final", "weight"),
    [
        (68, 88, 0.6, 74, Decimal("0.30")),
        (50, 51, 1, 51, Decimal("0.5")),  # 50.5 → 51, not banker's 50
        (68, 0, 0, 68, Decimal("0")),  # c = 0 → final = R
        (100, 100, 1, 100, Decimal("0.5")),
        (0, 0, 1, 0, Decimal("0.5")),
        (10, 100, 0.5, 33, Decimal("0.25")),  # 32.5 → 33
    ],
)
def test_blend_worked_cases(rules, agent, confidence, final, weight) -> None:
    value, w = blend(rules, agent, confidence)
    assert value == final
    assert w == weight


# ---------------------------------------------------------------------------
# AC3/AC8 — validation of untrusted gate evaluations
# ---------------------------------------------------------------------------


def _reject(document, ratings=None, packs=None) -> str:
    ratings = ratings or _ratings(architecture=_abstention("architecture"))
    with pytest.raises(ValidationError) as caught:
        apply_gate_evaluations(document, ratings, packs or _packs())
    return str(caught.value)


@pytest.mark.parametrize(
    ("entry", "named"),
    [
        (_ev(score=101), "gate_evaluations.architecture.score"),
        (_ev(score=-1), "gate_evaluations.architecture.score"),
        (_ev(score="88"), "gate_evaluations.architecture.score"),
        (_ev(score=True), "gate_evaluations.architecture.score"),
        (_ev(score=math.nan), "gate_evaluations.architecture.score"),
        (_ev(score=math.inf), "gate_evaluations.architecture.score"),
        (_ev(score=None), "gate_evaluations.architecture.score"),
        (_ev(confidence=1.01), "gate_evaluations.architecture.confidence"),
        (_ev(confidence=-0.1), "gate_evaluations.architecture.confidence"),
        (_ev(confidence=False), "gate_evaluations.architecture.confidence"),
        (_ev(confidence=math.nan), "gate_evaluations.architecture.confidence"),
        (_ev(confidence="high"), "gate_evaluations.architecture.confidence"),
        (_ev(refs=()), "gate_evaluations.architecture.evidence_refs"),
        (_ev(refs=(1,)), "gate_evaluations.architecture.evidence_refs"),
        (_ev(refs=("src/nope.py:1-2",)), "src/nope.py:1-2"),
        (_ev(verdict="x"), "gate_evaluations.architecture.verdict"),
        ({"score": 1, "confidence": 1}, "gate_evaluations.architecture.evidence_refs"),
        ("not an object", "gate_evaluations.architecture"),
        (_ev(rationale=7), "gate_evaluations.architecture.rationale"),
    ],
)
def test_invalid_evaluation_is_rejected_naming_the_field(entry, named) -> None:
    assert named in _reject({"architecture": entry})


def test_unknown_ref_names_the_ref_and_truncation() -> None:
    message = _reject(
        {"architecture": _ev(refs=("src/gone.py:1-9",))}, packs=_packs(truncated=True)
    )
    assert "src/gone.py:1-9" in message and "truncated" in message


def test_evaluation_for_ungated_dimension_is_rejected_naming_it() -> None:
    message = _reject({"architecture": _ev()}, ratings=_ratings())
    assert "gate_evaluations.architecture" in message
    assert "not at a hard gate" in message


def test_unknown_dimension_is_rejected() -> None:
    message = _reject({"vibes": _ev()})
    assert "gate_evaluations.vibes" in message and "unknown dimension" in message


def test_gate_evaluations_must_be_an_object() -> None:
    assert "gate_evaluations" in _reject([_ev()])


def test_too_many_refs_is_one_named_error() -> None:
    refs = tuple(f"bogus{i}.py:1-2" for i in range(100_000))
    message = _reject({"architecture": _ev(refs=refs)})
    assert "gate_evaluations.architecture.evidence_refs: 100000 refs" in message
    assert "bogus" not in message
    assert len(message) < 500


def test_error_lines_are_bounded() -> None:
    from easy_verifier.core.roles import MAX_ERROR_LINES

    document = {f"dim{i}": _ev() for i in range(MAX_ERROR_LINES + 30)}
    with pytest.raises(ValidationError) as caught:
        apply_gate_evaluations(
            document, _ratings(architecture=_abstention("architecture")), _packs()
        )
    assert len(caught.value.errors) == MAX_ERROR_LINES + 1
    assert caught.value.errors[-1] == "…and 30 more"
    assert "dim49" not in str(caught.value)


def test_every_error_is_reported_at_once() -> None:
    message = _reject({"architecture": _ev(score=500, confidence=9), "security": _ev()})
    assert "architecture.score" in message
    assert "architecture.confidence" in message
    assert "gate_evaluations.security" in message


# ---------------------------------------------------------------------------
# AC4/AC5/AC6 — applying a valid evaluation
# ---------------------------------------------------------------------------


def test_blended_rating_shows_its_parts() -> None:
    rules = _rating_68("code-quality")
    ratings = _ratings(**{"code-quality": rules})
    applied = apply_gate_evaluations(
        {"code-quality": _ev(88, 0.6, rationale="secret reasoning")},
        ratings,
        _packs(),
    )
    gated = applied[DIMENSIONS.index("code-quality")]
    assert type(gated) is GatedRating
    assert gated.value == 74
    assert gated.parts == "74 = rules 68 + agent 88 (w 0.30)"
    payload = gated.to_dict()
    assert payload["kind"] == "blended_rating"
    assert payload["value"] == 74
    assert payload["parts"] == "74 = rules 68 + agent 88 (w 0.30)"
    assert payload["rated_by"] == "blended (w 0.30)"
    assert payload["agent"]["weight"] == "0.30"
    assert payload["rules"] == rules.to_dict()
    assert "secret reasoning" not in json.dumps(payload)
    # every other dimension is untouched (AC8)
    for index, name in enumerate(DIMENSIONS):
        if name != "code-quality":
            assert applied[index] is ratings[index]


def test_agent_rated_keeps_abstention_record() -> None:
    abstained = _abstention("security")
    ratings = _ratings(security=abstained)
    applied = apply_gate_evaluations({"security": _ev(70, 0.8)}, ratings, _packs())
    gated = applied[DIMENSIONS.index("security")]
    assert gated.value == 70
    assert gated.rated_by == "agent-rated"
    payload = gated.to_dict()
    assert payload["kind"] == "agent_rated"
    assert payload["agent"]["weight"] is None
    assert payload["rules"] == abstained.to_dict()
    assert payload["rules"]["coverage_floor"] == abstained.coverage_floor
    assert payload["rules"]["sources_missing"]
    assert "70 = agent 70" in payload["parts"]
    assert "below_coverage_floor" in payload["parts"]


def test_agent_rated_score_rounds_half_up() -> None:
    applied = apply_gate_evaluations(
        {"security": _ev(70.5, 1)}, _ratings(security=_abstention("security")), _packs()
    )
    assert applied[DIMENSIONS.index("security")].value == 71


def test_overall_discloses_each_rating_kind() -> None:
    ratings = _ratings(
        architecture=_abstention("architecture"),
        security=_abstention("security"),
        **{"code-quality": _rating_68("code-quality")},
    )
    applied = apply_gate_evaluations(
        {"security": _ev(70, 0.8), "code-quality": _ev(88, 0.6)}, ratings, _packs()
    )
    overall = rate_overall(applied)
    assert overall.contributor_count == 6
    assert "security" in overall.contributors
    assert "architecture" not in overall.contributors
    assert "(4 rule-rated, 1 blended, 1 agent-rated)" in overall.disclosure
    assert "abstained: architecture (below_coverage_floor" in overall.disclosure
    assert dict(overall.contributor_values)["code-quality"] == 74
    assert dict(overall.rated_by) == {
        **{name: "rules" for name in overall.contributors},
        "code-quality": "blended (w 0.30)",
        "security": "agent-rated",
    }
    assert overall.to_dict()["rated_by"]


def test_overall_never_averages_abstained_dimension_without_evaluation() -> None:
    ratings = _ratings(architecture=_abstention("architecture"))
    overall = rate_overall(ratings)
    assert "architecture" not in overall.contributors
    assert "(6 rule-rated, 0 blended, 0 agent-rated)" in overall.disclosure


def test_ratings_without_agent_input_equal_ratings_with_empty_evaluations() -> None:
    """AC8 property: for every ungated dimension, agent input changes nothing."""
    ratings = _ratings(
        architecture=_abstention("architecture"),
        **{"code-quality": _rating_68("code-quality")},
    )
    applied = apply_gate_evaluations({"architecture": _ev(1, 1)}, ratings, _packs())
    gates = detect_evaluate_gates(ratings)
    for index, name in enumerate(DIMENSIONS):
        if name not in gates or name == "code-quality":
            assert applied[index] is ratings[index], name


# ---------------------------------------------------------------------------
# AC2 — gate requests are compact: refs only, capped, omitted counted
# ---------------------------------------------------------------------------


def test_gate_requests_cap_refs_and_count_omitted() -> None:
    refs = tuple(f"src/f{i}.py:1-2" for i in range(MAX_EVIDENCE_REFS_PER_GATE + 5))
    requests = gate_requests({"architecture": "abstained"}, _packs(refs))
    assert requests == [
        {
            "dimension": "architecture",
            "reason": "abstained",
            "evidence_refs": list(refs[:MAX_EVIDENCE_REFS_PER_GATE]),
            "omitted": 5,
        }
    ]


def test_gate_requests_skip_a_dimension_with_nothing_to_cite() -> None:
    packs = _packs()
    packs["architecture"] = None
    assert gate_requests({"architecture": "abstained"}, packs) is None


# ---------------------------------------------------------------------------
# integration: score_repository rounds (AC2, AC5, AC7, AC8, AC9)
# ---------------------------------------------------------------------------


def _repo(root: Path) -> Path:
    files = {
        "README.md": "# Demo\n\nA tiny service.\n",
        "src/app.py": "def add(a, b):\n    return a + b\n",
        "tests/test_app.py": "from app import add\n\n"
        "def test_add():\n    assert add(1, 2) == 3\n",
        "pyproject.toml": "[project]\nname = 'demo'\n",
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _first_round(repo: Path):
    first = score_repository(
        repo, scope="worktree", agent_input={"picks": {}}, detect_gates=True
    )
    assert first.needs_input is None
    assert first.gate_requests
    return first


def test_score_emits_gate_requests_and_applies_evaluations(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first = _first_round(repo)
    request = first.gate_requests[0]
    assert request["reason"] == "abstained" or request["reason"].startswith(
        "borderline: "
    )
    assert request["evidence_refs"]
    assert all(type(ref) is str for ref in request["evidence_refs"])

    abstained = next(r for r in first.gate_requests if r["reason"] == "abstained")
    dimension = abstained["dimension"]
    second = score_repository(
        repo,
        scope="worktree",
        agent_input={
            "picks": {},
            "gate_evaluations": {
                dimension: _ev(70, 0.8, abstained["evidence_refs"][:1], rationale="r")
            },
        },
        detect_gates=True,
    )
    assert second.needs_input is None and second.gate_requests is None
    payload = second.to_dict()
    rated = next(r for r in payload["ratings"] if r["dimension"] == dimension)
    assert rated["kind"] == "agent_rated" and rated["value"] == 70
    assert "1 agent-rated" in payload["overall"]["disclosure"]
    provenance = {p["dimension"]: p["rating"] for p in payload["provenance"]}
    assert provenance[dimension] == "agent-rated"
    assert '"r"' not in second.serialize()
    # AC8: every other dimension equals the first round's number exactly
    before = {r["dimension"]: r for r in first.to_dict()["ratings"]}
    for item in payload["ratings"]:
        if item["dimension"] != dimension:
            assert item == before[item["dimension"]]


def test_picks_are_asked_before_gates(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "notes").mkdir()
    (repo / "notes/product-brief.md").write_text("# Brief\n", encoding="utf-8")
    first = score_repository(repo, scope="worktree", detect_gates=True)
    assert first.needs_input is not None
    assert first.gate_requests is None
    second = score_repository(
        repo, scope="worktree", agent_input={"picks": {}}, detect_gates=True
    )
    assert second.needs_input is None and second.gate_requests


def test_first_call_asks_gates_when_no_picks_pending(
    tmp_path: Path, monkeypatch
) -> None:
    import easy_verifier.core.score as score_module

    monkeypatch.setattr(score_module, "detect_pick_gates", lambda *a, **k: None)
    first = score_repository(_repo(tmp_path), scope="worktree", detect_gates=True)
    assert first.needs_input is None and first.gate_requests


def test_cli_path_never_computes_gate_requests(tmp_path: Path) -> None:
    result = score_repository(_repo(tmp_path), scope="worktree")
    assert result.gate_requests is None
    assert "needs_input" not in result.serialize()


def test_evaluation_for_ungated_dimension_rejected_end_to_end(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first = _first_round(repo)
    gated = {r["dimension"] for r in first.gate_requests}
    ungated = next(name for name in DIMENSIONS if name not in gated)
    with pytest.raises(ValidationError) as caught:
        score_repository(
            repo,
            scope="worktree",
            agent_input={"gate_evaluations": {ungated: _ev(1, 1, ("README.md:1-3",))}},
        )
    assert f"gate_evaluations.{ungated}" in str(caught.value)


def test_findings_assessments_stay_unblended(tmp_path: Path) -> None:
    """AC9/FR-029a: divergence compares the finding assessment with the
    rules rating; the gate evaluation never enters an assessment."""
    repo = _repo(tmp_path)
    first = _first_round(repo)
    request = first.gate_requests[0]
    dimension, ref = request["dimension"], request["evidence_refs"][0]
    findings = [
        {
            "dimension": dimension,
            "title": "t",
            "detail": "d",
            "evidence_ref": ref,
            "confidence": "high",
        }
    ]
    plain = score_repository(
        repo, scope="worktree", findings=findings, agent_input={"picks": {}}
    )
    gated = score_repository(
        repo,
        scope="worktree",
        findings=findings,
        agent_input={"gate_evaluations": {dimension: _ev(5, 1, (ref,))}},
    )
    assert plain.to_dict()["assessments"] == gated.to_dict()["assessments"]
    assert plain.to_dict()["divergences"] == gated.to_dict()["divergences"]


# ---------------------------------------------------------------------------
# adapters: MCP wire shape (AC2), CLI replay parity (AC10), HTML parts (AC6)
# ---------------------------------------------------------------------------


def _mcp(arguments: dict) -> dict:
    from easy_verifier.adapters import mcp_server

    _content, result = asyncio.run(mcp_server.mcp.call_tool("score", arguments))
    return result


def test_mcp_score_emits_needs_input_gate_evaluations(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    payload = _mcp(
        {"repo": str(repo), "scope": "worktree", "agent_input": {"picks": {}}}
    )
    requests = payload["needs_input"]["gate_evaluations"]
    assert "picks" not in payload["needs_input"]
    assert set(requests[0]) == {"dimension", "reason", "evidence_refs", "omitted"}


def test_mcp_call_carrying_evaluations_emits_no_needs_input(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    request = _first_round(repo).gate_requests[0]
    payload = _mcp(
        {
            "repo": str(repo),
            "scope": "worktree",
            "agent_input": {
                "gate_evaluations": {
                    request["dimension"]: _ev(70, 0.8, request["evidence_refs"][:1])
                }
            },
        }
    )
    assert "needs_input" not in payload


def test_score_tool_description_explains_gate_evaluations() -> None:
    from easy_verifier.adapters import mcp_server

    tool = mcp_server.mcp._tool_manager.get_tool("score")
    assert "gate_evaluations" in tool.description
    assert "0.5" in tool.description


def test_cli_replays_picks_and_evaluations_byte_equal_to_mcp(tmp_path: Path) -> None:
    import subprocess
    import sys

    repo = _repo(tmp_path / "repo")
    request = _first_round(repo).gate_requests[0]
    agent_input = {
        "picks": {"requirements-doc": ["README.md"]},
        "gate_evaluations": {
            request["dimension"]: _ev(70, 0.8, request["evidence_refs"][:1])
        },
    }
    # the evaluation must still be for a gated dimension once picks apply
    after_picks = score_repository(
        repo,
        scope="worktree",
        agent_input={"picks": agent_input["picks"]},
        detect_gates=True,
    )
    gated = {r["dimension"]: r for r in after_picks.gate_requests}
    dimension = next(iter(gated))
    agent_input["gate_evaluations"] = {
        dimension: _ev(70, 0.8, gated[dimension]["evidence_refs"][:1])
    }
    document = tmp_path / "agent-input.json"
    document.write_text(json.dumps(agent_input), encoding="utf-8")
    src = Path(__file__).resolve().parents[1] / "src"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "score",
            "--repo",
            str(repo),
            "--scope",
            "worktree",
            "--agent-input",
            str(document),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(src), "PATH": "/usr/bin:/bin"},
    )
    assert completed.returncode == 0, completed.stderr
    cli_payload = json.loads(completed.stdout)
    mcp_payload = _mcp(
        {"repo": str(repo), "scope": "worktree", "agent_input": agent_input}
    )
    assert json.dumps(cli_payload, sort_keys=True) == json.dumps(
        mcp_payload, sort_keys=True
    )
    assert any(
        r["kind"] in {"blended_rating", "agent_rated"} for r in cli_payload["ratings"]
    )


def test_report_renders_parts_and_never_rationale(tmp_path: Path) -> None:
    from easy_verifier.core.synthesis import combined_pack

    repo = _repo(tmp_path)
    request = _first_round(repo).gate_requests[0]
    agent_input = {
        "gate_evaluations": {
            request["dimension"]: _ev(
                70, 0.8, request["evidence_refs"][:1], rationale="PRIVATE-RATIONALE"
            )
        }
    }
    packs = combined_pack(
        DIMENSIONS, repo_path=repo, scope="worktree", agent_input=agent_input
    )
    result = write_report([], packs, repo, agent_input=agent_input)
    document = (repo / result.path).read_text(encoding="utf-8")
    assert "PRIVATE-RATIONALE" not in document
    assert "Rating 70 = agent 70 (confidence 0.8; rules abstained: " in document
    assert "Rules rating withheld" in document
    assert "rule-rated" in document
