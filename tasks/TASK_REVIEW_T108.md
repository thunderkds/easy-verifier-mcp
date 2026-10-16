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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail / ☐ N/A | |
| Verification command run | ☐ pass / ☐ fail / ☐ N/A | |
| Negative cases hold | ☐ pass / ☐ fail / ☐ N/A | |
| verify | ☐ pass / ☐ fail / ☐ N/A | |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail / ☐ N/A | |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail / ☐ N/A | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | |

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

**AFTER**: [same command, post-change]

**DELTA**: [one sentence]

**WITNESS**: [who ran it and when]
