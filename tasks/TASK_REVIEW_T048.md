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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t048_finance_pack.py` (67 tests, written in this task; incl. `test_ts_number_counts_only_in_the_persistence_layer` — DTO `price: number` skipped, entity `@Column('float') price: number` counts — and `test_persistence_paths_live_in_the_registry`): AC1 `test_float_amount_in_a_payments_model_is_unmet_and_cited` (Success #1, `amount: float` → value 1, passed=False, CWE-1339 cited), `test_decimal_amount_is_met` (Success #2), `test_float_money_per_language` (24 cases: TS/JS number, Mongoose Number/Decimal128, Prisma Float/Decimal, SQL double precision/REAL/NUMERIC/bigint, Django FloatField/DecimalField, SQLAlchemy Float, Python Optional[float], Java double/BigDecimal, C# decimal, Go float64, Rust f64), `test_money_names_are_conservative`; AC2 `test_ledger_without_audit_column_counts`, `test_ledger_mutations_count_only_against_declared_ledgers`, `test_orm_models_and_inherited_audit_columns`, `test_no_ledger_abstains_never_zero`, `test_ledger_code_is_quoted_for_the_agent`, `test_a_batched_read_says_later_batches_were_not_read`; AC3 `test_inactive_pack_leaves_no_trace_and_area_stays_unruled`, `test_active_pack_measures_area_three_and_is_disclosed`, `test_agent_pick_activates_and_replay_is_byte_equal`. Output: `135 passed in 51.65s` (test_t048 + test_t047 + test_t068 snapshot suite) |
| Verification command run | ☑ pass | 2026-10-06T10:36Z, worktree at 057f503: `python -m pytest -q` → `2207 passed, 2 skipped in 254.29s (0:04:14)`; `python -m ruff check src tests` → `All checks passed!` (implementer run; reviewer to re-run) |
| Negative cases hold | ☑ pass | non-money names never count (`amount_of_items`, `item_count`, `total_pages`, bare `total`, `totalCount`, `priceId`, `feeRate`); integer minor units valid (`amount_cents: int`, `amountCents: number`, `amount_cents bigint`); `z.number()` value is not a type; `PaymentMethod`/`TransactionStatus`/`orders` are not ledgers; `prisma.user.update`, `$transaction`, `DELETE FROM orders` not counted; base-class-inheriting ledger never counted as unaudited; no ledger → both ledger rules abstain (never 0); no money field → float rule abstains and the pack rating abstains below floor. Inactive pack: `cmp` byte-identical on coffee-shop-api (769541 B), kitchd (894693 B), bryony (1425093 B) between develop 1e7b3a5 code and this branch; T068 snapshot test green |
| verify | ☒ pass | Supervisor 2026-10-06 on `90001f2`: scratch clone coffee-shop-api with `packs = ["finance"]` → overall 77, finance 100 (DTO `price!: number` skipped per user decision; column is `numeric(10,2)`), disclosure ends "packs active: finance" — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Supervisor code-review of `develop...feat/T048-finance-pack` (packs/finance.py, registry/packs/finance.toml, judge/metrics/registry/improve/report wiring, tests) + name-heuristic probe: money `price/totalPrice/unitCost/balance/taxAmount/costPerUnit` yes; `total/amount_of_items/item_count/total_pages/amountCents/priceId/feeRate` no; ledger `Transaction/LedgerEntry/Payment` yes, `PaymentMethod` no. P0 0 · P1 0. User decisions applied: weights 50/25/25, TS `number` persistence-only. Security: reads text only, no input handling added — pass |
| Full smoke suite still green (no regression) | ☒ pass | Supervisor rerun on `90001f2`: `2207 passed, 2 skipped in 264.40s`; `ruff check src tests` → All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | ☑ N/A | pure backend task, no UI component |

### Real-repo runs (implementer, 2026-10-06, scratch `git clone --local` copies under /tmp/claude-1000/t048, originals untouched; CLI `score --repo <clone> [--agent-input {"packs": ["finance"]}] < /dev/null`)

| Repo | Inactive: develop vs branch | Overall without → with finance | finance rating | float_money_observed | ledger audit | ledger mutated |
|---|---|---|---|---|---|---|
| coffee-shop-api (nestjs-training/coffee-shop-api) | `cmp` byte-identical (769541 B) | 72 → 77 | 100 | 0 of 4 money decls (entity `price!: string`, migration `"price" numeric(10,2)`; the DTO `price!: number` is now skipped) | abstain (no ledger) | abstain (no ledger) |
| kitchd | `cmp` byte-identical (894693 B) | 58 → 48 | 0 | 4 of 31: `schema.prisma:140 costPerUnit Float`, `schema.prisma:222 costComputedAtSnapshot Float`, `migrations/20260703100416_add_inventory_ingredient_stock/migration.sql:10 cost_per_unit DOUBLE PRECISION`, `migrations/20260703104034_add_recipes/migration.sql:36 cost_computed_at_snapshot DOUBLE PRECISION` (the 19 TS DTO/type `number` sites are now skipped) | abstain (no ledger) | abstain (no ledger) |
| bryony (batch 1 of a 1178-source repo) | `cmp` byte-identical (1425093 B) | 67 → 56 | 0 | 12 of 22 (unchanged: explicit Mongoose `Number`): `amount: {type: Number}` in `backend/platform/db/schema/crunchbase-company-log.js:45,54,77,86`, `crunchbase-company.js:115,124,147,156`, `crunchbase-people.js:167`; `amount: Number` / `totalAmount: Number` in `dashboard-company.js:369,379,404` | abstain (no ledger in batch read; disclosed: 978 later-batch files unread) | abstain |
| booking-personal-trainer (hoang.hoan/nestjs-training) | — | — / 73 | 100 | 0 of 13 (`payments.amount_cents int`: integer minor units) | 0 of 1 (`payments` has created_at) | 0 |
| java-training e-commerce/backend | — | — / 57 | 100 | 0 of 19 (BigDecimal / NUMERIC) | 0 of 1 (`CREATE TABLE payments` has created_at) | 0 |
| tapchat-apis `--all` | — | — / 64 | 25 | 107 of 188 (TS `amount/balanceAmount/diamondAmount/...: number`; measured before the persistence-layer decision, so DTO sites are included) | 0 of 2 (migration `transactions` + entity `Transaction`, both created_at) | 2: `transactions.service.ts:147`, `:168` `transactionsRepository.update(...)` |

Re-run 2026-10-06T10:40–10:42Z at 057f503 (user decisions applied: weights approved; TS/JS `number` counts only in persistence_paths files). Every site still cited was re-checked by hand against its source line: kitchd's 4 are Prisma `Float` / SQL `DOUBLE PRECISION` money columns (cost per unit, cost snapshot), bryony's 12 are Mongoose `Number` funding amounts; coffee-shop-api now cites none (its persisted `price` is `numeric(10,2)` / entity `string`). The first run (5153a12) cited coffee-shop-api 1, kitchd 23 and bryony 12, all also checked by hand. The booking, e-commerce and tapchat rows are from that first run (909ce22). tapchat's 2 mutation sites are real `transactionsRepository.update(...)` calls on the Transaction ledger. Defect found and fixed during the run (909ce22): tapchat batch 1 (200 of 450 sources) abstained "no ledger was found" while its `transactions` table sat in a later batch; the reason now discloses the unread later-batch files, and `--all` computes the ledger rules.

### Known limitations (accepted, T048 review 2026-10-06)

- Bare `total` is not a money name (accepted as conservative): it is as often a row count (pagination `total`) as a sum; `totalPrice` / `totalAmount` still count through `price` / `amount`.
- Ledger mutations are textual: ORM unit-of-work changes (assign then flush, MikroORM/TypeORM `save`) are not counted, so `ledger_rows_mutated_observed` is a lower bound.
- A ledger declaration that inherits from a base, audit or timestamp class is never counted as missing audit columns; TypeORM's own `BaseEntity` holds none, so such a ledger can be missed.
- In-app virtual currency (e.g. tapchat `diamondAmount`) is money-named and counts.
- TS/JS `number` counts only in persistence_paths files (user decision 2026-10-06): a persisted model outside those globs is missed, and a DTO kept under `models/` or `entities/` would count.

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

**WITNESS**: Supervisor, 2026-10-06 — Stage 4 review + heuristic probe, full suite rerun (2207 passed), live coffee-shop-api finance run (77, finance 100). Weights 50/25/25, TS-number scope and floor 0.25 user-approved.
