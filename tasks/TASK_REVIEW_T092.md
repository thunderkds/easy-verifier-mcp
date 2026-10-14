# TASK_REVIEW — T092: Dangerous-sink hits in test files are reported, not scored

> Sibling of `tasks/TASK_GUIDE_T092.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t092_test_path_sinks.py` (8 tests; run on pre-fix src: 5 failed, incl. count/abstain/derivation; sabotage tests pin both extremes: predicate always-False -> 2, always-True -> abstains) and updated `tests/test_t034_security_sinks.py::test_metric_tags_test_path_hits_and_does_not_count_them` |
| Verification command run | pass | `pytest tests/test_t092... test_t034... test_t068...`: 127 passed; `ruff check src tests`: All checks passed; real-repo `score` runs in Demonstration |
| Negative cases hold | pass | test-only pack abstains (never 0); no-test-hit derivation has no 'not counted' sentence; test hit still cited |
| verify | ☑ pass | Supervisor 2026-10-13 drove the CLI from the branch on nest-api: overall 81, security 59; `sink_hits_observed` 0, "0 dangerous-sink hit(s) in non-test files, from 17 excerpt(s): test/reset-test-db.ts:25 CWE-89 … [test path]; 1 test-path hit(s) are listed and not counted" — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor review of `_sink_hits_observed` / `_SINK_METHOD`, the SCORING_RULES sink row, t034 flip (counts → does not count; follows the user decision), and the t068 snapshot (only the sink metric's fields; test-strategy's sink now abstains per AC 3). P0 0 · P1 0. Weights untouched. |
| Full smoke suite still green (no regression) | pass | full run: 3 failed, 2712 passed, 2 skipped -- the 2 known stale-image container tests plus `test_t068 under_the_cap_payload_is_identical_to_develop`, which pinned the old sink wording; snapshot regenerated (only sink text changed, ratings/overall unchanged; test-strategy pack holding only a test file now abstains instead of 0), re-run of that file passes (127 passed with t092/t034) |
| **UI: Visual regression (diff or verdict pasted)** | N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-13T07:49Z-07:50Z at base `f758d75`, before any implementation commit; command per repo: `PYTHONPATH=<worktree>/src .venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project < /dev/null`, run one at a time):

| repo | run (UTC) | security | overall | sink_hits_observed (security pack) |
|------|-----------|----------|---------|------------------------------------|
| nest-api | 07:49:52-07:49:56 | **18** | 76 | **1** -> fails (earned 0/35) |
| node-monorepo | 07:49:56-07:50:30 | **50** | 59 | **0** -> passes (35/35) |
| fullstack-ts | 07:50:30-07:50:45 | **59** | 56 | **0** -> passes (35/35) |

Derivations (verbatim, method tail elided):
- nest-api: `1 dangerous-sink hit(s) in 17 excerpt(s): test/reset-test-db.ts:25 CWE-89 (https://cwe.mitre.org/data/definitions/89.html) [test path]`; computed_from `test/reset-test-db.ts:25-25`
- node-monorepo: `0 dangerous-sink hit(s) in 16 excerpt(s): none`
- fullstack-ts: `0 dangerous-sink hit(s) in 17 excerpt(s): none` (cites `apps/web/src/routes/AuthGuard.test.tsx:1-44` among its scanned excerpts; no hit)

**AFTER** (same command, 2026-10-13T08:05Z-08:06Z, HEAD `888c8ad`):

| repo | security before -> after | overall before -> after | sink_hits_observed before -> after |
|------|--------------------------|-------------------------|------------------------------------|
| nest-api | 18 -> **59** | 76 -> **81** | 1 (fail) -> **0** (pass, 35/35) |
| node-monorepo | 50 -> 50 | 59 -> 59 | 0 -> 0 |
| fullstack-ts | 59 -> 59 | 56 -> 56 | 0 -> 0 |

nest-api derivation now: `0 dangerous-sink hit(s) in non-test files, from 17 excerpt(s): test/reset-test-db.ts:25 CWE-89 (https://cwe.mitre.org/data/definitions/89.html) [test path]; 1 test-path hit(s) are listed and not counted`; computed_from still `test/reset-test-db.ts:25-25`.

Test-path hits that stopped counting, checked by hand: exactly one, nest-api `test/reset-test-db.ts:25` -- opened the file: line 25 is `.execute(\`truncate table ${names} restart identity cascade\`)` in a test DB-reset helper under `test/` (names come from the DB's own table list, not user input). node-monorepo and fullstack-ts had no counted hits before, so none stopped counting; fullstack-ts's scanned `AuthGuard.test.tsx` has no hit.

**DELTA**: Risky code inside test files is still listed and cited but no longer lowers the security rating (nest-api 18 -> 59).

**WITNESS**: Supervisor, 2026-10-13. Re-ran the full suite on the branch (2713 passed) and drove `score` on nest-api (security 18 → 59, overall 76 → 81).
