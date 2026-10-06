# TASK_REVIEW — T048: Finance pack (#3 financial integrity & historical reconstruction)

> Sibling of `tasks/TASK_GUIDE_T048.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t048_finance_pack.py` (63 tests, written in this task): AC1 `test_float_amount_in_a_payments_model_is_unmet_and_cited` (Success #1, `amount: float` → value 1, passed=False, CWE-1339 cited), `test_decimal_amount_is_met` (Success #2), `test_float_money_per_language` (24 cases: TS/JS number, Mongoose Number/Decimal128, Prisma Float/Decimal, SQL double precision/REAL/NUMERIC/bigint, Django FloatField/DecimalField, SQLAlchemy Float, Python Optional[float], Java double/BigDecimal, C# decimal, Go float64, Rust f64), `test_money_names_are_conservative`; AC2 `test_ledger_without_audit_column_counts`, `test_ledger_mutations_count_only_against_declared_ledgers`, `test_orm_models_and_inherited_audit_columns`, `test_no_ledger_abstains_never_zero`, `test_ledger_code_is_quoted_for_the_agent`, `test_a_batched_read_says_later_batches_were_not_read`; AC3 `test_inactive_pack_leaves_no_trace_and_area_stays_unruled`, `test_active_pack_measures_area_three_and_is_disclosed`, `test_agent_pick_activates_and_replay_is_byte_equal`. Output: `135 passed in 51.65s` (test_t048 + test_t047 + test_t068 snapshot suite) |
| Verification command run | ☑ pass | 2026-10-06T09:07Z, worktree at 909ce22: `python -m pytest -q` → `2203 passed, 2 skipped in 237.31s (0:03:57)`; `python -m ruff check src tests` → `All checks passed!` (implementer run; reviewer to re-run) |
| Negative cases hold | ☑ pass | non-money names never count (`amount_of_items`, `item_count`, `total_pages`, bare `total`, `totalCount`, `priceId`, `feeRate`); integer minor units valid (`amount_cents: int`, `amountCents: number`, `amount_cents bigint`); `z.number()` value is not a type; `PaymentMethod`/`TransactionStatus`/`orders` are not ledgers; `prisma.user.update`, `$transaction`, `DELETE FROM orders` not counted; base-class-inheriting ledger never counted as unaudited; no ledger → both ledger rules abstain (never 0); no money field → float rule abstains and the pack rating abstains below floor. Inactive pack: `cmp` byte-identical on coffee-shop-api (769541 B), kitchd (894693 B), bryony (1425093 B) between develop 1e7b3a5 code and this branch; T068 snapshot test green |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☑ pass | full suite `2203 passed, 2 skipped` (was 2140+ before; 63 new). Touched existing tests only where they enumerate packs: `test_t047_packs.py` (PACKS set), `test_t071_evaluation_docs.py` (DECLARED "finance"), `test_t082_uncovered_areas.py` (a pack with no documentation rules) |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | ☑ N/A | pure backend task, no UI component |

### Real-repo runs (implementer, 2026-10-06, scratch `git clone --local` copies under /tmp/claude-1000/t048, originals untouched; CLI `score --repo <clone> [--agent-input {"packs": ["finance"]}] < /dev/null`)

| Repo | Inactive: develop vs branch | Overall without → with finance | finance rating | float_money_observed | ledger audit | ledger mutated |
|---|---|---|---|---|---|---|
| coffee-shop-api (nestjs-training/coffee-shop-api) | `cmp` byte-identical (769541 B) | 72 → 60 | 0 | 1 of 4 money decls: `response-product-variant.dto.ts:15 (price: number)` | abstain (no ledger) | abstain (no ledger) |
| kitchd | `cmp` byte-identical (894693 B) | 58 → 48 | 0 | 23 of 31: Prisma `costPerUnit Float`, `costComputedAtSnapshot Float`, migrations `cost_per_unit DOUBLE PRECISION`, `cost_computed_at_snapshot DOUBLE PRECISION`, TS DTO/types `costPerUnit/lineCost/costComputed: number` | abstain (no ledger) | abstain (no ledger) |
| bryony (batch 1 of a 1178-source repo) | `cmp` byte-identical (1425093 B) | 67 → 56 | 0 | 12 of 22: Mongoose `amount: {type: Number}` / `amount: Number` / `totalAmount: Number` in `backend/platform/db/schema/crunchbase-company{,-log,-people}.js`, `dashboard-company.js` | abstain (no ledger in batch read; disclosed: 978 later-batch files unread) | abstain |
| booking-personal-trainer (hoang.hoan/nestjs-training) | — | — / 73 | 100 | 0 of 13 (`payments.amount_cents int`: integer minor units) | 0 of 1 (`payments` has created_at) | 0 |
| java-training e-commerce/backend | — | — / 57 | 100 | 0 of 19 (BigDecimal / NUMERIC) | 0 of 1 (`CREATE TABLE payments` has created_at) | 0 |
| tapchat-apis `--all` | — | — / 64 | 25 | 107 of 188 (TS `amount/balanceAmount/diamondAmount/...: number`) | 0 of 2 (migration `transactions` + entity `Transaction`, both created_at) | 2: `transactions.service.ts:147`, `:168` `transactionsRepository.update(...)` |

Every cited site of coffee-shop-api (1), kitchd (23) and bryony (12), and tapchat's 2 mutation sites, was inspected by hand against the source line: all are money-named fields typed as JS/TS `number`, Mongoose `Number`, Prisma `Float` or SQL `DOUBLE PRECISION`, and the mutations are real `update` calls on the Transaction repository. tapchat's float names were tallied (amount 29, diamondAmount 19, remainingBalance 11, balanceAmount 9, …): all money-named; `diamondAmount` is in-app virtual currency (borderline, counted). Defect found and fixed during the run (909ce22): tapchat batch 1 (200 of 450 sources) abstained "no ledger was found" while its `transactions` table sat in a later batch; the reason now discloses the unread later-batch files, and `--all` computes the ledger rules.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer before any T048 implementation commit, worktree HEAD = develop 1e7b3a5; demo repo = scratch git repo with `.easy-verifier.toml` `packs = ["finance"]` and `src/payments.py` declaring `amount: float`):

