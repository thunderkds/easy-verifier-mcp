# TASK_REVIEW — T108: change-risk slice 1

> Sibling of `tasks/TASK_GUIDE_T108.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t108_change_risk.py` (49 tests; collection failed pre-module with `ImportError: cannot import name 'change_risk'`); t026 invariant exemption (Supervisor decision 4): `110 passed in 11.51s` (t026 + t108) — pass |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!`; worktree clean at `2edcd8b` — pass |
| Negative cases hold | ☑ pass | project/task scope abstain ("change risk is rated at changes/worktree scope only") and project payload omits the dimension; deleted test never matches; test in another monorepo project does not match; rename-only (R100) and test-only diffs abstain "no changed source code"; root commit / clipped diff disclosed (all in t108 tests) — pass |
| verify | ☑ pass | Supervisor independent CLI run 2026-10-16 12:48 UTC, node-monorepo `--scope changes --ref 09be767d0`: payload keys `ratings, overall, change_risk, …`; `change_risk` = rating 0, `bugfix_without_regression_test` failed, cites `backend/server/dashboard/controllers/recently-added-companies.js`; `overall` 85 unchanged. Supervisor `write-report` on fullstack-ts `--ref 522d666`: "Change risk 100/100 — change kind bugfix (detected from commit subject: … fix(T041): …); passing: bugfix_without_regression_test 1 (≥ 1), cites apps/web/src/features/inventory/InventoryPage.test.tsx. Not averaged into the overall." AC2 (agent): project payload sha256 equal on 4 repos (option: omit). AC7 (a)(b)(c) all matched pre-registered expectations — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `change_risk.py` (417 lines), judge (`CHANGE_FLOORS`, rule, `rate_overall` filter, table-consistency check), metrics `PACK_METRICS`, score headline, report line, pipeline (2 lines), models, adapters (scope arg). code-review: P0/P1/P2 none. P3: (a) a project-scope `combined`/`write_report` explicitly requesting change-risk still renders its pack section; (b) the T107 context note is still pack-only. Security (Medium): git read-only with explicit argv (`log`, `diff --name-status -M`, `rev-parse`); commit subjects, branch, paths redacted; manifest probe contained (`_is_contained`) and never reads files — pass |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor run on `2edcd8b`: `3033 passed, 3 skipped in 440.40s (0:07:20)`, exit 0. Presence-only test edits approved (marked `# T108: change-risk added`) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | Rendered `evidence-report-changes-20261016T125657-233753Z.html` (fullstack-ts 522d666): one added `<p class="summary-overall">Change risk …</p>` line after the overall line, text pasted in the verify row; no other report element changed (project-scope report omits it, t108 test) — pass |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | `git diff develop...HEAD -- core/report.py` adds 0 lines matching style/css/color/font/@media/px; the block uses only the existing `summary-overall` and `notice notice-abstain` classes — pass |
| **UI: Responsiveness at target viewports** | ☑ pass | By construction, not a viewport screenshot: the line is the same element and class as the existing overall line inside the same summary container, with no new CSS or fixed widths, so it wraps exactly like the overall line at 375 px and 1280 px. No browser render was taken — pass (structural) |

---

## Demonstration

**BEFORE** (backend-developer, worktree at `54ce1c0` = develop HEAD, py3.12 venv, before any
implementation commit; raw payloads kept under the git-ignored `.local/t108/before/`):

```
2026-10-16T11:53:05Z  easy-verifier list-dimensions < /dev/null
list-dimensions: 13 dimensions: api, architecture, blast-radius, code-quality, data, infrastructure, operations, reliability, requirement-fidelity, security, solution-fit, supply-chain, test-strategy | change-risk present: False

2026-10-16T11:53:30Z  easy-verifier score --repo <real-repos>/node-monorepo --scope changes --ref 09be767d0 < /dev/null
node-monorepo score --scope changes --ref 09be767d0: top-level keys = ['areas_measured', 'areas_without_rule', 'capped', 'detected_stack', 'improvement_plan', 'metrics', 'overall', 'provenance', 'ratings', 'warnings'] | 'change_risk' in payload: False | overall.value = 85 | contributors = ['architecture', 'code-quality', 'security', 'blast-radius', 'supply-chain']
```

AC2 project-scope BEFORE payloads (`score --scope project < /dev/null`, sha256 of the stdout JSON):

```
2026-10-16T11:53:41Z  this repo (detached worktree pinned at 54ce1c0)  4fcd340ba914a24a399000a1221e85c6dfedbc8abfa50fa42e405540019b68b7
2026-10-16T11:53:55Z  fullstack-ts                                     98b9346acfd541904f4385903ab73056a042eeb30c5da5832a97366f10d095a7
2026-10-16T11:54:08Z  python-ml                                        bb3519a161af44c6dca82ff775c3a3795fe048f6f46915938b310b9f9a4791fe
2026-10-16T11:54:14Z  node-monorepo                                    83c9ede97429c367753a862663899a54b28d768175bac4b9aa2cad0d289689c4
```

**AC7 pre-registered expectations** (written 2026-10-16 before any AC7 run; commits found by
`git log --grep`):

