"""T088: layers assigned by observed behaviour (DDR-0012, FR-075).

api registers a route (route_tokens, T079 receivers included); data calls a
cited data_tokens DB/ORM method on a client or model name the file imports or
binds; service sits on an in-repo import path from api to data. layer_paths are
hints: behaviour wins and the disagreement is reported. A route file querying
the DB directly is api, never a violation (user, Q2).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core import structure
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MIN_CLASSIFIED_SHARE, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import architecture

ROUTE = (
    "const express = require('express');\n"
    "const svc = require('../lib/svc');\n"
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
EXPRESS = {"server/r.js": ROUTE, "lib/svc.js": SERVICE, "lib/store.js": STORE}


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
    metrics = {m.name: m for m in compute_metrics(pack, curated_metric_tables())}
    return metrics["layer_direction_violations"]


def _evidence(path: str, text: str):
    return structure.behaviour_evidence(None, curated_metric_tables())(path, text)


def _check_sc1(root: Path) -> None:
    metric = _layer(root, EXPRESS)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    assert "3 of 3 non-shared" in metric.derivation
    assert "3 by behaviour (1 api, 1 service, 1 data)" in metric.derivation


def _check_sc2(root: Path) -> None:
    files = {**EXPRESS, "lib/store.js": "const r = require('../server/r');\n" + STORE}
    metric = _layer(root, files)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 1
    assert "3 by behaviour (1 api, 1 service, 1 data)" in metric.derivation
    assert "lib/store.js:1 (data -> api)" in metric.derivation


def test_sc1_express_any_receiver_api_service_data_no_violation(tmp_path) -> None:
    _check_sc1(tmp_path)


def test_sc2_data_importing_api_is_one_cited_violation(tmp_path) -> None:
    _check_sc2(tmp_path)


def test_sc3_array_find_never_makes_a_file_data() -> None:
    text = (
        "const mongoose = require('mongoose');\n"
        "const items = [1, 2];\n"
        "items.find(x => x > 1);\n"
        "[3].find(function (x) { return x; });\n"
        "this.cache.find(1);\n"
    )
    assert _evidence("util.js", text).layer is None
    # the same call on a model name bound from the DB package is data
    assert _evidence(
        "util.js", text + "const User = mongoose.model('User');\nUser.find({});\n"
    ) == structure.LayerEvidence(
        "data",
        7,
        frozenset({"User"}),
        frozenset(),
        ((1, frozenset({"mongoose"})),),
    )


def test_sc4_route_file_querying_the_db_is_api_not_a_violation(tmp_path) -> None:
    route = ROUTE.replace(
        "res.json(svc.list());", "res.json(User.find({}));"
    ).replace(
        "const svc = require('../lib/svc');\n",
        "const mongoose = require('mongoose');\n"
        "const User = mongoose.model('User');\n",
    )
    assert _evidence("server/r.js", route).layer == "api"
    metric = _layer(tmp_path, {"server/r.js": route})
    assert metric.outcome == 0
    assert "1 by behaviour (1 api, 0 service, 0 data)" in metric.derivation


def test_sc5_route_in_services_folder_is_api_and_disagreement_listed(tmp_path) -> None:
    files = {
        "src/services/routes.js": ROUTE.replace("../lib/svc", "../lib/svc"),
        "src/lib/svc.js": SERVICE,
        "src/lib/store.js": STORE,
    }
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert "1 disagreement(s) with the layer_paths hints, behaviour wins" in (
        metric.derivation
    )
    assert (
        "src/services/routes.js (hint service, behaviour api at "
        "src/services/routes.js:4)"
    ) in metric.derivation


def test_sc6_unknown_framework_no_hints_abstains_framework_not_recognized(
    tmp_path,
) -> None:
    files = {
        "a/one.js": "const two = require('../b/two');\nmodule.exports = two;\n",
        "b/two.js": "const three = require('../c/three');\nmodule.exports = 2;\n",
        "c/three.js": "module.exports = [1].find(x => x);\n",
    }
    metric = _layer(tmp_path, files)
    assert metric.abstained
    assert metric.outcome.reason.startswith("framework_not_recognized: ")
    assert f"{MIN_CLASSIFIED_SHARE:.2f}" in metric.outcome.reason


def test_no_routes_but_data_is_not_framework_not_recognized(tmp_path) -> None:
    files = {
        "a/one.js": "const two = require('../b/two');\nmodule.exports = two;\n",
        "b/two.js": "const store = require('../c/store');\nmodule.exports = 2;\n",
        "c/store.js": STORE,
    }
    metric = _layer(tmp_path, files)
    assert metric.abstained
    assert not metric.outcome.reason.startswith("framework_not_recognized")
    assert "no route registration was found here" in metric.outcome.reason


@pytest.mark.parametrize("extreme", ["never", "always"])
def test_sc7_sabotaged_data_predicate_breaks_sc1_and_sc2(
    tmp_path, monkeypatch, extreme
) -> None:
    real = structure.layer_evidence

    def sabotaged(*args, **kwargs):
        found = real(*args, **kwargs)
        if found.layer == "api":
            return found
        layer = "data" if extreme == "always" else None
        return structure.LayerEvidence(layer, 1, found.defines, found.handlers,
                                       found.imports)

    monkeypatch.setattr(structure, "layer_evidence", sabotaged)
    with pytest.raises(AssertionError):
        _check_sc1(tmp_path / "sc1")
    with pytest.raises(AssertionError):
        _check_sc2(tmp_path / "sc2")


NEST = {
    "src/users/users.controller.ts": (
        "import { Controller, Get } from '@nestjs/common';\n"
        "import { UsersService } from './users.service';\n\n"
        "@Controller('users')\n"
        "export class UsersController {\n"
        "  constructor(private readonly usersService: UsersService) {}\n\n"
        "  @Get()\n"
        "  findAll() {\n    return this.usersService.findAll();\n  }\n}\n"
    ),
    "src/users/users.service.ts": (
        "import { Injectable } from '@nestjs/common';\n"
        "import { UsersRepository } from './users.repository';\n\n"
        "@Injectable()\n"
        "export class UsersService {\n"
        "  constructor(private readonly repo: UsersRepository) {}\n"
        "  findAll() {\n    return this.repo.find();\n  }\n}\n"
    ),
    "src/users/users.repository.ts": (
        "import { InjectRepository } from '@nestjs/typeorm';\n"
        "import { Repository } from 'typeorm';\n"
        "import { User } from './user.entity';\n\n"
        "export class UsersRepository {\n"
        "  constructor(\n"
        "    @InjectRepository(User) private readonly orm: Repository<User>,\n"
        "  ) {}\n"
        "  find() {\n    return this.orm.find();\n  }\n}\n"
    ),
    "src/users/user.entity.ts": "export class User {\n  id: number;\n}\n",
}


def test_nest_constructor_injected_service_is_on_the_path(tmp_path) -> None:
    # UsersService calls .find() on a name typed by an in-repo class that is
    # no DB client, so it is service, not data
    assert _evidence(
        "src/users/users.service.ts", NEST["src/users/users.service.ts"]
    ).layer is None
    metric = _layer(tmp_path, NEST)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    assert "(1 api, 1 service, 1 data)" in metric.derivation


def test_nest_prisma_service_subclass_imported_is_a_client(tmp_path) -> None:
    files = {
        "src/prisma/prisma.service.ts": (
            "import { PrismaClient } from '@prisma/client';\n"
            "export class PrismaService extends PrismaClient {}\n"
        ),
        "src/notes/notes.repo.ts": (
            "import { PrismaService } from '../prisma/prisma.service';\n"
            "export class NotesRepo {\n"
            "  constructor(private readonly prisma: PrismaService) {}\n"
            "  all() {\n    return this.prisma.note.findMany({});\n  }\n}\n"
        ),
    }
    metric = _layer(tmp_path, files)
    assert "0 api, 0 service, 1 data" in str(metric.outcome) + metric.derivation


FASTAPI = {
    "app/routers/items.py": (
        "from fastapi import APIRouter, Depends\n"
        "from sqlalchemy.orm import Session\n"
        "from ..database import get_db\n"
        "from ..logic import item_logic\n\n"
        "router = APIRouter()\n\n\n"
        '@router.get("/items")\n'
        "def list_items(db: Session = Depends(get_db)):\n"
        "    return item_logic.list_items(db)\n"
    ),
    "app/logic/item_logic.py": (
        "from ..crud import item_crud\n\n\n"
        "def list_items(db):\n    return item_crud.all_items(db)\n"
    ),
    "app/crud/item_crud.py": (
        "from sqlalchemy.orm import Session\n\n\n"
        "def all_items(db: Session):\n    return db.query(Item).all()\n"
    ),
    "app/database.py": (
        "from sqlalchemy import create_engine\n"
        "from sqlalchemy.orm import sessionmaker\n\n"
        'engine = create_engine("sqlite://")\n'
        "SessionLocal = sessionmaker(bind=engine)\n\n\n"
        "def get_db():\n    db = SessionLocal()\n    try:\n        yield db\n"
        "    finally:\n        db.close()\n"
    ),
}


def test_fastapi_depends_get_db_and_python_relative_imports(tmp_path) -> None:
    metric = _layer(tmp_path, FASTAPI)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 0
    assert "(1 api, 1 service, 1 data)" in metric.derivation


def test_django_urls_view_handler_and_model_queries() -> None:
    urls = (
        "from django.urls import path\nfrom . import views\n\n"
        'urlpatterns = [path("orders/", views.index)]\n'
    )
    found = _evidence("shop/urls.py", urls)
    assert (found.layer, found.handlers) == ("api", frozenset({"views"}))
    models = (
        "from django.db import models\n\n\n"
        "class Order(models.Model):\n    pass\n\n\n"
        "def recent():\n    return Order.objects.filter(done=False)\n"
    )
    assert _evidence("shop/models.py", models).layer == "data"
    assert "Order" in _evidence("shop/models.py", models).defines


def test_barrel_index_on_the_path_is_service_and_tests_take_no_layer(
    tmp_path,
) -> None:
    files = {
        "server/r.js": ROUTE.replace("../lib/svc", "../lib"),
        "server/admin.js": ROUTE.replace("../lib/svc", "../lib/svc"),
        "lib/index.js": "module.exports = require('./svc');\n",
        "lib/svc.js": SERVICE,
        "lib/store.js": STORE,
        "test/store.test.js": STORE,
    }
    metric = _layer(tmp_path, files)
    assert not metric.abstained, metric.outcome
    assert "5 of 5 non-shared" in metric.derivation
    assert "(2 api, 2 service, 1 data)" in metric.derivation


# --- AC 11: dynamic import with a literal directory prefix -----------------

DISPATCH = {
    "server/router.js": (
        "const express = require('express');\n"
        "const ControllerManager = require('./controller-manager');\n"
        "const webapp = express();\n"
        "webapp.all('/api/:controller', function (req, res) {\n"
        "  res.json(ControllerManager.handle(req));\n"
        "});\n"
    ),
    "server/controller-manager.js": (
        "const fs = require('fs');\n"
        "const loaded = {};\n"
        "fs.readdirSync(__dirname + '/controllers').forEach(function (name) {\n"
        "  loaded[name] = require('./controllers/' + name);\n"
        "});\n"
        "module.exports = { handle: function (req) { return loaded; } };\n"
    ),
    "server/controllers/accounts.js": (
        "const store = require('../../lib/store');\n"
        "module.exports = { list: function () { return store.all(); } };\n"
    ),
    "server/controllers/groups.js": (
        "const mongoose = require('mongoose');\n"
        "const Group = mongoose.model('Group');\n"
        "module.exports = { list: function () { return Group.find({}); } };\n"
    ),
    "lib/store.js": STORE,
    "lib/other.js": "const store = require('./store');\nmodule.exports = store;\n",
}


def _check_dispatch(root: Path) -> None:
    metric = _layer(root, DISPATCH)
    assert not metric.abstained, metric.outcome
    assert "5 of 6 non-shared" in metric.derivation
    assert "5 by behaviour (1 api, 2 service, 2 data)" in metric.derivation
    assert (
        "1 prefix edge(s) from dynamic imports with a literal directory prefix"
    ) in metric.derivation
    assert (
        "server/controller-manager.js:4 -> './controllers/' (2 file(s))"
    ) in metric.derivation


def test_ac11_prefix_edge_links_every_controller_in_the_directory(tmp_path) -> None:
    _check_dispatch(tmp_path)


@pytest.mark.parametrize(
    ("text", "prefixes"),
    [
        ("const c = require('./controllers/' + name);\n", ((1, "./controllers/"),)),
        ("const c = require(`./strategies/${name}`);\n", ((1, "./strategies/"),)),
        ("const c = await import('../dir/' + x);\n", ((1, "../dir/"),)),
        ("const c = require(name);\n", ()),
        ("const c = require(base + name);\n", ()),
        ("const c = require(`${base}/x`);\n", ()),
        ("// require('./dir/' + x)\n", ()),
    ],
)
def test_ac11_js_dynamic_prefix_forms(text, prefixes) -> None:
    assert _evidence("server/m.js", text).prefixes == prefixes


@pytest.mark.parametrize(
    ("text", "prefixes"),
    [
        (
            "import importlib\nm = importlib.import_module('app.plugins.' + n)\n",
            ((2, "app.plugins."),),
        ),
        (
            'import importlib\nm = importlib.import_module(f"app.plugins.{n}")\n',
            ((2, "app.plugins."),),
        ),
        ("import importlib\nm = importlib.import_module(n)\n", ()),
    ],
)
def test_ac11_python_dynamic_prefix_forms(text, prefixes) -> None:
    assert _evidence("app/loader.py", text).prefixes == prefixes


def test_ac11_python_prefix_resolves_non_recursively() -> None:
    from easy_verifier.core.metrics import _prefix_targets

    files = [
        "src/app/loader.py",
        "src/app/plugins/a.py",
        "src/app/plugins/b.py",
        "src/app/plugins/deep/c.py",
    ]
    assert _prefix_targets("src/app/loader.py", "app.plugins.", files) == {
        "src/app/plugins/a.py",
        "src/app/plugins/b.py",
    }
    assert _prefix_targets("src/app/loader.py", "./plugins/", files) == {
        "src/app/plugins/a.py",
        "src/app/plugins/b.py",
    }


@pytest.mark.parametrize("extreme", ["never", "everything"])
def test_ac11_sabotaged_prefix_edges_break_the_dispatch_fixture(
    tmp_path, monkeypatch, extreme
) -> None:
    from easy_verifier.core import metrics

    if extreme == "never":
        monkeypatch.setattr(metrics, "_prefix_targets", lambda *a: set())
    else:
        monkeypatch.setattr(
            metrics, "_prefix_targets", lambda path, _p, files: set(files) - {path}
        )
    with pytest.raises(AssertionError):
        _check_dispatch(tmp_path)
