"""T034 - dangerous-sink tokens per language (CWE-95/78/89) as registry data.

Safe/unsafe twins differ only in the sink construct. Sabotage tests vary one
pinned predicate each -- comment/string blanking, the "not after ." guard,
the security dimension's sink excerpts -- and show the result move with it.
"""

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core import metrics as metrics_module
from easy_verifier.core.metric_tables import curated_metric_tables, token_regex
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    SinkPattern,
    compute_metrics,
    sink_hits,
)
from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.dimensions import DIMENSIONS
from easy_verifier.dimensions import security as security_module

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDORED_CWE = REPO_ROOT / "src/easy_verifier/registry/vendored/cwe.json"
SINK_CWES = {"CWE-95", "CWE-78", "CWE-89"}

# (path, unsafe line, safe twin, cwe) -- at least one pair per language per
# CWE that language declares.
PAIRS = [
    (
        "a.py",
        "cursor.execute(f\"SELECT * FROM u WHERE n = '{user}'\")",
        'cursor.execute("SELECT * FROM u WHERE n = %s", (user,))',
        "CWE-89",
    ),
    (
        "a.py",
        'cursor.execute("SELECT * FROM u WHERE n = %s" % user)',
        'cursor.execute("SELECT * FROM u WHERE n = %s", (user,))',
        "CWE-89",
    ),
    (
        "a.py",
        'cursor.execute("SELECT * FROM u WHERE n = " + user)',
        'cursor.execute("SELECT * FROM u WHERE n = ?", [user])',
        "CWE-89",
    ),
    ("a.py", "subprocess.run(cmd, shell=True)", 'subprocess.run(["ls", d])', "CWE-78"),
    ("a.py", "os.system(cmd)", 'os.system("ls")', "CWE-78"),
    ("a.py", "eval(user_input)", "ast.literal_eval(user_input)", "CWE-95"),
    ("a.js", "eval(code);", "JSON.parse(code);", "CWE-95"),
    (
        "a.ts",
        "child_process.exec(cmd);",
        'child_process.execFile("ls", [dir]);',
        "CWE-78",
    ),
    ("a.js", "spawn(cmd, { shell: true });", "spawn(cmd, [arg]);", "CWE-78"),
    (
        "a.js",
        'db.query("SELECT * FROM u WHERE id = " + id);',
        'db.query("SELECT * FROM u WHERE id = ?", [id]);',
        "CWE-89",
    ),
    ("a.go", "exec.Command(name, arg)", 'exec.Command("ls", dir)', "CWE-78"),
    (
        "a.go",
        'db.Query("SELECT * FROM u WHERE id = " + id)',
        'db.Query("SELECT * FROM u WHERE id = $1", id)',
        "CWE-89",
    ),
    (
        "a.go",
        'db.Exec(fmt.Sprintf("DELETE FROM u WHERE id = %s", id))',
        'db.Exec("DELETE FROM u WHERE id = $1", id)',
        "CWE-89",
    ),
    ("A.java", "engine.eval(script);", 'engine.eval("1 + 1");', "CWE-95"),
    (
        "A.java",
        "Runtime.getRuntime().exec(cmd);",
        'new ProcessBuilder("ls").start();',
        "CWE-78",
    ),
    (
        "A.java",
        'stmt.executeQuery("SELECT * FROM u WHERE id = " + id);',
        'conn.prepareStatement("SELECT * FROM u WHERE id = ?");',
        "CWE-89",
    ),
    ("a.kt", "engine.eval(script)", 'engine.eval("1 + 1")', "CWE-95"),
    ("a.kt", "Runtime.getRuntime().exec(cmd)", 'ProcessBuilder("ls")', "CWE-78"),
    (
        "a.kt",
        'db.rawQuery("SELECT * FROM u WHERE id = " + id, null)',
        'db.rawQuery("SELECT * FROM u WHERE id = ?", arrayOf(id))',
        "CWE-89",
    ),
    (
        "A.cs",
        "await CSharpScript.EvaluateAsync(code);",
        "int.Parse(code);",
        "CWE-95",
    ),
    ("A.cs", "Process.Start(cmd);", 'Process.Start("notepad.exe");', "CWE-78"),
    (
        "A.cs",
        'new SqlCommand($"SELECT * FROM u WHERE id = {id}", conn);',
        'new SqlCommand("SELECT * FROM u WHERE id = @id", conn);',
        "CWE-89",
    ),
    ("a.php", "eval($code);", "json_decode($code);", "CWE-95"),
    ("a.php", "system($cmd);", "$this->system($cmd);", "CWE-78"),
    (
        "a.php",
        '$pdo->query("SELECT * FROM u WHERE id = " . $id);',
        '$pdo->prepare("SELECT * FROM u WHERE id = ?");',
        "CWE-89",
    ),
    ("a.rb", "eval(code)", "Integer(code)", "CWE-95"),
    ("a.rb", "system(cmd)", 'system("ls", dir)', "CWE-78"),
    (
        "a.rb",
        'User.where("name = \'" + name + "\'")',
        'User.where("name = ?", name)',
        "CWE-89",
    ),
    ("a.rs", "Command::new(cmd)", 'Command::new("ls")', "CWE-78"),
    (
        "a.rs",
        'conn.execute(&format!("DELETE FROM u WHERE id = {}", id), [])',
        'conn.execute("DELETE FROM u WHERE id = ?1", [id])',
        "CWE-89",
    ),
]


