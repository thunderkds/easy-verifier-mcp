# TASK_REVIEW — T088: Layers assigned by observed behaviour

> Sibling of `tasks/TASK_GUIDE_T088.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t088_behaviour_layers.py` (14 tests: SC1–SC6, SC7 both extremes `never`/`always`, data-without-routes is not `framework_not_recognized`, AC8 Nest DI + TypeORM, Nest Prisma subclass imported cross-file, FastAPI `Depends(get_db)` + Python relative imports, Django urls handler module + `objects.filter`, barrel `index.js` + tests take no layer). `14 passed in 1.01s` (implementer run at `0451f17`) |
| Verification command run | ☒ pass | Full suite at `0451f17` (2026-10-12T10:33Z–10:38Z): `3 failed, 2622 passed, 2 skipped in 350.48s (0:05:50)`. The 3 failures are pre-existing and outside T088: 2 container tests (stale docker image) and `test_t029...test_every_tracked_path_of_this_repo_survives_redaction` (fails identically on develop `72223c5` in the main checkout, on `tests/test_t087_third_party_exclusion.py`). `ruff check src tests`: `All checks passed!` |
| Negative cases hold | ☒ pass | SC3 (`items.find`, `[3].find`, `this.cache.find` with mongoose imported: not data); SC4 (route file querying `User.find` is api, 0 violations); SC6 (`framework_not_recognized`); SC7 sabotage both extremes make SC1 and SC2 fail (pytest.raises(AssertionError)) |
| verify | ☑ pass | Supervisor 2026-10-13T02:24Z drove the CLI from the branch (the `verify` skill can only be invoked by the user): `score --repo nest-api --scope project < /dev/null` → overall 80; architecture `layer_direction_violations` = 0, "35 of 35 … classify: 4 by behaviour (4 api), 31 by the layer_paths hints only; 0 disagreement(s)" — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor code-review of `develop...feat/T088` src (8 files: structure.py, metrics.py, metric_tables.py, registry.py, requirement_fidelity.py, 3 registry tomls) + tests. P0 0 · P1 0. Data evidence requires a receiver bound to a `MODULE=` import (AC 2 holds). Backtracking probe on `_RECEIVER_CHAIN`, `_ASSIGN`, `_CLASS`, `_ANNOTATED`, `_WITH_AS` and `_DYNAMIC_IMPORTS` with 20k–50k-char hostile lines: none slow. Related tests t075/t079/t088: 94 passed. Accepted deviations: disagreements in the derivation text, not the payload (DDR-0005 parity); reason-text prefix `framework_not_recognized`. Known limitation, not a defect: the classified-share denominator is repo-wide, so monorepos with a frontend (fullstack-ts 49/177, node-monorepo --all 450/1063) abstain. A backend-only denominator is a follow-up pending the user's decision. |
| Full smoke suite still green (no regression) | ☑ pass | Implementer at 4fd5d88: 2635 passed, 3 pre-existing failures (2 stale-image container tests; t029 tracked-path redaction, which already fails on develop since the T087 merge: separate bugfix). ruff clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A | backend only (guide: UI/Design AC N/A) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A | backend only (guide: UI/Design AC N/A) |
| **UI: Responsiveness at target viewports** | ☒ N/A | backend only (guide: UI/Design AC N/A) |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-12T09:54Z on `feat/T088-behaviour-layers` at `72223c5` (no implementation commit yet), by `PYTHONPATH=<worktree>/src .venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project`, one repo at a time. Run log:

```
=== node-monorepo 2026-10-12T09:54:04Z
warning [batches]: read batches 1 of 6 (200 of 1159 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
exit 0 2026-10-12T09:54:31Z
=== k8s-ops 2026-10-12T09:54:31Z
exit 0 2026-10-12T09:54:36Z
=== fullstack-ts 2026-10-12T09:54:36Z
exit 0 2026-10-12T09:54:46Z
=== python-ml 2026-10-12T09:54:46Z
exit 0 2026-10-12T09:54:51Z
=== nest-api 2026-10-12T09:54:51Z
exit 0 2026-10-12T09:54:54Z
DONE
```

`layer_direction_violations` (architecture dimension) per repo, extracted from the JSON:

