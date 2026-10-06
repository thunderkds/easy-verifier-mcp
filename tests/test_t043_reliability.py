"""T043 - the ``reliability`` dimension (FR-050..052): areas #6, #12, #13,
#15 (partial) and #32 (partial).

AC1 discoverable with its roles; AC2 cited rules (swallowed errors, outbound
calls without a timeout, retries without backoff, queries in loops) plus the
#32 documentation rule, with #6 transaction / idempotency code quoted as
evidence and never scored; AC3 every language token lives in the registry;
AC5 a fixture meeting every rule rates 100 and one with none of the roles
abstains with named misses. Each sabotage pair varies only the predicate it
pins.
"""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    COVERAGE_FLOORS,
    DOCUMENTATION_RULES,
    PROJECT_DEFAULT,
    RATING_RULES,
)
from easy_verifier.core.metric_tables import (
    FIELD_METRICS,
    OPTIONAL_FIELDS,
    curated_metric_tables,
)
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    METRIC_DEFINITIONS,
    SAMPLED_METRICS,
    MetricAbstention,
    compute_metrics,
    reliability_findings,
)
from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.registry import ENTRY_FIELDS, load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.dimensions import list_dimensions, reliability

REPO_ROOT = Path(__file__).resolve().parents[1]

SWALLOWED = "swallowed_errors_observed"
TIMEOUTS = "outbound_calls_without_timeout_observed"
RETRIES = "retries_without_backoff_observed"
LOOPS = "queries_in_loops_observed"
RULE_METRICS = (SWALLOWED, TIMEOUTS, RETRIES, LOOPS)
FIELDS = (
    "swallowed_errors",
    "outbound_calls",
    "call_timeouts",
    "client_timeouts",
    "retry_calls",
    "retry_backoff",
    "query_calls",
    "loop_keywords",
    "transaction_markers",
)


def findings(path: str, text: str):
    found = reliability_findings(path, text, curated_metric_tables())
    assert found is not None
    return found


def pack(files, *, dimension="reliability"):
    return EvidencePack(
        dimension=dimension,
        mode="standalone",
        scope="project",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(path, 1, len(text.splitlines()), text)
            for path, text in files.items()
        ),
        sources_sought=("x",),
        sources_found=("x",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=False,
        omitted_count=0,
        truncation=TruncationRecord(truncated=False, omitted_count=0),
    )


def metric(files, name):
    (found,) = compute_metrics(pack(files), curated_metric_tables()).by_name(name)
    return found


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
    return json.loads(completed.stdout)


def _reliability(payload: dict) -> dict:
    return next(r for r in payload["ratings"] if r["dimension"] == "reliability")


# --- AC1: discoverable, with its roles ---------------------------------------


def test_reliability_is_discoverable_with_purpose_and_roles():
    (found,) = [d for d in list_dimensions() if d.name == "reliability"]
    assert found.purpose
    assert [role.name for role in found.roles] == [
        reliability.SOURCE,
        reliability.HTTP,
        reliability.DATABASE,
        "readme",
    ]
    assert found.sources_sought == tuple(role.name for role in found.roles)


# --- AC2: rules, floor and the documentation rule ----------------------------


def test_rules_are_cited_weighted_and_labelled_by_area():
    rules = RATING_RULES["reliability"]
    assert list(rules) == list(RULE_METRICS)
    assert sum(rule.weight for rule in rules.values()) == 100
    assert rules[SWALLOWED].area == AREAS[11]
    assert rules[TIMEOUTS].area == AREAS[12]
    assert rules[RETRIES].area == AREAS[12]
    assert rules[LOOPS].area == AREAS[14]
    for rule in rules.values():
        assert (rule.comparison, rule.threshold) == ("at_most", 0)
        assert rule.threshold_citation == PROJECT_DEFAULT
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    labels = {
        name: " ".join(c.label for c in rule.metric_citation)
        for name, rule in rules.items()
    }
    assert "CWE-390" in labels[SWALLOWED] and "ISO/IEC 5055" in labels[SWALLOWED]
    assert "CWE-400" in labels[TIMEOUTS]
    assert "Google SRE" in labels[RETRIES]
    assert "CWE-1050" in labels[LOOPS] and "ISO/IEC 5055" in labels[LOOPS]


