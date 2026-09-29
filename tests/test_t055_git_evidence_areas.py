"""T055 - area rule groups needing git evidence (FR-051, FR-043).

#5 backward compatibility (blast-radius): removed or renamed public
declarations and destructive migration operations, read from the diff of a
``changes`` scope. #27 documentation source of truth (requirement-fidelity):
competing requirements documents and the share of code-changing commits that
also change documentation. Each sabotage pair varies only the predicate it
pins, so a metric that ignored the predicate would fail here.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.adapters import cli
from easy_verifier.core import scope as scope_module
from easy_verifier.core.metric_tables import FIELD_METRICS, curated_metric_tables
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    METRIC_DEFINITIONS,
    compute_metrics,
)
from easy_verifier.core.models import EvidencePack, to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.dimensions import DIMENSIONS, blast_radius, requirement_fidelity

SYMBOLS = "public_symbols_removed"
OPS = "destructive_migration_ops"
DOCS = "requirements_docs_count"
CO_CHANGE = "code_commits_with_docs_share"

API = """def list_items():
    return []


def get_item(item_id):
    return {"id": item_id}


def _helper():
    return 1
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    ).stdout


def _write(root: Path, files: dict[str, str | None]) -> None:
    for relative, text in files.items():
        path = root / relative
        if text is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _commit(root: Path, files: dict[str, str | None], message: str = "c") -> None:
    _write(root, files)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _commit(root, files, "init")
    return root


def _metric(pack: EvidencePack, name: str):
    (found,) = compute_metrics(pack, curated_metric_tables()).by_name(name)
    return found


def _change(root: Path, files: dict[str, str | None], **kwargs) -> EvidencePack:
    _commit(root, files, "the change")
    return run_dimension(blast_radius.DESCRIPTOR, root, "changes", ref="HEAD", **kwargs)


def _base(tmp_path: Path, name: str = "r") -> Path:
    return _repo(
        tmp_path / name,
        {
            "src/shop/api.py": API,
            "migrations/0001_init.sql": "CREATE TABLE items (id int, price int);\n",
            "README.md": "# shop\n",
        },
    )


# ---------------------------------------------------------------------------
# Declarations and registry data
# ---------------------------------------------------------------------------


def test_new_metrics_are_declared_evidence_local():
    kinds = {d.name: d.kind for d in METRIC_DEFINITIONS}
    for name in (SYMBOLS, OPS, DOCS, CO_CHANGE):
        assert kinds.get(name) == EVIDENCE_LOCAL, name
    assert FIELD_METRICS["public_declarations"] == (SYMBOLS,)


def test_every_curated_language_declares_cited_public_declarations():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    assert not registry.warnings
    for name, entry in registry.languages.items():
        cited = entry.fields.get("public_declarations", ())
        assert cited and all(c.value for c in cited), name
        assert all(c.citation_url.startswith("https://") for c in cited), name


@pytest.mark.parametrize(
    ("suffix", "line", "name"),
    [
        (".py", "def get_item(item_id):", "get_item"),
        (".py", "    def method(self):", "method"),
        (".py", "class Shop(Base):", "Shop"),
        (".py", "def f():", "f"),
        (".py", "def _private():", None),
        (".py", "default = 1", None),
        (".go", "func Handle(w http.ResponseWriter) {", "Handle"),
        (".go", "func (s Server) Serve() {", "Serve"),
        (".go", "func handle() {", None),
        (".ts", "export function load(x: number) {", "load"),
        (".ts", "export const store = {", "store"),
        (".ts", "function internal() {", None),
        (".java", "public static int add(int a, int b) {", "add"),
        (".java", "public class Shop extends Base {", "Shop"),
        (".java", "private int add(int a) {", None),
        (".rs", "pub fn load() -> u8 {", "load"),
        (".rs", "pub(crate) fn load() {", None),
        (".rb", "def self.build(x)", "build"),
        (".php", "public function save($x) {", "save"),
        (".php", "private function save($x) {", None),
        (".kt", "fun greet(name: String) {", "greet"),
        (".kt", "private fun greet() {", None),
    ],
)
def test_public_declaration_names_per_language(suffix, line, name):
    pattern = curated_metric_tables().public_declarations[suffix]
    assert blast_radius._declared_name(pattern, line) == name