```
## node-monorepo  overall=59  architecture=83
  ABSTAINED: 88 of 195 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared
## k8s-ops  overall=None  architecture=None
  ABSTAINED: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import
## fullstack-ts  overall=56  architecture=100
  ABSTAINED: 32 of 177 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 185 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## python-ml  overall=60  architecture=83
  ABSTAINED: 2 of 79 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 90 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## nest-api  overall=80  architecture=80
  value: 0
  derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 35 of 35 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared); shared and unclassified files never count, and a file stem shared by files of different layers names none; only the import statements quoted in this pack are seen; import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import; all 85 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
```

Summary: node-monorepo abstains at 88/195 classified (45%), fullstack-ts 32/177 (18%), python-ml 2/79 (3%), k8s-ops has no import graph (abstains, no source imports read), nest-api 35/35 classified by folder name with 0 violations (no cited examples: there are none). No file is classified by what its code does.

**AFTER**: captured 2026-10-12T10:38Z–10:39Z at `0451f17` (final; identical layer output to the first post-change run at `82a40e5`, 10:05Z), same command, one repo at a time. Run log:

```
=== node-monorepo 2026-10-12T10:38:52Z
warning [batches]: read batches 1 of 6 (200 of 1159 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
exit 0 2026-10-12T10:39:19Z
=== k8s-ops 2026-10-12T10:39:19Z
exit 0 2026-10-12T10:39:24Z
=== fullstack-ts 2026-10-12T10:39:24Z
exit 0 2026-10-12T10:39:35Z
=== python-ml 2026-10-12T10:39:35Z
exit 0 2026-10-12T10:39:40Z
=== nest-api 2026-10-12T10:39:40Z
exit 0 2026-10-12T10:39:43Z
DONE
```

`layer_direction_violations` (architecture) per repo:

```
## node-monorepo  overall=59  architecture=83
  ABSTAINED: 89 of 195 non-shared source file(s) quoted here classify into a layer (api, service, data): 21 by behaviour (0 api, 0 service, 21 data), 68 by the layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; no route registration was found here; 20 disagreement(s) with the layer_paths hints, behaviour wins: backend/platform/db/services/company-custom-data.js (hint service, behaviour data at backend/platform/db/services/company-custom-data.js:78); backend/platform/db/services/company-custom-field-management.js (hint service, behaviour data at backend/platform/db/services/company-custom-field-management.js:33); backend/platform/db/services/dashboard-benchmarking-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-benchmarking-group.js:142); backend/platform/db/services/dashboard-company-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-company-group.js:142); backend/platform/db/services/dashboard-company.js (hint service, behaviour data at backend/platform/db/services/dashboard-company.js:73); curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared
## k8s-ops  overall=None  architecture=None
  ABSTAINED: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import
## fullstack-ts  overall=56  architecture=100
  ABSTAINED: 49 of 177 non-shared source file(s) quoted here classify into a layer (api, service, data): 37 by behaviour (17 api, 0 service, 20 data), 12 by the layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; 3 disagreement(s) with the layer_paths hints, behaviour wins: apps/api/prisma/seed.ts (hint api, behaviour data at apps/api/prisma/seed.ts:32); apps/api/src/auth/guards/roles.guard.ts (hint api, behaviour data at apps/api/src/auth/guards/roles.guard.ts:48); apps/api/src/realtime/realtime.gateway.ts (hint api, behaviour data at apps/api/src/realtime/realtime.gateway.ts:63); curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 185 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## python-ml  overall=60  architecture=83
  ABSTAINED: framework_not_recognized: no source file quoted here registers a route or calls a recognised DB/ORM API (the registry's route_tokens and data_tokens), and the layer_paths hints classify 2 of 79 non-shared source file(s), below the declared minimum share of 0.50; curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 90 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
## nest-api  overall=80  architecture=80
  value: 0
  derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 35 of 35 non-shared source file(s) quoted here classify into a layer (api, service, data): 4 by behaviour (4 api, 0 service, 0 data), 31 by the layer_paths hints only (curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared); 0 disagreement(s) with the layer_paths hints, behaviour wins. A file's layer is what its code does (DDR-0012): api registers a route (route_tokens) or is the module of a dotted route handler; data calls a data_tokens DB/ORM method on a client or model name it imports from a DB/ORM package or an in-repo file binding one; service is a file on an import path from an api file to a data file; a file with route and DB calls is api, and its DB access is never scored; a file the behaviour does not classify takes its layer_paths hint; shared and unclassified files never count, and a file stem shared by files of different layers names none; only the import statements quoted in this pack are seen; import statements are the registry's import tokens, found textually in excerpts of registry-language files; a statement names a file when it contains the file's stem (a package's __init__-style file: its directory) as a whole word -- a textual match, not a resolved import; all 85 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
```