def test_floor_is_the_user_approved_quarter_inclusive():
    floor = COVERAGE_FLOORS["reliability"]
    assert (floor.value, floor.boundary) == (0.25, "inclusive")


def test_business_continuity_is_a_documentation_rule_only():
    (rule,) = DOCUMENTATION_RULES["reliability"]
    assert rule.area == AREAS[31]
    assert "ISO 22301" in rule.citation[0].label
    # #6 needs judgment: no rule may score it (evidence only, user decision).
    assert all(r.area != AREAS[5] for r in RATING_RULES["reliability"].values())


def test_rule_metrics_are_declared_evidence_local_and_sampled():
    declared = {d.name: d for d in METRIC_DEFINITIONS}
    for name in RULE_METRICS:
        assert declared[name].kind == EVIDENCE_LOCAL
    assert SAMPLED_METRICS["reliability"] == RULE_METRICS


# --- AC3: patterns in the registry, not the dimension module ------------------


@pytest.mark.parametrize("field", FIELDS)
def test_fields_are_optional_registry_fields_feeding_the_rules(field):
    assert field in ENTRY_FIELDS
    assert field in OPTIONAL_FIELDS
    if field != "transaction_markers":
        assert set(FIELD_METRICS[field]) & set(RULE_METRICS)


def test_curated_values_load_cleanly_with_https_citations():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    assert registry.warnings == ()
    declared = 0
    for entry in registry.languages.values():
        for field in FIELDS:
            for cited in entry.fields.get(field, ()):
                declared += 1
                assert cited.citation_url.startswith("https://"), (entry.name, field)
    assert declared


def test_dimension_module_holds_no_language_tokens():
    source = inspect.getsource(reliability)
    assert "\nimport re\n" not in source
    tokens = ("requests.get", "fetch (", "except ", "catch (", "findUnique", "@retry")
    for token in tokens:
        assert token not in source.split('"""', 2)[-1], token


# --- #12 swallowed errors ------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("src/a.py", "try:\n    go()\nexcept Exception:\n    pass\n"),
        ("src/a.py", "try:\n    go()\nexcept:\n    pass\n"),
        ("src/a.py", "try:\n    go()\nexcept (OSError, ValueError) as e:\n    pass\n"),
        ("src/a.ts", "try {\n  go();\n} catch (e) {\n}\n"),
        ("src/a.ts", "try { go(); } catch (e: unknown) {}\n"),
        ("src/a.ts", "try { go(); } catch {}\n"),
        ("src/a.ts", "go().catch(() => {});\n"),
        ("src/A.java", "try { go(); } catch (IOException e) {}\n"),
        ("src/a.go", "if err != nil {\n}\n"),
        ("src/a.rb", "begin\n  go\nrescue => e\nend\n"),
    ],
)
def test_an_empty_handler_is_swallowed(path, text):
    assert len(findings(path, text).swallowed) == 1


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("src/a.py", "try:\n    go()\nexcept Exception:\n    log.exception('x')\n"),
        ("src/a.py", "s = 'except Exception: pass'\n"),
        ("src/a.ts", "try { go(); } catch (e) { log(e); }\n"),
        ("src/a.ts", "try { go(); } catch (e) { /* expected: optional */ }\n"),
        ("src/a.ts", "try { go(); } catch (e) {} // expected: optional\n"),
        ("src/a.py", "try:\n    go()\nexcept OSError:\n    pass  # reported later\n"),
        ("src/a.ts", "go().catch((e) => report(e));\n"),
        # Go's idiomatic handling is never a swallowed error (user decision).
        ("src/a.go", "if err != nil {\n\treturn err\n}\n"),
        ("src/a.go", 'if err != nil {\n\treturn fmt.Errorf("x: %w", err)\n}\n'),
    ],
)
def test_handled_or_commented_errors_are_not_swallowed(path, text):
    assert findings(path, text).swallowed == ()


