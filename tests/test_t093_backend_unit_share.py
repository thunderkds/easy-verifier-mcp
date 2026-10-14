"""T093: the layer rule's classified share counts only backend units.

A backend unit is the deepest directory at or above an api file (by
behaviour) holding a file of the ``package-manifest`` role. Non-shared source
files owned by another manifest directory (a monorepo's frontend apps) leave
the share's denominator, and the derivation says how many and where. With no
api file the denominator stays the whole repository. Violations are still
counted over every classified file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from easy_verifier.core import metrics as metrics_module
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import architecture

MANIFEST = '{"name": "x", "version": "1.0.0"}\n'
ROUTE = (
    "const express = require('express');\n"
    "const svc = require('./svc');\n"
    "const webapp = express();\n"
    "webapp.get('/users', function (req, res) {\n"
    "  res.json(svc.list());\n"
    "});\n"
    "module.exports = webapp;\n"
)
SERVICE = (
    "const store = require('./store');\n"
    "function list() {\n  return store.all();\n}\n"
    "module.exports = { list };\n"
)
STORE = (
    "const mongoose = require('mongoose');\n"
    "const User = mongoose.model('User', new mongoose.Schema({}));\n"
    "function all() {\n  return User.find({});\n}\n"
    "module.exports = { all };\n"
)


def _react(index: int) -> str:
    return (
        "import React from 'react';\n"
        f"export function Widget{index}() {{\n  return null;\n}}\n"
    )


def _backend(prefix: str) -> dict[str, str]:
    return {
        f"{prefix}package.json": MANIFEST,
        f"{prefix}src/routes.js": ROUTE,
        f"{prefix}src/svc.js": SERVICE,
        f"{prefix}src/store.js": STORE,
    }


def _web(prefix: str, count: int = 10) -> dict[str, str]:
    files = {f"{prefix}package.json": MANIFEST}
    files.update({f"{prefix}ui/widget{i}.js": _react(i) for i in range(count)})
    return files


MONOREPO = {"package.json": MANIFEST, **_backend("apps/api/"), **_web("apps/web/")}


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


def _layer(root: Path, files: dict[str, str]):
    pack = run_dimension(architecture.DESCRIPTOR, _repo(root, files), "project")
    found = {m.name: m for m in compute_metrics(pack, curated_metric_tables())}
    return found["layer_direction_violations"]


def test_ac1_ac2_ac4_monorepo_backend_unit_is_measured(tmp_path) -> None:
    metric = _layer(tmp_path, MONOREPO)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    assert "3 of 3 non-shared source file(s) in backend unit(s) (apps/api)" in (
        metric.derivation
    )
    assert (
        "10 non-shared source file(s) outside backend units (apps/web) are not "
        "counted" in metric.derivation
    )


def test_ac6_sabotaged_unit_predicate_whole_repo_abstains(
    tmp_path, monkeypatch
) -> None:
    """Both extremes: the real predicate measures the monorepo (above); a
    predicate placing every file in a unit (today's whole repository)
    abstains on the same files."""
    monkeypatch.setattr(metrics_module, "_in_backend_unit", lambda *_args: True)
    metric = _layer(tmp_path, MONOREPO)
    assert metric.abstained
    assert "3 of 13 non-shared" in metric.outcome.reason


def test_ac3_no_api_file_keeps_the_whole_repository(tmp_path) -> None:
    files = {
        "package.json": MANIFEST,
        "apps/api/package.json": MANIFEST,
        "apps/api/src/svc.js": SERVICE,
        "apps/api/src/store.js": STORE,
        **_web("apps/web/"),
    }
    metric = _layer(tmp_path, files)
    assert metric.abstained
    reason = metric.outcome.reason
    assert "of 12 non-shared source file(s) quoted here classify" in reason
    assert "backend unit" not in reason


def test_root_manifest_only_is_the_whole_repository(tmp_path) -> None:
    files = {**_backend(""), **{f"ui/widget{i}.js": _react(i) for i in range(2)}}
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert (
        "3 of 5 non-shared source file(s) in backend unit(s) (the repository root)"
        in metric.derivation
    )
    assert "outside backend units" not in metric.derivation


def test_api_with_only_a_root_manifest_above_it_uses_the_root_unit(tmp_path) -> None:
    """The root unit does not swallow a nested frontend package: each file
    belongs to the deepest manifest directory above it."""
    files = {**_backend(""), **_web("web/", count=4)}
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert (
        "3 of 3 non-shared source file(s) in backend unit(s) (the repository root)"
        in metric.derivation
    )
    assert "4 non-shared source file(s) outside backend units (web)" in (
        metric.derivation
    )


def test_two_services_are_the_union_of_their_units(tmp_path) -> None:
    files = {
        "package.json": MANIFEST,
        **_backend("services/a/"),
        **_backend("services/b/"),
        **_web("apps/web/", count=12),
    }
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert (
        "6 of 6 non-shared source file(s) in backend unit(s) (services/a, "
        "services/b)" in metric.derivation
    )


LEAK = {
    **MONOREPO,
    "apps/web/ui/leak.js": "const routes = require('../../api/src/routes');\n" + STORE,
}


def test_ac12_import_target_resolves_only_within_the_importers_unit(
    tmp_path,
) -> None:
    """A data file in apps/web naming the stem ``routes`` of an api file in
    apps/api is not a violation: targets resolve within the importer's own
    manifest unit (fullstack-ts: users.service.ts matched apps/web/.../auth.ts)."""
    metric = _layer(tmp_path, LEAK)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    assert "matched only among files of the importer's own manifest unit" in (
        metric.derivation
    )


def test_ac12_sabotaged_whole_repo_targets_count_the_cross_unit_import(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(metrics_module, "_import_unit", lambda *_args: "")
    metric = _layer(tmp_path, LEAK)
    assert metric.outcome == 1
    assert "apps/web/ui/leak.js:1 (data -> api)" in metric.derivation


def test_ac12_same_unit_violation_in_another_package_still_counts(tmp_path) -> None:
    """Within one unit (apps/web, its own manifest) a data -> api import is
    still a violation: AC 12 narrows where targets resolve, nothing more."""
    files = {
        "package.json": MANIFEST,
        **_backend("apps/api/"),
        **_web("apps/web/", count=0),
        "apps/web/ui/page.js": ROUTE,
        "apps/web/ui/leak.js": "const page = require('./page');\n" + STORE,
    }
    metric = _layer(tmp_path, files)
    assert metric.outcome == 1, metric.derivation
    assert "apps/web/ui/leak.js:1 (data -> api)" in metric.derivation


# --- Amendment (AC 8, AC 9): shared wins a layer_paths hint conflict --------

MODULES = {
    f"apps/api/src/m{i}/m{i}.module.js": "module.exports = {};\n" for i in range(4)
}


def test_ac8_shared_wins_a_hint_conflict_in_an_api_named_folder() -> None:
    from easy_verifier.core.structure import layer_of

    assert layer_of("apps/api/src/x/x.module.ts") == "shared"
    assert layer_of("apps/api/src/x/dto/create-x.dto.ts") == "shared"
    assert layer_of("src/x/x.module.ts") == "shared"
    # Not shared-vs-other: a conflict between two non-shared layers stays None.
    assert layer_of("apps/api/models/user.js") is None


def test_ac8_behaviour_still_overrides_a_shared_hint(tmp_path) -> None:
    """A route registered in a ``*.module.js`` file is api by behaviour."""
    files = {**MONOREPO, "apps/api/src/routes.module.js": ROUTE}
    del files["apps/api/src/routes.js"]
    files["apps/api/src/svc.js"] = SERVICE
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert "3 of 3 non-shared source file(s) in backend unit(s) (apps/api)" in (
        metric.derivation
    )
    assert "apps/api/src/routes.module.js (hint shared, behaviour api" in (
        metric.derivation
    )


def test_ac9_monorepo_api_folder_module_files_leave_the_share(tmp_path) -> None:
    """Both extremes: with shared winning, 4 NestJS-style module files in
    ``apps/api`` are shared and the unit share is 3 of 3; sabotaged to
    today's conflict -> unclassified, they stay in the denominator (3 of 7)
    and the rule abstains."""
    files = {
        **MONOREPO,
        **MODULES,
    }
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert "3 of 3 non-shared source file(s) in backend unit(s) (apps/api)" in (
        metric.derivation
    )


def test_ac9_sabotaged_conflict_unclassified_abstains(tmp_path, monkeypatch) -> None:
    from easy_verifier.core import structure

    monkeypatch.setattr(structure, "_resolve_hints", lambda layers: (
        layers.pop() if len(layers) == 1 else None
    ))
    files = {
        **MONOREPO,
        **MODULES,
    }
    metric = _layer(tmp_path, files)
    assert metric.abstained
    assert "3 of 7 non-shared" in metric.outcome.reason


# --- Amendment 2 (AC 11, AC 13): a violation needs behaviour at both ends ---

HINT_ENDS = {
    **_backend(""),
    # api by the *.controller.* hint only: registers no route.
    "src/thing.controller.js": "module.exports = { KIND: 'x' };\n",
    # data by the models/** hint only: calls no DB API, imports the route file.
    "src/models/shape.js": (
        "const routes = require('../routes');\nmodule.exports = {};\n"
    ),
}
HINT_ENDS["src/store.js"] = "const thing = require('./thing.controller');\n" + STORE


def test_ac11_hint_only_ends_are_never_violations(tmp_path) -> None:
    metric = _layer(tmp_path, HINT_ENDS)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    # hint-only files still count in the share
    assert "5 of 5 non-shared" in metric.derivation
    assert "a violation needs a layer from behaviour at both ends" in metric.derivation


def test_ac11_sabotaged_hint_ends_count_again(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(metrics_module, "_is_violation_end", lambda *_args: True)
    metric = _layer(tmp_path, HINT_ENDS)
    assert metric.outcome == 2, metric.derivation
    assert "src/store.js:1 (data -> api)" in metric.derivation
    assert "src/models/shape.js:1 (data -> api)" in metric.derivation
