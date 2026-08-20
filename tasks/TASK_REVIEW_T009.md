# TASK_REVIEW — T009: test-strategy dimension

> Sibling of `tasks/TASK_GUIDE_T009.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t009_test_strategy.py` — 17 tests, one per Success Criterion (1–4) plus AC #1/#5/#6/#7/#8/#9, the ranked-cap ordering guard, the declared-source probe guard, and the missing-vs-bogus selector pair. `PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q` → `17 passed in 0.19s` (2026-08-20T11:34:02Z, exit 0). |
| Verification command run | ☑ pass | See the AFTER capture below: `pytest tests/test_t009_test_strategy.py -q` → `17 passed`, and `python -m easy_verifier.adapters.cli test-strategy --repo .` now prints a real pack (was `invalid choice: 'test-strategy'` in BEFORE). |
| Negative cases hold | ☑ pass | Empty repo → `coverage_score 0.0`, full miss list, no estimate. `--scope task` with the flag **omitted** → `resolved_scope=None`, zero files read, explicit "could not be resolved" warning (no widening); with it **empty** and with it **bogus** (`T999`) → empty task scope, zero files read. `--scope changes` without `--ref` → same refusal. Coverage artifacts (`coverage.xml`, `.coverage`, `htmlcov/`) named in a warning but never read and their figures never serialized. |
| verify | ☐ pass / ☐ fail / ☐ N/A | Not run by the implementer — `verify` is user-invocation-only. The CLI was driven manually with each selector present, omitted, empty and bogus (see Negative cases) as a stand-in; Stage 5 `verify` still owed. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | Changed set: `src/easy_verifier/dimensions/test_strategy.py` (new), `src/easy_verifier/dimensions/__init__.py` (one registry row), `tests/test_t009_test_strategy.py` (new), `tests/test_t001_pipeline.py` (registry expectation only). `core/**`, `_doc_extract.py` and `.claude/hooks/**` untouched. |
| Full smoke suite still green (no regression) | ☑ pass | `PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest -q` → `311 passed in 1.31s`, exit 0 (baseline 294 + 17 new). `ruff check .` → `All checks passed!`. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-20T11:26:38Z on `feat/t009-test-strategy` at `8d96335`, before any
implementation commit — the guide's Verification Command, run in the worktree):

```
$ date -u
Thu Aug 20 11:26:38 AM UTC 2026
$ git log --oneline -1
8d96335 docs(T009): carry Supervisor gate sign-off onto the branch
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q
ERROR: file or directory not found: tests/test_t009_test_strategy.py

no tests ran in 0.00s
pytest exit=4
$ PYTHONPATH=src python -m easy_verifier.adapters.cli test-strategy --repo .
usage: easy-verifier [-h] [--repo REPO]
                     [--scope {changes,project,task,worktree}] [--ref REF]
                     [--task-id TASK_ID] [--budget-bytes BUDGET_BYTES]
                     {architecture,code-quality,requirement-fidelity,security,solution-fit}
easy-verifier: error: argument dimension: invalid choice: 'test-strategy' (choose from 'architecture', 'code-quality', 'requirement-fidelity', 'security', 'solution-fit')
```

Neither half of the Verification Command can run: the test file does not exist, and `test-strategy`
is not a dimension the CLI accepts.

**AFTER** (2026-08-20T11:34:02Z, same commands, same worktree):

```
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q
.................                                                        [100%]
17 passed in 0.19s
exit=0
$ PYTHONPATH=src python -m easy_verifier.adapters.cli test-strategy --repo . | head -30
{
  "dimension": "test-strategy",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
    "pyproject.toml",
    "tests/conftest.py",
    "src/easy_verifier/dimensions/test_strategy.py",
    "tests/test_t001_pipeline.py",
    "tests/test_t002_context.py",
    "tests/test_t003_scope.py",
    "tests/test_t004_redact.py",
    "tests/test_t005_budget.py",
    "tests/test_t006_findings.py",
    "tests/test_t007_doc_dimensions.py",
    "tests/test_t008_security.py",
    "tests/test_t009_test_strategy.py"
  ],
  "excerpts": [
    {
      "path": "pyproject.toml",
      "start_line": 20,
      "end_line": 29,
      "text": "dev = [\"pytest>=7.4\", \"ruff>=0.6\"]\n\n[tool.setuptools.packages.find]\nwhere = [\"src\"]\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n..."
    },
```