Extra data point, node-monorepo with every batch (`score --all`, 2026-10-12T10:07Z–10:08Z, `82a40e5`): `435 of 1062 non-shared source file(s) quoted here classify into a layer (api, service, data): 28 by behaviour (4 api, 0 service, 24 data), 407 by the layer_paths hints only, below the declared minimum share of 0.50 ...; 22 disagreement(s) with the layer_paths hints, behaviour wins` (overall 42, architecture 83).

| Repo | BEFORE classified share / result | AFTER classified share / result | Violations | Disagreements with path hints |
|---|---|---|---|---|
| node-monorepo (batch 1 of 6) | 88/195 (45%), abstains | 89/195 (46%): 21 by behaviour (0 api, 0 service, 21 data), abstains; "no route registration was found here" | not counted (abstains) | 20 (all hint service → behaviour data) |
| k8s-ops | no import graph, abstains | unchanged (no import statement in source excerpts) | — | — |
| fullstack-ts | 32/177 (18%), abstains | 49/177 (28%): 37 by behaviour (17 api, 0 service, 20 data), abstains | not counted (abstains) | 3 (hint api → behaviour data) |
| python-ml | 2/79 (3%), abstains | abstains `framework_not_recognized` (psycopg/Streamlit are outside the first framework set) | — | — |
| nest-api | 35/35 by hints, value 0 | 35/35: 4 by behaviour (4 api), 31 by hints only, value 0 (MikroORM is outside the first set, so data/service come from hints) | 0 | 0 |

Hand-checked against source (implementer, 2026-10-12):
- node-monorepo disagreements: `backend/platform/db/services/company-custom-data.js:78` `this.modelClass.find({dealId, customFieldId}).count().exec(fn);` with `modelClass: mongoose.model('DBCompanyCustomData')` at :21 — true data. `company-custom-field-management.js:33` `self.modelClass.find(searchOpts)` with `modelClass: mongoose.model('DBCompanyCustomFieldManagement')` at :17 — true. `dashboard-benchmarking-group.js:142` `this.modelClass.findOneAndUpdate({` with `modelClass: mongoose.model('DBBenchmarkingGroup')` at :24 — true. node-monorepo api (only in later batches): `backend/server/dashboard/router.js:83` `webapp.get('/api/health-check', ...)`, `backend/server/scraper/routers/master.js:16`, `backend/server/web/router.js:18` — true routes on a T079 receiver. node-monorepo controllers stay hint-only because `router.js:107` dispatches `webapp.all('/api/:controller/:action', authenticate, apiHandler)` through `controller-manager.js:35` `require('./controllers/' + name)` (dynamic), so no static import path exists: correctly not assumed.
- fullstack-ts disagreements: `apps/api/prisma/seed.ts:32` `await prisma.organization.findFirst({` (`const prisma = new PrismaClient()` :22) — true data; `apps/api/src/auth/guards/roles.guard.ts:48` `this.prisma.user.findUnique(...)` (`prisma: PrismaService` :27, PrismaService `extends PrismaClient` in `prisma/prisma.service.ts`, cross-file) — true; `apps/api/src/realtime/realtime.gateway.ts:63` `this.prisma.user.findUnique({` — true. fullstack-ts api: `announcements.controller.ts:44` `@Get()`, `auth.controller.ts:10` `@Post('signup')` — true; data via a Prisma transaction client `inventory.service.ts:69` `tx.stockMovement.create({` — true. 0 service: fullstack-ts's Nest services call Prisma themselves, so they are data, and no file sits between.
- nest-api api: `category.controller.ts:70` `@Get()`, `product.controller.ts:46` `@Get()`, `user.controller.ts:53` `@Post()` — true.
- Cited violations: none exist on any of the 5 repos (nest-api measures 0; the others abstain), so there is no violation citation to hand-check; violation citation format is pinned by SC2 (`lib/store.js:1 (data -> api)`).