def tables():
    return curated_metric_tables()


def pack(files, *, truncated=False):
    """``files`` maps path -> text; each becomes one whole-file excerpt."""
    return EvidencePack(
        dimension="security",
        mode="kit-aware",
        scope="worktree",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(path, 1, len(text.splitlines()), text)
            for path, text in files.items()
        ),
        sources_sought=("x",),
        sources_found=("x",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=truncated,
        omitted_count=5 if truncated else 0,
        truncation=TruncationRecord(
            truncated=truncated, omitted_count=5 if truncated else 0
        ),
    )


def sink_metric(evidence):
    (found,) = compute_metrics(evidence, tables()).by_name("sink_hits_observed")
    return found


# --- AC 1: registry field, cited per CWE -----------------------------------


def test_every_language_declares_cited_sinks_from_the_vendored_cwe_pages():
    vendored = {
        f"CWE-{item['id']}": item["url"]
        for item in json.loads(VENDORED_CWE.read_text())["weaknesses"]
    }
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    assert registry.warnings == ()
    assert len(registry.languages) == 9
    for name, entry in registry.languages.items():
        items = entry.fields.get("security_sinks", ())
        assert items, name
        assert {item.cwe for item in items} >= {"CWE-78", "CWE-89"}, name
        for item in items:
            assert item.cwe in SINK_CWES, (name, item.cwe)
            assert item.citation_url == vendored[item.cwe], (name, item.cwe)
            assert item.source_tag == "curated"


def test_every_pair_language_cwe_is_covered():
    declared = {
        (suffix, pattern.cwe)
        for suffix, patterns in tables().sinks.items()
        for pattern in patterns
    }
    by_language = {
        name: {
            (ext, item.cwe)
            for ext in entry.fields["source_extensions"][0].value
            for item in entry.fields["security_sinks"]
        }
        for name, entry in load_registry(known_roles=GENERIC_PATTERNS).languages.items()
    }
    covered = {(Path(path).suffix, cwe) for path, _u, _s, cwe in PAIRS}
    for name, wanted in by_language.items():
        assert wanted <= declared, name
        assert {cwe for _e, cwe in wanted} == {
            cwe for ext, cwe in covered if (ext, cwe) in wanted
        }, name