# ---------------------------------------------------------------------------
# #5 removed / renamed public symbols (AC 1, Success Criterion 1)
# ---------------------------------------------------------------------------


def test_a_change_removing_a_public_function_counts_one_cited_at_its_line(
    tmp_path: Path,
):
    root = _base(tmp_path)
    pack = _change(
        root,
        {
            "src/shop/api.py": API.replace(
                'def get_item(item_id):\n    return {"id": item_id}\n\n\n', ""
            ),
            "migrations/0002.sql": "CREATE TABLE t (id int);\n",
        },
    )
    metric = _metric(pack, SYMBOLS)
    assert metric.outcome == 1
    assert metric.computed_from == ("src/shop/api.py:5-5",)  # the quoted line only
    assert "get_item removed" in metric.derivation
    (quoted,) = [e for e in pack.excerpts if e.ref == "src/shop/api.py:5-5"]
    assert quoted.text == "-def get_item(item_id):"


def test_private_removal_and_a_resignatured_function_are_not_counted(tmp_path: Path):
    root = _base(tmp_path)
    changed = API.replace("def _helper():\n    return 1\n", "").replace(
        "def get_item(item_id):", "def get_item(item_id, default=None):"
    )
    pack = _change(root, {"src/shop/api.py": changed})
    metric = _metric(pack, SYMBOLS)
    assert metric.outcome == 0
    assert metric.computed_from == ("src/shop/api.py",)


def test_a_rename_is_counted_and_labelled_renamed(tmp_path: Path):
    root = _base(tmp_path)
    pack = _change(root, {"src/shop/api.py": API.replace("get_item", "fetch_item")})
    metric = _metric(pack, SYMBOLS)
    assert metric.outcome == 1
    assert "get_item renamed (to fetch_item)" in metric.derivation


def test_a_function_moved_to_another_module_is_kept_and_a_file_rename_is_named(
    tmp_path: Path,
):
    root = _base(tmp_path)
    _git(root, "mv", "src/shop/api.py", "src/shop/service.py")
    pack = _change(root, {"src/shop/other.py": "def helper_two():\n    return 2\n"})
    metric = _metric(pack, SYMBOLS)
    assert metric.outcome == 0
    assert "1 code file(s) renamed, not counted" in metric.derivation
    assert pack.compat.renamed_code_files == ("src/shop/service.py",)


def test_a_deleted_test_file_is_not_a_public_api_removal(tmp_path: Path):
    root = _repo(
        tmp_path / "r",
        {
            "src/app.py": "def run():\n    pass\n",
            "tests/test_app.py": "def test_run():\n    assert True\n",
        },
    )
    pack = _change(
        root, {"tests/test_app.py": None, "src/app.py": "def run():\n    return 1\n"}
    )
    assert _metric(pack, SYMBOLS).outcome == 0
    deleted = _change(root, {"src/app.py": None})
    metric = _metric(deleted, SYMBOLS)
    assert metric.outcome == 1
    assert "src/app.py:1-1" in metric.computed_from


# ---------------------------------------------------------------------------
# #5 destructive migration operations (AC 1)
# ---------------------------------------------------------------------------


def test_a_migration_dropping_a_column_counts_one_cited_at_its_line(tmp_path: Path):
    root = _base(tmp_path)
    pack = _change(
        root,
        {
            "migrations/0002_drop.sql": (
                "-- tidy up\nALTER TABLE items DROP COLUMN price;\n"
            )
        },
    )
    metric = _metric(pack, OPS)
    assert metric.outcome == 1
    assert "migrations/0002_drop.sql:2-2" in metric.computed_from
    assert "in a new migration file" in metric.derivation