**DELTA**: A file's layer now comes from what its code does — a route registration makes it api, a cited DB/ORM call on an imported or bound model/client makes it data, a file on the import path between them is service — with folder conventions only filling gaps and every hint/behaviour disagreement reported with its evidence line, and a repository whose frameworks are not recognised abstains `framework_not_recognized` instead of a share count.


**AC 11 (dynamic import with a literal directory prefix), added 2026-10-12 at `a07549e`.** Tests: `tests/test_t088_behaviour_layers.py` now `28 passed in 1.68s`. They cover JS `require('./controllers/' + name)`, `` require(`./strategies/${name}`) ``, `import('../dir/' + x)`; Python `importlib.import_module('app.plugins.' + n)` and the f-string form; negatives `require(name)`, `require(base + name)`, `` require(`${base}/x`) `` and a commented-out form; non-recursive resolution; a node-monorepo-shaped dispatch fixture (router → controller-manager → `controllers/*` → model); and a both-extremes sabotage of `_prefix_targets` (never link / link everything), each of which breaks that fixture. The classified-share denominator is unchanged, as instructed. Prefix edges feed layer assignment only; violations are still counted from named import statements.

Run log (one at a time):

```
=== node-monorepo batch1 2026-10-12T11:07:01Z a07549e
warning [batches]: read batches 1 of 6 (200 of 1159 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
exit 0 2026-10-12T11:07:30Z
=== node-monorepo-all all 2026-10-12T11:07:30Z a07549e
exit 0 2026-10-12T11:08:30Z
=== fullstack-ts batch 2026-10-12T11:08:30Z a07549e
exit 0 2026-10-12T11:08:42Z
DONE
```

```
## node-monorepo overall=59 architecture=83
  ABSTAINED: 89 of 195 non-shared source file(s) quoted here classify into a layer (api, service, data): 21 by behaviour (0 api, 0 service, 21 data), 68 by the layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; no route registration was found here; 20 disagreement(s) with the layer_paths hints, behaviour wins: backend/platform/db/services/company-custom-data.js (hint service, behaviour data at backend/platform/db/services/company-custom-data.js:78); backend/platform/db/services/company-custom-field-management.js (hint service, behaviour data at backend/platform/db/services/company-custom-field-management.js:33); backend/platform/db/services/dashboard-benchmarking-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-benchmarking-group.js:142); backend/platform/db/services/dashboard-company-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-company-group.js:142); backend/platform/db/services/dashboard-company.js (hint service, behaviour data at backend/platform/db/services/dashboard-company.js:73); 2 prefix edge(s) from dynamic imports with a literal directory prefix, each linking every source file directly in that directory: backend/platform/queue/index.js:104 -> './strategies/' (4 file(s)); backend/server/dashboard/controller-manager.js:35 -> './controllers/' (17 file(s)); curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared
## node-monorepo-all overall=42 architecture=83
  ABSTAINED: 450 of 1063 non-shared source file(s) quoted here classify into a layer (api, service, data): 58 by behaviour (4 api, 30 service, 24 data), 392 by the layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; 31 disagreement(s) with the layer_paths hints, behaviour wins: backend/platform/core/models/index.js (hint data, behaviour service at backend/platform/core/models/index.js:9); backend/platform/db/services/company-custom-data.js (hint service, behaviour data at backend/platform/db/services/company-custom-data.js:78); backend/platform/db/services/company-custom-field-management.js (hint service, behaviour data at backend/platform/db/services/company-custom-field-management.js:33); backend/platform/db/services/dashboard-benchmarking-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-benchmarking-group.js:142); backend/platform/db/services/dashboard-company-group.js (hint service, behaviour data at backend/platform/db/services/dashboard-company-group.js:142); 2 prefix edge(s) from dynamic imports with a literal directory prefix, each linking every source file directly in that directory: backend/platform/queue/index.js:104 -> './strategies/' (4 file(s)); backend/server/dashboard/controller-manager.js:35 -> './controllers/' (54 file(s)); curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared
## fullstack-ts overall=56 architecture=100
  ABSTAINED: 49 of 177 non-shared source file(s) quoted here classify into a layer (api, service, data): 37 by behaviour (17 api, 0 service, 20 data), 12 by the layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this code is not measurable; 3 disagreement(s) with the layer_paths hints, behaviour wins: apps/api/prisma/seed.ts (hint api, behaviour data at apps/api/prisma/seed.ts:32); apps/api/src/auth/guards/roles.guard.ts (hint api, behaviour data at apps/api/src/auth/guards/roles.guard.ts:48); apps/api/src/realtime/realtime.gateway.ts (hint api, behaviour data at apps/api/src/realtime/realtime.gateway.ts:63); curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared; all 185 source files -- computed over the whole text of those files, not only the excerpts quoted in this pack
```