The dimension is now a CLI choice, the pytest configuration is cited at its real
lines (`pyproject.toml:20-29`, the `[tool.pytest.ini_options]` block), and the
repo's own test tree is read as evidence.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]

---

## Stage 4 Review

### P1 — Cross-subproject false correspondence (found by the Supervisor, fixed)

**Finding.** `_correspondence` indexed test basenames across the **whole repository**, so a test in
one independent subproject was reported as covering a same-named source in another. On the reviewer's
fixture the pack claimed `svc_a/src/payments.py -> svc_b/tests/test_payments.py`, telling the calling
agent that a file nothing in `svc_a` tests was covered — the exact "confident-but-unfounded claim"
the guide's Approach section forbids, and the unticked Edge Case Checklist row *"Monorepo with several
independent test suites in subprojects"*. The Go branch already refused a cross-directory
`foo_test.go`; Python, JS/TS, Ruby, Java and C# had no guard at all.

**Reproduced before fixing.** The new regression test was written first and run against the pre-fix
commit `832a6ef`:

```
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q \
    -k "monorepo or project_root_src"
>       assert "svc_a/src/payments.py ->" not in reason
E       AssertionError: ... 'svc_a/src/payments.py -> svc_b/tests/test_payments.py; no test
E       discovered for 1 file(s): svc_a/src/orders.py'
1 failed, 1 passed, 17 deselected in 0.08s
```

The second selected test (`test_project_root_src_and_tests_split_still_matches`) passed pre-fix: it is
the pin ensuring the fix cannot trade this defect for the opposite one.

**Fix.** A name match is now accepted only when both files resolve to the same project
(`_project_boundary`). The boundary takes the **more specific** of two signals, because either alone
mis-reads a real layout: the deepest ancestor holding a manifest (`pyproject.toml`, `package.json`,
`go.mod`, `Cargo.toml`, …), and everything above the file's first *layout* segment (`src`, `tests`,
`pkg`, `__tests__`, …). That keeps `src/foo.py -> tests/test_foo.py` — including a nested
`src/deep/pkg/bar.py -> tests/unit/test_bar.py` — while separating `svc_a/src` from `svc_b/tests`
even when neither subproject carries a manifest of its own. A cross-boundary match is reported as
"no test discovered", never guessed. The Go same-directory rule is retained on top.

**Verified on the reviewer's exact fixture** (2026-08-20T11:39:10Z, via the real CLI):

```
$ python -m easy_verifier.adapters.cli test-strategy --repo <mono> --scope project
... test discovered for 1 file(s): colo/widget.py -> colo/widget_test.py;
    no test discovered for 2 file(s): svc_a/src/orders.py, svc_a/src/payments.py
```

**Regression tests**: `test_monorepo_subprojects_do_not_borrow_each_others_tests` and
`test_project_root_src_and_tests_split_still_matches` in `tests/test_t009_test_strategy.py`.

**Post-fix suite**: `python -m pytest -q` → `313 passed in 1.29s`, exit code 0 read directly (311 + 2
new). `ruff check .` → `All checks passed!`.

**Root cause worth carrying forward**: every correspondence fixture in the original 534-line suite
used a single flat project, where repo-wide and project-scoped matching are indistinguishable — the
same blind spot shape as T008's cap test built from 205 identical files. A selection rule needs a
fixture where the right answer and the wrong answer are *different files*.


---

## Stage 4 — Supervisor close-out (2026-08-20)

**code-review (mandatory): P0 0 / P1 1 (fixed, `b50865a`) / P2 0 / P3 0.**
**security-review: ☐ N/A** — Low risk per the guide's own Completion Checklist; this dimension opens
no new read surface (it *refuses* coverage artifacts) and adds no subprocess, network or path-resolver
primitive.
**blast-radius / migration-safety: ☐ N/A** — Low risk, no sensitive-data handling, no DB.

### P1 — cross-subproject false correspondence (conf 100, reproduced pre-fix)

