"""T074: architecture from code + documents (DDR-0011, 20/80).

architecture = architecture_description_missing 10 + decision_records_missing 10
+ top_level_import_cycles 40 + layer_direction_violations 40. A missing document
is a failed rule; the layer rule abstains below a 0.50 classified share; the
coverage floor also counts source files with imports; a README "Architecture"
section is an architecture description; ``shared`` files never classify.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.judge import RATING_RULES
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import SAMPLED_METRICS, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.structure import layer_of
from easy_verifier.dimensions import architecture

REPO_ROOT = Path(__file__).resolve().parents[1]

LAYERED = {
    "src/app/controllers/user_controller.py": (
        "from app.services import user_service\n\n\ndef get():\n"
        "    return user_service.find()\n"
    ),
    "src/app/services/user_service.py": (
        "from app.repositories import user_repository\n\n\ndef find():\n"
        "    return user_repository.load()\n"
    ),
    "src/app/repositories/user_repository.py": (
        "import os\n\n\ndef load():\n    return os.sep\n"
    ),
}


def _repo(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    return root


def _metrics(root: Path, **kwargs):
    pack = run_dimension(architecture.DESCRIPTOR, root, "project", **kwargs)
    return pack, {m.name: m for m in compute_metrics(pack, curated_metric_tables())}


def _score(root: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", "score"]
        + ["--repo", str(root), "--scope", "project"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    return next(r for r in payload["ratings"] if r["dimension"] == "architecture")


def test_rules_and_weights_are_ddr_0011() -> None:
    rules = RATING_RULES["architecture"]
    assert {name: rule.weight for name, rule in rules.items()} == {
        "architecture_description_missing": 10,
        "decision_records_missing": 10,
        "top_level_import_cycles": 40,
        "layer_direction_violations": 40,
    }
    layer = rules["layer_direction_violations"]
    assert (layer.threshold, layer.comparison) == (0, "at_most")
    assert "Stable Dependencies" in layer.threshold_citation.label
    assert "42010" in rules["decision_records_missing"].threshold_citation.label
    assert "layer_direction_violations" in SAMPLED_METRICS["architecture"]


def test_a_repository_importing_a_service_is_one_cited_violation(
    tmp_path: Path,
) -> None:
    files = dict(LAYERED)
    files["src/app/repositories/user_repository.py"] = (
        "import os\nfrom app.services import user_service\n\n\ndef load():\n"
        "    return user_service\n"
    )
    _pack, metrics = _metrics(_repo(tmp_path, {"README.md": "# r\n", **files}))
    metric = metrics["layer_direction_violations"]
    assert metric.outcome == 1
    assert "src/app/repositories/user_repository.py:2" in metric.derivation
    assert "data -> service" in metric.derivation
    assert "3 of 3" in metric.derivation  # classified share
    assert any("user_repository.py" in ref for ref in metric.computed_from)


def test_no_docs_no_cycles_no_violations_rates_80(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"README.md": "# r\n\nAn app.\n", **LAYERED})
    _pack, metrics = _metrics(root)
    assert metrics["layer_direction_violations"].outcome == 0
    assert metrics["architecture_description_missing"].outcome == 1
    assert metrics["decision_records_missing"].outcome == 1
    rating = _score(root)
    assert rating["kind"] == "rating", rating  # AC5: code + README pass the floor
    assert rating["value"] == 80


def test_under_half_classified_abstains_and_rates_on_the_rest(tmp_path: Path) -> None:
    files = {
        "src/app/controllers/user_controller.py": "import os\n",
        "src/app/alpha.py": "import os\n",
        "src/app/beta.py": "import os\n",
        "src/app/gamma.py": "import os\n",
    }
    root = _repo(tmp_path, {"README.md": "# r\n", **files})
    _pack, metrics = _metrics(root)
    metric = metrics["layer_direction_violations"]
    assert metric.abstained
    assert "1 of 4" in metric.derivation
    rating = _score(root)
    assert rating["kind"] == "rating", rating
    assert rating["value"] == 67  # cycles 40 of 60 measured


def test_shared_files_leave_the_denominator_and_never_violate(tmp_path: Path) -> None:
    files = dict(LAYERED)
    files["src/app/utils/strings.py"] = "from app.services import user_service\n"
    files["src/app/repositories/user_repository.py"] = "from app.utils import strings\n"
    _pack, metrics = _metrics(_repo(tmp_path, {"README.md": "# r\n", **files}))
    metric = metrics["layer_direction_violations"]
    assert metric.outcome == 0
    assert "3 of 3" in metric.derivation


def test_readme_architecture_section_is_a_description(tmp_path: Path) -> None:
    # T089 (AC 7): the heading counts only when its section has the shape
    readme = (
        "# r\n\nIntro.\n\n## Architecture\n\n"
        "- src/app/controllers: HTTP entry points\n"
        "- src/app/services: business rules here\n"
        "- src/app/repositories: data access code\n"
    )
    _pack, metrics = _metrics(_repo(tmp_path, {"README.md": readme, **LAYERED}))
    assert _pack.coverage_score == 0.75
    metric = metrics["architecture_description_missing"]
    assert metric.outcome == 0
    assert "README.md (readme-heading" in metric.derivation
    assert any(ref.startswith("README.md") for ref in metric.computed_from)
    # Supervisor review: the section also fills the role for coverage.
    assert "architecture-doc" in _pack.sources_found


@pytest.mark.parametrize("name", ["ARCHITECTURE.md", "docs/architecture/overview.txt"])
def test_architecture_doc_conventions(tmp_path: Path, name: str) -> None:
    # T089 (AC 4): a conventional name alone no longer fills the role
    root = _repo(tmp_path, {"README.md": "# r\n", name: "Layers.\n", **LAYERED})
    _pack, metrics = _metrics(root)
    assert metrics["architecture_description_missing"].outcome == 1


def test_missing_documents_fail_even_when_the_budget_truncates(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"README.md": "# r\n", **LAYERED})
    pack, metrics = _metrics(root, budget_bytes=50)
    assert pack.truncated
    assert metrics["architecture_description_missing"].outcome == 1
    assert metrics["decision_records_missing"].outcome == 1


def test_coverage_counts_source_files_with_imports(tmp_path: Path) -> None:
    pack, _metrics_ = _metrics(_repo(tmp_path, {"README.md": "# r\n", **LAYERED}))
    assert architecture.IMPORTS_SOURCE in pack.sources_found
    assert pack.coverage_score == 0.5


def test_no_imports_is_a_stated_miss(tmp_path: Path) -> None:
    pack, metrics = _metrics(_repo(tmp_path, {"README.md": "# r\n", "x.md": "x\n"}))
    miss = {m.source: m.reason for m in pack.sources_missing}
    assert "not found" in miss[architecture.IMPORTS_SOURCE]
    assert metrics["layer_direction_violations"].abstained


@pytest.mark.parametrize(
    ("path", "layer"),
    [
        ("src/users/dto/create-user.dto.ts", "shared"),
        ("src/users/users.schema.ts", "shared"),
        ("src/users/dto/index.ts", "shared"),
        ("src/common/exceptions/base.exception.ts", "shared"),
        ("src/common/providers/auth.provider.ts", "shared"),
        ("src/auth/jwt.guard.ts", "api"),
        ("src/common/middlewares/log.ts", "api"),
        ("src/common/http.filter.ts", "api"),
        ("src/common/timing.interceptor.ts", "api"),
        ("src/common/user.decorator.ts", "api"),
        ("src/database/migrations/1700-init.ts", "data"),
        ("src/users/users.module.ts", "shared"),
        ("src/config/database.ts", "shared"),
        ("src/app.config.ts", "shared"),
        ("src/utils/dates.ts", "shared"),
        ("src/common/date.util.ts", "shared"),
        ("src/constants/roles.ts", "shared"),
        ("src/roles.constant.ts", "shared"),
        ("src/enums/status.ts", "shared"),
        ("src/status.enum.ts", "shared"),
        ("src/types/index.ts", "shared"),
        ("src/global.d.ts", "shared"),
        ("src/user.interface.ts", "shared"),
        ("src/main.ts", "shared"),
        ("src/users/users.controller.spec.ts", None),
    ],
)
def test_nestjs_and_shared_layer_conventions(path: str, layer: str | None) -> None:
    assert layer_of(path) == layer


def test_a_repository_importing_a_dto_is_not_a_violation(tmp_path: Path) -> None:
    """Supervisor review: DTOs/schemas are shared boundary contracts."""
    files = dict(LAYERED)
    files["src/app/dto/user_dto.py"] = "import os\n"
    files["src/app/repositories/user_repository.py"] = "from app.dto import user_dto\n"
    _pack, metrics = _metrics(_repo(tmp_path, {"README.md": "# r\n", **files}))
    metric = metrics["layer_direction_violations"]
    assert metric.outcome == 0
    assert "3 of 3" in metric.derivation
    assert "curated layer_paths only" in metric.derivation  # T078 note