def test_create_with_a_downgrade_drop_comments_and_non_migrations_do_not_count(
    tmp_path: Path,
):
    root = _base(tmp_path)
    alembic = (
        "def upgrade():\n    op.create_table('orders')\n\n\n"
        "def downgrade():\n    op.drop_table('orders')\n"
    )
    pack = _change(
        root,
        {
            "alembic/versions/0002_orders.py": alembic,
            "migrations/0003.sql": "-- DROP TABLE items later\nCREATE TABLE t;\n",
            "migrations/0004.down.sql": "DROP TABLE t;\n",
            "src/shop/sql.py": 'QUERY = "DROP TABLE items"\n',
        },
    )
    assert _metric(pack, OPS).outcome == 0
    # Sabotage twin: the same drop in the upgrade section counts.
    other = _base(tmp_path, "twin")
    twin = _change(
        other,
        {
            "alembic/versions/0002_orders.py": alembic.replace(
                "op.create_table('orders')", "op.drop_column('items', 'price')"
            )
        },
    )
    assert _metric(twin, OPS).outcome == 1


def test_an_edited_migration_is_labelled_edited_and_framework_apis_count(
    tmp_path: Path,
):
    root = _base(tmp_path)
    pack = _change(
        root,
        {
            "migrations/0001_init.sql": (
                "CREATE TABLE items (id int);\nALTER TABLE items RENAME TO goods;\n"
            ),
            "db/migrate/0002_remove.rb": (
                "class Remove < Migration\n  def change\n"
                "    remove_column :items, :price\n  end\nend\n"
            ),
        },
    )
    metric = _metric(pack, OPS)
    assert metric.outcome == 2
    assert "in an edited migration file" in metric.derivation
    assert "remove_column in a new migration file" in metric.derivation


# ---------------------------------------------------------------------------
# #5 abstentions: no diff, clipped diff, dropped evidence (AC 2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scope", ["project", "worktree"])
def test_outside_a_changes_scope_the_count_abstains_naming_the_scope(
    tmp_path: Path, scope: str
):
    root = _base(tmp_path)
    pack = run_dimension(blast_radius.DESCRIPTOR, root, scope)
    assert pack.compat is None
    for name in (SYMBOLS, OPS):
        metric = _metric(pack, name)
        assert metric.abstained
        assert f"{scope!r} scope" in metric.abstention.reason
        assert "'changes' scope" in metric.abstention.reason


def test_an_unresolved_changes_scope_abstains_and_other_packs_abstain(tmp_path: Path):
    root = _base(tmp_path)
    unresolved = run_dimension(blast_radius.DESCRIPTOR, root, "changes")
    assert "could not be resolved" in _metric(unresolved, SYMBOLS).abstention.reason
    other = run_dimension(DIMENSIONS["code-quality"], root, "changes", ref="HEAD")
    assert "only the blast-radius pack" in _metric(other, OPS).abstention.reason


def test_a_clipped_diff_abstains_instead_of_counting_a_partial_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _base(tmp_path)
    removal = {"src/shop/api.py": API.replace("def get_item", "def other_item")}
    monkeypatch.setattr(scope_module, "MAX_DIFF_CHARS", 40)
    pack = _change(root, removal)
    metric = _metric(pack, SYMBOLS)
    assert metric.abstained
    assert "clipped" in metric.abstention.reason


def test_a_count_whose_quoted_line_the_budget_dropped_abstains(tmp_path: Path):
    root = _base(tmp_path)
    removal = {"src/shop/api.py": API.replace("def get_item", "def other_item")}
    _commit(root, removal, "the change")
    tight = run_dimension(
        blast_radius.DESCRIPTOR, root, "changes", ref="HEAD", budget_bytes=5
    )
    metric = _metric(tight, SYMBOLS)
    assert metric.abstained
    assert "byte budget dropped" in metric.abstention.reason
    roomy = run_dimension(blast_radius.DESCRIPTOR, root, "changes", ref="HEAD")
    assert _metric(roomy, SYMBOLS).outcome == 1


def test_a_listed_cap_counts_the_rest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _repo(
        tmp_path / "r",
        {"src/m.py": "".join(f"def f{i}():\n    pass\n" for i in range(5))},
    )
    monkeypatch.setattr(blast_radius, "MAX_COMPAT_LISTED", 2)
    pack = _change(root, {"src/m.py": "X = 1\n"})
    metric = _metric(pack, SYMBOLS)
    assert metric.outcome == 5
    assert "and 3 more counted, not quoted" in metric.derivation
    assert len(pack.compat.removed_symbols) == 2