`_correspondence` indexed tests by basename across the whole repository, so `svc_b/tests/test_payments.py`
was reported as covering `svc_a/src/payments.py` in a two-service repo. This is the failure the guide's
Approach section names outright — *"a wrong correspondence is worse than an admitted gap"* — and Edge
Case Checklist item *"Monorepo with several independent test suites in subprojects"*, which was unticked
and untested.

Notable: the author **had already identified this hazard** and guarded it for Go, commenting that
matching a `foo_test.go` from an unrelated package would be a fabricated correspondence. The reasoning
was right; it was simply not generalised beyond Go. Python, JS/TS, Ruby, Java and C# were unguarded.

**Why the suite could not see it**: all correspondence fixtures used a single flat project, where
repo-wide matching and project-scoped matching are indistinguishable. Same shape as T008's cap test
using 205 identical files. **A selection rule needs a fixture where the right answer and the wrong
answer are different files.**

**Fix**: `_project_boundary` takes the more specific (longer) of two ancestor signals — deepest ancestor
holding a manifest, or everything above the file's first layout segment (`src`, `tests`, `pkg`, `lib`,
`cmd`, `internal`, `__tests__`). Either signal alone mis-reads a real layout: manifests alone fail on a
manifest-less monorepo, layout segments alone fail when a subproject manifest sits below such a segment.
Cross-boundary pairs report "no test discovered" rather than guessing. Go's same-directory rule retained
on top. The agent flagged this refinement to the Supervisor's prescribed approach before building it.

### Independent re-verification by the Supervisor, at the CLI

Cases 1, 2 and 4 are the agent's; **case 3 was constructed by the Supervisor after the fix**, so it was
not a fixture the implementation was tuned against.

| Fixture | Result |
|---|---|
| Manifest-less monorepo (`svc_a/src` + `svc_b/tests`) | `no test discovered for 2 file(s): svc_a/src/orders.py, svc_a/src/payments.py` — false match gone |
| Flat `src/` + `tests/` | `src/foo.py -> tests/test_foo.py` — unchanged, no overcorrection |
| **Manifest monorepo, both services holding a same-named test** | `svc_a/src/payments.py -> svc_a/tests/test_payments.py` **only** — matches its own suite, not `svc_b`'s |
| Deep nesting across a root split (`src/deep/pkg/bar.py`) | `-> tests/unit/test_bar.py` — a naive same-directory rule would have killed this |

Do-not-regress list re-checked at the CLI: coverage artifacts still named-but-unopened with `0.87`/`91%`
absent from the pack; `--scope task` with the selector omitted still yields `files_read []` plus the
unresolved warning; AC #4 still returns the guide's Acceptance Criteria excerpt under kit-aware task
scope. Suite `313 passed`, exit `0` read directly; `ruff check .` exit `0`.

### Accepted residue (recorded, not fixed)

- **Pseudo-source channel for AC #3.** Per-run scope-file names cannot enter the miss list directly —
  `pipeline._missing_sources` drops any `SourceMiss` whose source is not in the static `sources_sought`.
  Rather than propose a core change, the agent declared `CORRESPONDENCE_SOURCE` as a permanent
  pseudo-source whose *reason* carries both sides of the result, following T008's `git history` precedent.
  Accepted: no core change needed, and the miss list stays an exact partition of `sources_sought`.
- **Correspondence names are capped at `MAX_NAMED_FILES` (10).** With 25 unmatched files the reason
  renders 10 names plus `(+15 more)` and an exact `25 file(s)` count. Truthful and bounded per FR-011b,
  but a reviewing agent cannot act on the unnamed remainder without narrowing scope.
- **Discovery is strictly scope-bounded.** Under `changes`/`task`/`worktree` the dimension does not walk
  outside the resolved file set; a warning states that a corresponding test living elsewhere is reported
  as *not discovered*, which is not the same as absent. Trades a possible false gap for a guaranteed
  absence of false coverage claims — the correct direction for this project.
- **A production module named `test_*.py` is classified as a test file** (this dimension's own source is
  visible as such in the AFTER capture). That is pytest's own convention; requiring a `tests/` ancestor
  would drop every co-located suite.

### Pre-existing, not T009's

`files_read` lists `tasks/TASK_GUIDE_T009.md` twice under `task` scope. Reproduces on `architecture`,
`code-quality` and `security`. Left alone.

**Stage 4 closed. Stage 5 `verify` is outstanding — it is user-invocation-only.**