def test_swallowed_metric_counts_lines_and_abstains_without_scannable_code():
    bad = "def f():\n    try:\n        go()\n    except Exception:\n        pass\n"
    found = metric({"src/app/a.py": bad}, SWALLOWED)
    assert found.outcome == 1
    assert "src/app/a.py:4" in found.derivation
    good = bad.replace("pass", "raise")
    assert metric({"src/app/a.py": good}, SWALLOWED).outcome == 0
    none = metric({"README.md": "# x\n"}, SWALLOWED)
    assert isinstance(none.outcome, MetricAbstention)


def test_test_files_are_not_scanned_for_swallowed_errors():
    text = "try:\n    go()\nexcept Exception:\n    pass\n"
    found = metric({"src/app/a.py": "x = 1\n", "tests/test_a.py": text}, SWALLOWED)
    assert found.outcome == 0


# --- #13 outbound calls without a timeout ---------------------------------------


@pytest.mark.parametrize(
    ("path", "text", "unbounded"),
    [
        ("src/a.py", "r = requests.get(url)\n", 1),
        ("src/a.py", "r = requests.get(url, timeout=5)\n", 0),
        ("src/a.py", "r = requests.post(\n    url,\n    timeout=(3, 9),\n)\n", 0),
        ("src/a.ts", "const r = await fetch(url);\n", 1),
        ("src/a.ts", "r = fetch(u, { signal: AbortSignal.timeout(5) });\n", 0),
        ("src/a.ts", "const r = await axios.get(url, { timeout: 5000 });\n", 0),
        ("src/a.ts", "const r = await axios.get(url);\n", 1),
        ("src/a.go", "resp, err := http.Get(url)\n", 1),
        ("src/a.go", "c := &http.Client{\n\tTimeout: 5 * time.Second,\n}\n", 0),
        ("src/a.go", "c := &http.Client{}\n", 1),
        # bryony (real repo): Node core requests and jQuery ajax
        ("src/a.js", "let req = http.request(opts, function (res) {});\n", 1),
        ("src/a.js", "$.ajax({ url: u, timeout: 5000 });\n", 0),
        ("src/a.js", "$.ajax({ url: u, type: 'POST' });\n", 1),
        ("src/a.js", "$.post('/api/charts/mark', { id: 1 });\n", 1),
    ],
)
def test_outbound_calls_need_a_deadline_in_the_call(path, text, unbounded):
    found = findings(path, text)
    assert len(found.calls) == 1
    assert len(found.unbounded_calls) == unbounded


def test_a_client_wide_timeout_in_the_file_honours_its_wrapper_calls():
    wrapper = (
        "export async function get(url) {\n"
        "  const controller = new AbortController();\n"
        "  setTimeout(() => controller.abort(), 5000);\n"
        "  return fetch(url, options);\n"
        "}\n"
    )
    assert findings("src/http.ts", wrapper).unbounded_calls == ()
    without = wrapper.replace("new AbortController()", "makeController()")
    assert len(findings("src/http.ts", without).unbounded_calls) == 1
    node = "const req = https.request(opts, onResponse);\nreq.setTimeout(5000);\n"
    assert findings("src/a.js", node).unbounded_calls == ()


def test_timeout_metric_abstains_without_any_outbound_call():
    found = metric({"src/app/a.py": "def f():\n    return 1\n"}, TIMEOUTS)
    assert isinstance(found.outcome, MetricAbstention)
    assert "no outbound call" in found.outcome.reason
    bad = metric({"src/app/a.py": "def f():\n    return requests.get(u)\n"}, TIMEOUTS)
    assert bad.outcome == 1