# ---------------------------------------------------------------------------
# #27 documentation source of truth (AC 3, Success Criterion 3)
# ---------------------------------------------------------------------------


def _rf(root: Path) -> EvidencePack:
    return run_dimension(requirement_fidelity.DESCRIPTOR, root, "project")


def test_two_competing_requirements_docs_count_two_and_one_counts_one(tmp_path: Path):
    two = _repo(
        tmp_path / "two",
        {
            "PRD.md": "# PRD\n",
            "docs/requirements.md": "# Requirements\n",
            "a.py": "A = 1\n",
        },
    )
    one = _repo(tmp_path / "one", {"PRD.md": "# PRD\n", "a.py": "A = 1\n"})
    metric = _metric(_rf(two), DOCS)
    assert metric.outcome == 2
    assert metric.computed_from == ("PRD.md", "docs/requirements.md")
    assert _metric(_rf(one), DOCS).outcome == 1


def test_no_requirements_doc_abstains_rather_than_counting_zero(tmp_path: Path):
    root = _repo(tmp_path / "r", {"README.md": "# r\n", "a.py": "A = 1\n"})
    metric = _metric(_rf(root), DOCS)
    assert metric.abstained
    assert "requirements-doc role" in metric.abstention.reason


def test_code_commits_never_touching_docs_share_zero_and_docs_raise_it(tmp_path: Path):
    never = _repo(tmp_path / "never", {"PRD.md": "# PRD\n"})  # a docs-only commit
    for i in range(4):
        _commit(never, {"src/a.py": f"A = {i}\n"})
    metric = _metric(_rf(never), CO_CHANGE)
    assert metric.outcome == 0.0
    assert "0 of 4 code-changing commit(s)" in metric.derivation
    assert metric.computed_from == ("PRD.md",)

    # Sabotage twin: the same history with docs changed in two commits.
    some = _repo(tmp_path / "some", {"PRD.md": "# PRD\n"})
    _commit(some, {"src/a.py": "A = 0\n"})
    _commit(some, {"src/a.py": "A = 1\n", "docs/usage.md": "use it\n"})
    _commit(some, {"src/a.py": "A = 2\n"})
    _commit(some, {"src/a.py": "A = 3\n", "docs/usage.md": "use it well\n"})
    metric = _metric(_rf(some), CO_CHANGE)
    assert metric.outcome == 0.5
    assert "docs/usage.md" in metric.computed_from