```text
$ date -u; git -C easy-verifier-mcp-T048 rev-parse --short HEAD
2026-10-06T08:43:49Z
1e7b3a5
$ python -m easy_verifier.adapters.cli score --repo demo < /dev/null   # demo: .easy-verifier.toml packs = ["finance"], src/payments.py 'amount: float'
exit=0
stderr:
warning [registry]: unknown pack 'finance' ignored; known packs: healthcare
ratings dimensions: ['architecture', 'blast-radius', 'code-quality', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy']
area #3 in areas_without_rule: True
finance in payload: False | float_money in payload: False
overall: 67 lared floor of this dimension's rule weight was measured, so no number is given)
```

The finance pack is unknown (noted and ignored), no finance slot/metric exists, and area #3 "Financial integrity & historical reconstruction" is listed in `areas_without_rule`.

**AFTER** (backend-developer, same demo repo and command, worktree at 5153a12):

```text
$ date -u; git rev-parse --short HEAD
2026-10-06T09:04:46Z
5153a12
$ python -m easy_verifier.adapters.cli score --repo demo < /dev/null   # same demo repo as BEFORE
exit=0
stderr:
ratings dimensions: ['architecture', 'blast-radius', 'code-quality', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy', 'finance']
area #3 in areas_without_rule: False | in areas_measured: True
float_money_observed {'abstained': False, 'value': 1} 1 money-named field(s) of a binary floating-point type, of 1 money-named declaration(s) in 1 source and schema
ledger_tables_without_audit_columns_observed {'abstained': True, 'omitted_lower_bound': None, 'reason': "no ledger, transaction or payment table or model (the pack's ledger_declarations and ledger_names) was found in 1 source and schema file(s), so there is no ledger to judge"} no value: no ledger, transaction or payment table or model (the pack's ledger_declarations and ledger_names) w
ledger_rows_mutated_observed {'abstained': True, 'omitted_lower_bound': None, 'reason': "no ledger, transaction or payment table or model (the pack's ledger_declarations and ledger_names) was found in 1 source and schema file(s), so there is no ledger to judge"} no value: no ledger, transaction or payment table or model (the pack's ledger_declarations and ledger_names) w
finance rating: rating 0
disclosure tail:  was measured, so no number is given); packs active: finance
```

**DELTA**: A repository that enables `packs = ["finance"]` (or an agent pick) now gets a cited finance rating on area #3 — float money fields counted, ledger audit columns and append-only evidence where a ledger exists (abstaining otherwise) — instead of the pack being ignored and #3 listed as unruled; without the pack the payload is byte-identical.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T048.jsonl`, never the
implementing agent alone]