# --- #13 retries without backoff ------------------------------------------------


@pytest.mark.parametrize(
    ("text", "unbacked"),
    [
        ("@retry\ndef f():\n    go()\n", 1),
        ("@retry(stop=stop_after_attempt(3))\ndef f():\n    go()\n", 1),
        ("@retry(wait=wait_random(), stop=stop_after_attempt(3))\ndef f(): ...\n", 0),
        ("r = Retry(total=3)\n", 1),
        ("r = Retry(total=3, backoff_factor=0.5)\n", 0),
    ],
)
def test_retries_need_backoff(text, unbacked):
    found = findings("src/a.py", text)
    assert len(found.retries) == 1
    assert len(found.unbacked_retries) == unbacked


def test_retry_metric_abstains_without_any_retry():
    found = metric({"src/app/a.py": "x = 1\n"}, RETRIES)
    assert isinstance(found.outcome, MetricAbstention)


# --- #15 queries in loops --------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "text", "in_loop"),
    [
        ("src/a.py", "for u in users:\n    cur.execute(q, (u,))\n", 1),
        ("src/a.py", "while more:\n    rows = (\n        cur.execute(q)\n    )\n", 1),
        ("src/a.py", "cur.execute(q)\nfor row in cur:\n    print(row)\n", 0),
        # the loop header runs the query once
        ("src/a.py", "for row in session.query(User):\n    print(row)\n", 0),
        ("src/a.py", "rows = cur.execute(q)\n", 0),
        ("src/a.ts", "for (const i of ids) {\n  await db.u.findUnique({ i });\n}\n", 1),
        ("src/a.ts", "await Promise.all(ids.map((i) => db.u.findUnique({ i })));\n", 1),
        ("src/a.ts", "const us = await db.u.findMany();\nus.map((u) => u.id);\n", 0),
        ("src/a.go", "for _, id := range ids {\n\trow := db.QueryRow(q, id)\n}\n", 1),
        ("src/A.java", "for (Long id : ids) {\n    repo.findById(id);\n}\n", 1),
    ],
)
def test_a_query_in_a_loop_body_is_counted(path, text, in_loop):
    found = findings(path, text)
    assert len(found.queries) >= 1
    assert len(found.queries_in_loops) == in_loop


def test_a_loop_outside_the_enclosing_function_does_not_count():
    text = (
        "for x in xs:\n"
        "    def load(i):\n"
        "        return cur.execute(q, (i,))\n"
    )
    assert findings("src/a.py", text).queries_in_loops == ()


def test_loop_metric_abstains_without_any_query():
    found = metric({"src/app/a.py": "x = 1\n"}, LOOPS)
    assert isinstance(found.outcome, MetricAbstention)


# --- #6 evidence only --------------------------------------------------------------


def test_transaction_and_idempotency_markers_are_found_but_never_scored():
    text = (
        "from django.db import transaction\n\n"
        "def pay(idempotency_key):\n"
        "    with transaction.atomic():\n"
        "        save()\n"
    )
    assert findings("src/a.py", text).transactions == (3, 4)
    names = {d.name for d in METRIC_DEFINITIONS}
    assert not any("transaction" in name or "idempoten" in name for name in names)


# --- the dimension over real files -------------------------------------------------


GOOD_FILES = {
    "README.md": "# svc\n\nA service.\n",
    "docs/business-continuity.md": "# Degraded modes\n\nWhen the API is down we...\n",
    "src/app/client.py": (
        "import requests\n\n\n"
        "def fetch_user(uid):\n"
        "    return requests.get(URL + uid, timeout=5)\n"
    ),
    "src/app/jobs.py": (
        "from tenacity import retry, wait_exponential\n\n\n"
        "@retry(wait=wait_exponential())\n"
        "def sync():\n"
        "    try:\n"
        "        push()\n"
        "    except OSError:\n"
        "        log.warning('push failed')\n"
        "        raise\n"
    ),
    "src/app/store.py": (
        "from django.db import transaction\n\n\n"
        "def load(cur, ids):\n"
        "    cur.execute('select * from u where id = any(%s)', (ids,))\n"
        "    return cur.fetchall()\n\n\n"
        "def pay(idempotency_key):\n"
        "    with transaction.atomic():\n"
        "        save(idempotency_key)\n"
    ),
}