def test_merge_commits_and_doc_only_commits_are_not_code_commits(tmp_path: Path):
    root = _repo(tmp_path / "r", {"PRD.md": "# PRD\n", "src/a.py": "A = 0\n"})
    _git(root, "checkout", "-qb", "side")
    _commit(root, {"src/b.py": "B = 1\n"})
    _git(root, "checkout", "-q", "main")
    _commit(root, {"notes.md": "notes\n"})
    _git(root, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    pack = _rf(root)
    facts = pack.doc_history
    assert (facts.commits_scanned, facts.code_commits) == (3, 2)
    assert facts.code_commits_with_docs == 1  # only init; the merge is skipped
    assert _metric(pack, CO_CHANGE).outcome == 0.5


def test_no_git_and_a_shallow_clone_abstain_with_a_reason(tmp_path: Path):
    plain = tmp_path / "plain"
    _write(plain, {"PRD.md": "# PRD\n", "a.py": "A = 1\n"})
    reason = _metric(_rf(plain), CO_CHANGE).abstention.reason
    assert "not a git repository" in reason

    origin = _repo(tmp_path / "origin", {"PRD.md": "# PRD\n", "a.py": "A = 0\n"})
    for i in range(3):
        _commit(origin, {"a.py": f"A = {i + 1}\n"})
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{origin}", str(clone))
    assert "shallow clone" in _metric(_rf(clone), CO_CHANGE).abstention.reason


def test_the_window_bounds_the_commits_read(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path / "r", {"PRD.md": "# PRD\n", "a.py": "A = 0\n"})
    for i in range(4):
        _commit(root, {"a.py": f"A = {i + 1}\n"})
    monkeypatch.setattr(requirement_fidelity, "CO_CHANGE_WINDOW", 3)
    pack = _rf(root)
    assert (pack.doc_history.commits_scanned, pack.doc_history.window) == (3, 3)
    assert "window 3" in _metric(pack, CO_CHANGE).derivation
    assert _metric(pack, CO_CHANGE).outcome == 0.0  # the init commit is outside


# ---------------------------------------------------------------------------
# AC 4: additive models, byte-identical JSON when the new facts are unused
# ---------------------------------------------------------------------------

PRE_T055_PACK_KEYS = [
    "dimension",
    "mode",
    "scope",
    "files_read",
    "excerpts",
    "sources_sought",
    "sources_found",
    "sources_missing",
    "coverage_score",
    "truncated",
    "omitted_count",
    "warnings",
    "redactions",
    "had_redactions",
    "truncation",
    "approval_requests",
    "source_provenance",
    "trace_search",
    "reach",
]


def test_unused_facts_leave_the_pack_json_byte_identical(tmp_path: Path, capsys):
    root = _base(tmp_path)
    pack = run_dimension(DIMENSIONS["code-quality"], root, "project")
    emitted = to_json_dict(pack)
    assert list(emitted) == PRE_T055_PACK_KEYS
    legacy = dataclasses.asdict(pack)
    del legacy["compat"], legacy["doc_history"]
    assert json.dumps(emitted) == json.dumps(legacy)

    assert cli.main(["code-quality", "--repo", str(root), "--scope", "project"]) == 0
    assert list(json.loads(capsys.readouterr().out)) == PRE_T055_PACK_KEYS
    blast = run_dimension(blast_radius.DESCRIPTOR, root, "project")
    assert list(to_json_dict(blast)) == PRE_T055_PACK_KEYS


def test_used_facts_are_serialized(tmp_path: Path):
    root = _base(tmp_path)
    pack = _change(root, {"README.md": "# shop!\n"})
    emitted = to_json_dict(pack)
    assert list(emitted) == [*PRE_T055_PACK_KEYS, "compat"]
    assert emitted["compat"]["removed_symbols_total"] == 0
    assert "doc_history" in to_json_dict(_rf(root))


# ---------------------------------------------------------------------------
# User decision (b): a template is not a competing requirements source
# ---------------------------------------------------------------------------


def test_templates_do_not_fill_the_requirements_doc_role(tmp_path: Path):
    root = _repo(
        tmp_path / "r",
        {
            "PRD.md": "# PRD\n",
            "templates/PRD_template.md": "# PRD template\n",
            "docs/PRD.template.md": "# t\n",
            "docs/requirements_template.md": "# t\n",
            "a.py": "A = 1\n",
        },
    )
    pack = _rf(root)
    metric = _metric(pack, DOCS)
    assert metric.outcome == 1
    assert metric.computed_from == ("PRD.md",)
    # Sabotage twin: the same file outside a template path still competes.
    _commit(root, {"specs/PRD_v2.md": "# PRD v2\n"})
    assert _metric(_rf(root), DOCS).outcome == 2


# ---------------------------------------------------------------------------
# AC 5: user-signed weights (2026-09-29), areas and citations
# ---------------------------------------------------------------------------

BACKWARD = "Backward compatibility & upgrade safety"
DOC_TRUTH = "Documentation source-of-truth governance"
SIGNED_OFF = {
    "blast-radius": {
        "max_fan_in_changed": (35, 20, "at_most", BACKWARD),
        "changed_files_in_churn_hotspots_share": (35, 0.20, "at_most", BACKWARD),
        SYMBOLS: (15, 0, "at_most", BACKWARD),
        OPS: (15, 0, "at_most", BACKWARD),
    },
    "requirement-fidelity": {
        "acceptance_criteria_traced_to_code_share": (
            35,
            0.80,
            "at_least",
            "Business-rule correctness",
        ),
        "acceptance_criteria_traced_to_test_share": (
            35,
            0.80,
            "at_least",
            "Business-rule correctness",
        ),
        DOCS: (15, 1, "at_most", DOC_TRUTH),
        CO_CHANGE: (15, 0.30, "at_least", DOC_TRUTH),
    },
}


@pytest.mark.parametrize("dimension", sorted(SIGNED_OFF))
def test_signed_off_weights_thresholds_and_areas(dimension):
    from easy_verifier.core.judge import AREAS, PROJECT_DEFAULT, RATING_RULES

    rules = RATING_RULES[dimension]
    assert {
        n: (r.weight, r.threshold, r.comparison, r.area) for n, r in rules.items()
    } == SIGNED_OFF[dimension]
    assert sum(r.weight for r in rules.values()) == 100
    assert AREAS[4] == BACKWARD and AREAS[26] == DOC_TRUTH
    for name in (SYMBOLS, OPS, DOCS, CO_CHANGE):
        if name in rules:
            assert rules[name].threshold_citation == PROJECT_DEFAULT
    urls = {c.url for name in rules for c in rules[name].metric_citation}
    if dimension == "blast-radius":
        assert "https://semver.org/spec/v2.0.0.html" in urls
    else:
        assert "https://www.iso.org/standard/77451.html" in urls


def test_the_new_rules_are_unmet_on_the_success_fixtures(tmp_path: Path):
    from easy_verifier.core.judge import RATING_RULES, _passes

    root = _base(tmp_path)
    pack = _change(root, {"src/shop/api.py": API.replace("def get_item", "def x_")})
    for name in (SYMBOLS,):
        value = _metric(pack, name).outcome
        assert not _passes(value, RATING_RULES["blast-radius"][name])
    two = _repo(tmp_path / "two", {"PRD.md": "# P\n", "docs/requirements.md": "# R\n"})
    for i in range(3):
        _commit(two, {"a.py": f"A = {i}\n"})
    rf = _rf(two)
    for name in (DOCS, CO_CHANGE):
        assert not _passes(
            _metric(rf, name).outcome, RATING_RULES["requirement-fidelity"][name]
        )


def test_an_unknown_language_is_asked_for_public_declarations_too():
    from easy_verifier.core import gate

    registry = load_registry(known_roles=GENERIC_PATTERNS)
    stack = {"languages": ["zz-unknown"], "frameworks": []}
    fields = [i["field"] for i in gate.reference_requests(stack, registry)["requests"]]
    assert "public_declarations" in fields
    assert len(fields) == 14  # 13 before T055 wired the #5 rule


# ---------------------------------------------------------------------------
# DDR-0002: a secret-bearing file in the diff is never parsed or quoted
# ---------------------------------------------------------------------------


def test_secret_bearing_files_in_the_diff_are_excluded_not_parsed(tmp_path: Path):
    root = _repo(
        tmp_path / "r",
        {
            ".env": "def leaked_name():\nTOKEN=FAKEfake\n",
            "src/app.py": "def run():\n    pass\n",
        },
    )
    pack = _change(
        root,
        {
            ".env": "TOKEN=FAKEfake\n",
            "migrations/secrets.pem": "DROP TABLE items;\n",
            "src/app.py": "def run():\n    return 1\n",
        },
    )
    assert _metric(pack, OPS).outcome == 0
    symbols = _metric(pack, SYMBOLS)
    assert symbols.outcome == 0
    assert pack.compat.secret_excluded == (".env", "migrations/secrets.pem")
    assert ".env" not in pack.compat.examined
    assert "2 secret-bearing file(s) excluded" in symbols.derivation
    assert not [
        e for e in pack.excerpts if e.path in {".env", "migrations/secrets.pem"}
    ]
    # Sabotage twin: the same content under ordinary names is parsed.
    twin = _repo(
        tmp_path / "twin",
        {
            "env.py": "def leaked_name():\n    pass\n",
            "src/app.py": "def run():\n    pass\n",
        },
    )
    parsed = _change(
        twin, {"env.py": "X = 1\n", "migrations/0002.sql": "DROP TABLE items;\n"}
    )
    assert _metric(parsed, OPS).outcome == 1
    assert _metric(parsed, SYMBOLS).outcome == 1