def _entry(tmp_path: Path, sink_item: str) -> Path:
    (tmp_path / "x.toml").write_text(
        '[[manifests]]\nvalue = ["x.mod"]\ncitation_url = "https://e.org/"\n'
        'source_tag = "curated"\n\n[[security_sinks]]\n' + sink_item,
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize(
    ("item", "problem"),
    [
        (
            'value = ["eval ("]\ncitation_url = "https://e.org/"\n'
            'source_tag = "curated"\n',
            "missing cwe",
        ),
        (
            'cwe = "89"\nvalue = ["eval ("]\ncitation_url = "https://e.org/"\n'
            'source_tag = "curated"\n',
            "cwe: must be a CWE id",
        ),
    ],
)
def test_a_sink_item_without_a_valid_cwe_is_rejected(tmp_path, item, problem):
    loaded = load_registry(_entry(tmp_path, item), known_roles=GENERIC_PATTERNS)
    assert "x" not in loaded.languages
    assert any(problem in warning for warning in loaded.warnings), loaded.warnings


def test_cwe_is_accepted_only_on_security_sinks(tmp_path):
    (tmp_path / "x.toml").write_text(
        '[[manifests]]\ncwe = "CWE-89"\nvalue = ["x.mod"]\n'
        'citation_url = "https://e.org/"\nsource_tag = "curated"\n',
        encoding="utf-8",
    )
    loaded = load_registry(tmp_path, known_roles=GENERIC_PATTERNS)
    assert "x" not in loaded.languages
    assert any("unknown key cwe" in warning for warning in loaded.warnings)


# --- AC 4 / success criteria: safe twin 0, unsafe twin 1 --------------------


@pytest.mark.parametrize(("path", "unsafe", "safe", "cwe"), PAIRS)
def test_unsafe_twin_hits_once_and_safe_twin_never(path, unsafe, safe, cwe):
    hits = sink_hits(path, f"x = 1\n{unsafe}\n", tables())
    assert [(hit.line, hit.cwe) for hit in hits] == [(2, cwe)]
    assert sink_hits(path, f"x = 1\n{safe}\n", tables()) == ()


def test_multi_line_call_hits_at_its_first_line():
    text = 'cursor.execute(\n    f"SELECT {user}"\n)\n'
    (hit,) = sink_hits("a.py", text, tables())
    assert (hit.line, hit.end_line, hit.cwe) == (1, 2, "CWE-89")


# --- AC 3: comments and strings are blanked before matching ----------------

COMMENTED = (
    "# eval(user_input) is forbidden here\n"
    'doc = "never call os.system(cmd) or cursor.execute(f\\"...\\")"\n'
    "x = 1  # subprocess.run(cmd, shell=True)\n"
)


def test_sinks_in_comments_and_strings_are_not_hits():
    assert sink_hits("a.py", COMMENTED, tables()) == ()


def test_sabotage_without_blanking_the_same_text_hits(monkeypatch):
    monkeypatch.setattr(metrics_module, "strip", lambda text, syntax, **_: text)
    assert {hit.cwe for hit in sink_hits("a.py", COMMENTED, tables())} == SINK_CWES


METHODS = "model.eval(batch)\nframe.eval(expr)\n"


def test_a_same_named_method_is_not_a_sink():
    assert sink_hits("a.py", METHODS, tables()) == ()


def test_sabotage_without_the_not_after_dot_guard_methods_hit():
    unguarded = {
        suffix: tuple(
            dataclasses.replace(p, regex=re.compile(token_regex(p.token)))
            for p in patterns
        )
        for suffix, patterns in tables().sinks.items()
    }
    sabotaged = dataclasses.replace(tables(), sinks=unguarded)
    assert len(sink_hits("a.py", METHODS, sabotaged)) == 2


def test_minified_lines_are_ignored():
    assert sink_hits("a.js", "eval(code);" + " " * 600 + "\n", tables()) == ()


def test_patterns_carry_their_token_and_cannot_inject_regex():
    for patterns in tables().sinks.values():
        for pattern in patterns:
            assert isinstance(pattern, SinkPattern)
            assert pattern.regex.pattern.endswith(token_regex(pattern.token))


# --- AC 2: the evidence-local metric with per-hit citation -----------------

UNSAFE = (
    "def find(cursor, user):\n"
    "    cursor.execute(f\"SELECT * FROM u WHERE n = '{user}'\")\n"
)
SAFE = (
    "def find(cursor, user):\n"
    '    cursor.execute("SELECT * FROM u WHERE n = %s", (user,))\n'
)


def test_metric_counts_the_unsafe_twin_with_path_line_and_cwe():
    found = sink_metric(pack({"app/db.py": UNSAFE}))
    assert found.kind == EVIDENCE_LOCAL
    assert found.outcome == 1
    assert found.computed_from == ("app/db.py:1-2",)
    assert "app/db.py:2 CWE-89 (https://cwe.mitre.org/data/definitions/89.html)" in (
        found.derivation
    )


def test_metric_is_zero_on_the_safe_twin_and_cites_what_it_scanned():
    found = sink_metric(pack({"app/db.py": SAFE}))
    assert found.outcome == 0
    assert found.computed_from == ("app/db.py:1-2",)


def test_metric_tags_test_path_hits_and_still_counts_them():
    found = sink_metric(pack({"app/db.py": UNSAFE, "tests/test_db.py": UNSAFE}))
    assert found.outcome == 2
    assert "tests/test_db.py:2 CWE-89" in found.derivation
    assert (
        "tests/test_db.py:2 CWE-89 (https://cwe.mitre.org/data/definitions/89.html)"
        " [test path]" in found.derivation
    )
    assert (
        "app/db.py:2 CWE-89 (https://cwe.mitre.org/data/definitions/89.html)"
        " [test path]" not in found.derivation
    )


def test_metric_computes_over_a_truncated_pack():
    assert sink_metric(pack({"app/db.py": UNSAFE}, truncated=True)).outcome == 1


def test_metric_abstains_when_no_code_was_scanned():
    found = sink_metric(pack({"README.md": "eval(x)\n"}))
    assert found.abstained
    assert "no code was scanned" in found.abstention.reason


# --- The real surface: the security pack quotes the sink lines --------------

REPO_FILES = {
    "pyproject.toml": '[project]\nname = "x"\n',
    "app/db.py": (
        "import subprocess\n\n\ndef find(cursor, user):\n"
        "    cursor.execute(f\"SELECT * FROM u WHERE n = '{user}'\")\n\n\n"
        "def run(cmd):\n    return subprocess.run(cmd, shell=True)\n"
    ),
    "app/safe.py": SAFE + "# eval(x)\n",
}


def _repo(tmp_path: Path) -> Path:
    for relative, text in REPO_FILES.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_security_pack_quotes_each_sink_line_and_the_metric_reads_it(tmp_path):
    evidence = run_dimension(DIMENSIONS["security"], _repo(tmp_path), scope="project")
    refs = {excerpt.ref: excerpt.text for excerpt in evidence.excerpts}
    assert "app/db.py:5-5" in refs and "cursor.execute(f" in refs["app/db.py:5-5"]
    assert "app/db.py:9-9" in refs and "shell=True" in refs["app/db.py:9-9"]
    assert not any(ref.startswith("app/safe.py") for ref in refs)
    found = sink_metric(evidence)
    assert found.outcome == 2
    assert set(found.computed_from) == {"app/db.py:5-5", "app/db.py:9-9"}


def test_sabotage_without_sink_excerpts_the_pack_has_nothing_to_count(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(security_module, "_sink_excerpts", lambda *_a: iter(()))
    evidence = run_dimension(DIMENSIONS["security"], _repo(tmp_path), scope="project")
    assert not any(e.path == "app/db.py" for e in evidence.excerpts)
    assert sink_metric(evidence).abstained


def test_sink_excerpts_per_file_are_capped_with_a_warning(tmp_path):
    many = "".join(f"eval(x{i})\n" for i in range(25))
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    (tmp_path / "app").mkdir()
    (tmp_path / "app/many.py").write_text(many)
    evidence = run_dimension(DIMENSIONS["security"], tmp_path, scope="project")
    quoted = [e for e in evidence.excerpts if e.path == "app/many.py"]
    assert len(quoted) == security_module.MAX_SINK_EXCERPTS_PER_FILE
    assert any("app/many.py" in warning for warning in evidence.warnings)


def test_cli_score_reports_sink_hits_for_the_security_dimension(tmp_path):
    repo = _repo(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from easy_verifier.adapters.cli import main; "
            f"sys.exit(main(['score', '--repo', {str(repo)!r}, '--scope', 'project']))",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stderr
    (found,) = [
        m
        for m in json.loads(completed.stdout)["metrics"]["metrics"]
        if m["name"] == "sink_hits_observed" and m["dimension"] == "security"
    ]
    assert found["outcome"] == {"abstained": False, "value": 2}
    assert "app/db.py:5 CWE-89" in found["derivation"]
    assert "app/db.py:9 CWE-78" in found["derivation"]