| Run | Before AC 11 (`0451f17`) | After AC 11 (`a07549e`) |
|---|---|---|
| node-monorepo batch 1 | 89/195; by behaviour 21 (0 api, 0 service, 21 data); abstains; 20 disagreements | 89/195; by behaviour 21 (0 api, 0 service, 21 data); abstains; 20 disagreements; 2 prefix edges (17 controllers in batch 1, 4 strategies). No route file is in batch 1, so there is no api to start a path from: unchanged |
| node-monorepo `--all` | 435/1062; by behaviour 28 (4 api, 0 service, 24 data); abstains; 22 disagreements | 450/1063; by behaviour 58 (4 api, **30 service**, 24 data); abstains; 31 disagreements; 2 prefix edges (54 controllers, 4 strategies) |
| fullstack-ts (regression) | 49/177; 37 (17 api, 0 service, 20 data) | identical: 49/177; 37 (17 api, 0 service, 20 data); 3 disagreements; no prefix edge |

Violations: none on these runs (all abstain below the share floor, so violations are not counted).

Prefix edges hand-checked against node-monorepo source:
1. `backend/server/dashboard/controller-manager.js:35` `constrollerClass = require('./controllers/' + name),` after `fs.readdirSync(__dirname + '/controllers')` at :32 and a `.js` filter at :33. `controllers/` has 56 entries: 54 `.js` and 2 `.jade`. The edge links 54 files (`--all`), which is correct.
2. `backend/platform/queue/index.js:104` `var strategy = require('./strategies/' + name);` links `strategies/` = `dblazy.js, scraper-company-name.js, scraper.js, signup.js` (4 files), which is correct.
3. A request path through the prefix edge: `backend/server/dashboard/router.js:5` `require('./controller-manager')`, then `controller-manager.js:35` (prefix), then `controllers/search.js:14` `require('../../../platform/db/services/dashboard-sector')`, then `dashboard-sector.js:27` `self.modelClass.find(query)` with `modelClass: mongoose.model('DBSector')` at :14 (data). `search.js` and `controller-manager.js` are therefore service, which is correct.
New disagreement worth noting: `backend/platform/core/models/index.js` has hint data and behaviour service at :9 (`Companies = require('./company').Companies`). It is a model barrel on an api→data path, so it is service per the barrel edge case.

Follow-up `4fd5d88`: the full suite at `3481720` flagged `test_metrics.py::test_metrics_module_imports_nothing_that_reads_the_filesystem`, because `metrics.py` had imported `posixpath`. The fix replaces it with `PurePosixPath`. After the fix, `tests/test_t088_behaviour_layers.py` and `tests/test_metrics.py` give 60 passed. A re-run of node-monorepo `--all` at `4fd5d88` gave a layer derivation byte-identical to the `a07549e` run above. Full suite at `3481720`: 2635 passed, and 4 failed: the 3 pre-existing failures (2 container tests, t029) plus that posixpath test, which is now fixed.

**WITNESS**: Supervisor, 2026-10-13. `memory/event-trace/T088.jsonl` (117 records) holds the implementer's runs. The Supervisor independently re-ran 94 related tests and drove `score` on nest-api from the branch (layer rule measured, 0 violations, 4 api by behaviour).