| Case | Repo (alias) + commit | What the commit is | Expected `change_risk` |
|---|---|---|---|
| (a) | node-monorepo `09be767d0` | subject `Bugfix/ Update condition time range`, 1 source file changed (`backend/server/dashboard/controllers/recently-added-companies.js`), no test | `change_kind.value = bugfix` (signal: commit subject), rating **fails** `bugfix_without_regression_test` (value 0, metric 0 matched tests), cites the changed source file lacking a test |
| (b) | fullstack-ts `522d666` | subject `fix(T041): capture low-stock threshold …`; changes `InventoryPage.tsx`, `IngredientFormDialog.tsx` and `InventoryPage.test.tsx` (same directory) | `change_kind.value = bugfix` (signal: commit subject `fix`), rating **passes** (value 100, ≥ 1 matched test), cites `apps/web/src/features/inventory/InventoryPage.test.tsx` |
| (c) | python-ml `684ebb4` | subject `feat: show off-topic refusal message …`, 3 source files, no test | `change_kind.value = feature` (signal: commit subject `feat`), **abstains** with "rules for feature arrive in T110" |

**AFTER** (backend-developer, branch `feat/T108-change-risk`; raw payloads in the git-ignored `.local/t108/after/`):

```
2026-10-16T12:47:23Z  easy-verifier list-dimensions < /dev/null
list-dimensions: 14 dimensions: api, architecture, blast-radius, change-risk, code-quality, data, infrastructure, operations, reliability, requirement-fidelity, security, solution-fit, supply-chain, test-strategy | change-risk present: True

2026-10-16T12:46:38Z  score --repo <real-repos>/node-monorepo --scope changes --ref 09be767d0 < /dev/null
change_risk: kind=rating value=0 | change_kind=bugfix (detected; commit subject "09be767d Bugfix/ Update condition time range")
  bugfix_without_regression_test metric 0, passed false, cites backend/server/dashboard/controllers/recently-added-companies.js
overall: 85 (unchanged from BEFORE; contributors identical, change-risk not among them)
```

AC2 project-scope AFTER (same commands as BEFORE; **option chosen: omit** -- change-risk is not gathered at project scope, so no entry is added):

```
2026-10-16T12:45:39Z  this repo (pinned 54ce1c0)  4fcd340ba914a24a399000a1221e85c6dfedbc8abfa50fa42e405540019b68b7  BYTE-EQUAL
2026-10-16T12:45:51Z  fullstack-ts                98b9346acfd541904f4385903ab73056a042eeb30c5da5832a97366f10d095a7  BYTE-EQUAL
2026-10-16T12:46:03Z  python-ml                   bb3519a161af44c6dca82ff775c3a3795fe048f6f46915938b310b9f9a4791fe  BYTE-EQUAL
2026-10-16T12:46:08Z  node-monorepo               83c9ede97429c367753a862663899a54b28d768175bac4b9aa2cad0d289689c4  BYTE-EQUAL
```

AC7 actual `change_risk` headlines (run after the expectations above, background, one at a time):

| Case | Expected | Actual | Match |
|---|---|---|---|
| (a) node-monorepo `09be767d0` | bugfix, fails, value 0 | 2026-10-16T12:46:38Z `rating` value **0**; kind bugfix (commit subject `Bugfix/ …`); metric 0, cites the changed `.js` source | yes |
| (b) fullstack-ts `522d666` | bugfix, passes, value 100 | 2026-10-16T12:46:49Z `rating` value **100**; kind bugfix (commit subject `fix(T041): …`); metric 1, cites `apps/web/src/features/inventory/InventoryPage.test.tsx` | yes |
| (c) python-ml `684ebb4` | feature, abstains | 2026-10-16T12:46:53Z `rating_abstention`; kind feature (commit subject `feat: …`); unavailable `bugfix_without_regression_test`: "rules for feature arrive in T110" | yes |

**Supervisor decisions (2026-10-16, recorded here):**
1. One prefix vocabulary for branch names and commit subjects (fix, bugfix, hotfix, feat, feature, refactor, chore, docs, ci, build, deps), case-insensitive, the type followed by `:` or `/` (so `Bugfix/ …` is a bugfix; side effect accepted: `CI/CD: …` counts as chore).
2. Only issue references whose keyword is fix / fixes / fixed are a bugfix signal; a bare `#N` or `closes #N` gives no kind.
3. `write_report` at project scope omits the change-risk line, matching the score payload.
4. Option A for the t026 invariant: `test_every_descriptor_declares_roles_and_sources_sought_is_their_names` exempts dimensions in `judge.CHANGE_FLOORS` from the "at least one file-backed role" assertion only (DDR-0014: change-risk evaluates the change itself, not a file a pattern fills); every other assertion in that test still applies to change-risk.

**DELTA**: `change-risk` is now the 14th listed dimension and the node-monorepo no-test bugfix carries a separate failing `change_risk` headline (0), while `overall` (85) and all four project-scope payloads are byte-identical to before.

**WITNESS**: backend-developer (agent), BEFORE 2026-10-16T11:53Z, AFTER 2026-10-16T12:45Z–2026-10-16T12:47:23Z.