def test_every_rule_met_rates_100_with_its_document_present(tmp_path):
    rating = _reliability(_score(_repo(tmp_path, GOOD_FILES)))
    assert rating["kind"] == "rating", rating
    assert rating["value"] == 100
    assert [i["metric_name"] for i in rating["inputs"]] == list(RULE_METRICS)
    assert all(i["passed"] for i in rating["inputs"])
    (doc,) = rating["documentation"]
    assert (doc["status"], doc["file"]) == ("present", "docs/business-continuity.md")


def test_breaking_one_rule_loses_exactly_its_weight(tmp_path):
    files = dict(GOOD_FILES)
    files["src/app/client.py"] = files["src/app/client.py"].replace(", timeout=5", "")
    rating = _reliability(_score(_repo(tmp_path, files)))
    assert rating["value"] == 100 - RATING_RULES["reliability"][TIMEOUTS].weight


def test_no_role_filled_abstains_below_the_floor_with_named_misses(tmp_path):
    payload = _score(_repo(tmp_path, {"data/values.csv": "a,b\n1,2\n"}))
    rating = _reliability(payload)
    assert rating["reason_code"] == "below_coverage_floor"
    missed = {miss["source"] for miss in rating["sources_missing"]}
    assert missed == {
        reliability.SOURCE,
        reliability.HTTP,
        reliability.DATABASE,
        "readme",
    }
    assert len(payload["ratings"]) == len(COVERAGE_FLOORS)


def test_pack_quotes_hits_and_transaction_evidence_and_fills_code_roles(tmp_path):
    files = dict(GOOD_FILES)
    files["src/app/client.py"] = files["src/app/client.py"].replace(", timeout=5", "")
    root = _repo(tmp_path, files)
    pack = run_dimension(reliability.DESCRIPTOR, root, "project")
    assert set(pack.sources_found) == {
        reliability.SOURCE,
        reliability.HTTP,
        reliability.DATABASE,
        "readme",
    }
    quoted = {
        (e.path, line)
        for e in pack.excerpts
        for line in range(e.start_line, e.end_line + 1)
    }
    assert ("src/app/client.py", 5) in quoted  # the call without a timeout
    assert ("src/app/store.py", 10) in quoted  # transaction.atomic, #6 evidence
    assert "docs/business-continuity.md" in pack.files_read


def test_a_library_without_calls_or_queries_names_the_unfilled_code_roles(tmp_path):
    root = _repo(
        tmp_path,
        {"README.md": "# lib\n", "src/lib/util.py": "def add(a, b):\n    return a\n"},
    )
    pack = run_dimension(reliability.DESCRIPTOR, root, "project")
    assert set(pack.sources_found) == {reliability.SOURCE, "readme"}
    reasons = {m.source: m.reason for m in pack.sources_missing}
    assert "outbound" in reasons[reliability.HTTP]
    assert "database" in reasons[reliability.DATABASE]


def test_an_unresolved_narrow_scope_reads_nothing_and_names_every_source(tmp_path):
    root = _repo(tmp_path, GOOD_FILES)
    pack = run_dimension(reliability.DESCRIPTOR, root, "task")  # no task id
    assert pack.excerpts == () and pack.coverage_score == 0
    assert {m.source for m in pack.sources_missing} == set(reliability.SOURCES_SOUGHT)
    assert any("could not be resolved" in w for w in pack.warnings)
