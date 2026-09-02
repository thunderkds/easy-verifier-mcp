# TASK_REVIEW — T011: Dimension discovery operation

> Reviewer-owned evidence for `TASK_GUIDE_T011.md`.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t011_discovery.py` — 8 tests cover the seven rich records, descriptor-derived values, no-argument API, deterministic order, automatic discovery of a newly added module, explicit helper exclusion, loud failure for a malformed public module, honest empty-source metadata, and deterministic CLI JSON. `8 passed in 0.03s`. |
| Verification command run | ☑ pass | `PATH=<main>/.venv/bin:$PATH PYTHONPATH=src pytest tests/test_t011_discovery.py -q && PYTHONPATH=src python -m easy_verifier.adapters.cli list-dimensions` → `8 passed in 0.03s`, exit 0; CLI emitted seven records with `name`, `purpose`, and `sources_sought`. |
| Negative cases hold | ☑ pass | A temporary public module appears without editing `DIMENSIONS`; a public module lacking `DESCRIPTOR` raises `RuntimeError` naming that module; `_doc_extract.py` stays excluded by the explicit leading-underscore rule; an empty `sources_sought` tuple remains visible. The dynamic-module test would fail if discovery reverted to the hand-maintained execution map. |
| verify | ☑ pass | Public-boundary verification passed: two CLI invocations serialize byte-identical JSON, the exact guide command exits 0, and T012's combined-pack behavior remains covered by its full test file. T011 is C0; the unavailable Claude-only `verify` skill was substituted with the exact executable verification command. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `dimensions/__init__.py`, `adapters/cli.py`, the user-authorized T012 compatibility seam in `core/synthesis.py`, and T018's README truth boundary; reviewed T011/T012/T018 focused tests and the guide update. No individual dimension, pipeline, model, hook, memory, report, or target-repository reader changed. Manual structured review: P0 0 / P1 1 fixed / P2 0 / P3 0. |
| Full smoke suite still green (no regression) | ☑ pass | Final tree: `PYTHONPATH=src <main>/.venv/bin/python -m pytest -q` → **418 passed in 7.06s**, exit 0. `ruff check src tests` → `All checks passed!`; `ruff format --check src tests` → `37 files already formatted`. T011+T012+T018 focused coverage → `42 passed`. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend metadata and JSON output; no UI or rendered document. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI surface. |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI surface. |

---

## Demonstration

**BEFORE** (2026-09-02T04:01:35Z, before implementation):

```text
$ PYTHONPATH=src python -m easy_verifier.adapters.cli list-dimensions
easy-verifier: error: argument dimension: invalid choice: 'list-dimensions'
```

At that point `list_dimensions()` returned only a tuple of names, so callers could not obtain a
dimension's purpose or declared sources.

**AFTER** (2026-09-02T04:05:10Z):

```text
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src pytest tests/test_t011_discovery.py -q
........                                                                 [100%]
8 passed in 0.03s
$ PYTHONPATH=src python -m easy_verifier.adapters.cli list-dimensions
[
  {"name": "architecture", "purpose": "Gather ...", "sources_sought": [...]},
  ... seven deterministic records total ...
]
```

**DELTA**: A caller can now discover all seven dimensions, their actionable purposes, and their
declared evidence sources through one deterministic, repository-independent API or CLI command;
T012 continues using the compatible name-only `dimension_names()` helper.

**WITNESS**: Codex Supervisor, 2026-09-02; independently executed the focused test, full suite,
lint, format check, compatibility probe, and public CLI command in the isolated T011 worktree.

---

## Stage 4 Review

The Claude-only `code-review` skill is not callable in this Codex session, so the complete diff was
reviewed manually against all seven acceptance criteria and the T012 compatibility surface.

**Verdict: P0 0 / P1 1 fixed / P2 0 / P3 0.**

**P1 — README still advertised T011 as planned and named a nonexistent `discover` command.** The
T018 doc-truth suite intentionally skips planned blocks, so it stayed green after the command
became available. Fixed by marking discovery runnable today, using the canonical `list-dimensions`
name, and adding a regression that requires that exact unplanned command to exit 0. This is T018's
recorded "mismarked planned block is undetectable" residue becoming real; the new test closes it for
discovery.

- Discovery imports only modules inside `easy_verifier.dimensions`; it accepts no repository path
  and never reads target-repository content.
- Leading-underscore helpers are excluded explicitly. Any other module must expose `DESCRIPTOR`,
  and import/contract errors are not swallowed.
- Records are immutable dataclasses copied directly from descriptors and sorted by external name.
- T012's public `combined_pack()` signature and output are unchanged. Its name-only dependency was
  moved to `dimension_names()` under the user's explicit 2026-09-02 authorization.
- The CLI performs serialization only and adds no inference, recommendation, network, subprocess,
  report write, or target-repository access.
