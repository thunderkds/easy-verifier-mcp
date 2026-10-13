# TASK_REVIEW — T093: The layer rule's classified-share floor counts only backend units

> Sibling of `tasks/TASK_GUIDE_T093.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass (implementer) | `tests/test_t093_backend_unit_share.py`, 7 tests: AC1/2/4 monorepo `apps/api`+`apps/web` measured ("3 of 3 ... in backend unit(s) (apps/api)", "10 ... outside backend units (apps/web) are not counted"); AC6 sabotage `_in_backend_unit -> True` abstains "3 of 13"; AC3 no api file keeps whole repo ("of 12 ... quoted here", no unit wording); root-only manifest; api under root with nested `web/` package; two services = union; a classified file outside every unit still counts as a violation. Pre-change: 6 failed, 1 passed (AC3 passes before, by design). Post-change: `7 passed in 0.96s`; with T088: `35 passed in 3.41s`. |
| Verification command run | ☒ pass (implementer) | `ruff check src tests` -> `All checks passed!`; kitchd/bryony/coffee/ai-training score runs pasted under Demonstration AFTER. |
| Negative cases hold | ☒ pass (implementer) | no api file -> whole repository (AC3 test + ai-training byte-identical derivation); single manifest -> same value (coffee 0, 35/35); outside-unit violation still counted. |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☒ pass (implementer) | full suite on `3abe66d`: `2 failed, 2720 passed, 2 skipped in 621.71s`; the 2 failures are the known stale-image container tests (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`). |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured on `130f129` (no implementation commit yet), one run at a time, with
`PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> --scope project [--all] < /dev/null`;
the architecture `layer_direction_violations` metric, the architecture rating and the overall
extracted from the JSON payload (`[...]` marks elided T088 method boilerplate only).

```
# kitchd  started 2026-10-13T08:18:12Z  exit 0 finished 2026-10-13T08:18:29Z
layer_direction_violations: abstained: "49 of 177 non-shared source file(s) quoted here classify into
  a layer (api, service, data): 37 by behaviour (17 api, 0 service, 20 data), 12 by the layer_paths
  hints only, below the declared minimum share of 0.50, so the layer direction of this code is not
  measurable; 3 disagreement(s) with the layer_paths hints, behaviour wins: apps/api/prisma/seed.ts
  (hint api, behaviour data at apps/api/prisma/seed.ts:32); apps/api/src/auth/guards/roles.guard.ts
  (hint api, behaviour data at apps/api/src/auth/guards/roles.guard.ts:48);
  apps/api/src/realtime/realtime.gateway.ts (hint api, behaviour data at
  apps/api/src/realtime/realtime.gateway.ts:63); curated layer_paths only: [...]; all 185 source
  files -- computed over the whole text of those files, not only the excerpts quoted in this pack"
architecture rating: 100
overall: 56

# bryony --all  started 2026-10-13T08:18:39Z  exit 0 finished 2026-10-13T08:19:59Z
layer_direction_violations: abstained: "450 of 1063 non-shared source file(s) quoted here classify
  into a layer (api, service, data): 58 by behaviour (4 api, 30 service, 24 data), 392 by the
  layer_paths hints only, below the declared minimum share of 0.50, so the layer direction of this
  code is not measurable; 31 disagreement(s) with the layer_paths hints, behaviour wins:
  backend/platform/core/models/index.js (hint data, behaviour service at
  backend/platform/core/models/index.js:9); [...4 more...]; 2 prefix edge(s) from dynamic imports
  with a literal directory prefix [...]; curated layer_paths only: [...]; sample: batches 6 of 6,
  1159 of 1159 files -- computed over the whole text of those files [...]"
architecture rating: 83
overall: 42

# coffee-shop-api  started 2026-10-13T08:20:15Z  exit 0 finished 2026-10-13T08:20:20Z
layer_direction_violations: value 0: "0 import statement(s) from a lower to a higher layer (data ->
  service, service -> api, data -> api). 35 of 35 non-shared source file(s) quoted here classify into
  a layer (api, service, data): 4 by behaviour (4 api, 0 service, 0 data), 31 by the layer_paths
  hints only (curated layer_paths only: [...]); 0 disagreement(s) with the layer_paths hints,
  behaviour wins. [...]; all 85 source files -- computed over the whole text of those files [...]"
architecture rating: 90
overall: 81

# ai-training  started 2026-10-13T08:20:43Z  exit 0 finished 2026-10-13T08:20:48Z
layer_direction_violations: abstained: "framework_not_recognized: no source file quoted here
  registers a route or calls a recognised DB/ORM API (the registry's route_tokens and data_tokens),
  and the layer_paths hints classify 2 of 79 non-shared source file(s), below the declared minimum
  share of 0.50; curated layer_paths only: [...]; all 90 source files -- [...]"
architecture rating: 83
overall: 60
```

**AFTER**: same command on `3abe66d`, one run at a time (`[...]` as above).

```
# kitchd  started 2026-10-13T08:25:25Z  exit 0 finished 2026-10-13T08:25:44Z
layer_direction_violations: abstained: "43 of 88 non-shared source file(s) in backend unit(s)
  (apps/api) classify into a layer (api, service, data): 37 by behaviour (17 api, 0 service, 20
  data), 6 by the layer_paths hints only; 89 non-shared source file(s) outside backend units
  (apps/mobile, apps/web, packages/shared, the repository root) are not counted in this share: a
  backend unit is the deepest directory holding a package manifest at or above a file that registers
  a route, and a file belongs to the deepest such directory above it; violations are still counted
  over all 49 classified file(s), below the declared minimum share of 0.50, so the layer direction of
  this code is not measurable; 3 disagreement(s) [...unchanged...]"
architecture rating: 100
overall: 56

# bryony --all  started 2026-10-13T08:26:06Z  exit 0 finished 2026-10-13T08:27:47Z
layer_direction_violations: abstained: "148 of 515 non-shared source file(s) in backend unit(s)
  (backend) classify into a layer (api, service, data): 47 by behaviour (4 api, 19 service, 24
  data), 101 by the layer_paths hints only; 548 non-shared source file(s) outside backend units
  (backend/scripts/companies/linkedin/queue, backend/scripts/companies/linkedin/scraper,
  backend/scripts/netwise, design, frontend, ...) are not counted in this share: [...]; violations
  are still counted over all 450 classified file(s), below the declared minimum share of 0.50, so
  the layer direction of this code is not measurable; 31 disagreement(s) [...unchanged...]"
architecture rating: 83
overall: 42

# coffee-shop-api  started 2026-10-13T08:28:01Z  exit 0 finished 2026-10-13T08:28:06Z
layer_direction_violations: value 0: "0 import statement(s) from a lower to a higher layer [...]. 35 of
  35 non-shared source file(s) in backend unit(s) (the repository root) classify into a layer (api,
  service, data): 4 by behaviour (4 api, 0 service, 0 data), 31 by the layer_paths hints only [...]"
architecture rating: 90
overall: 81

# ai-training  started 2026-10-13T08:28:06Z  exit 0 finished 2026-10-13T08:28:14Z
layer_direction_violations: abstained, derivation byte-identical to BEFORE ("framework_not_recognized
  [...] classify 2 of 79 non-shared source file(s) [...]")
architecture rating: 83
overall: 60
```

| Repo | Share BEFORE | Share AFTER | Measured | Violations | Architecture | Overall |
|---|---|---|---|---|---|---|
| kitchd | 49/177 (27.7%) | 43/88 (48.9%) | no -> no | - | 100 -> 100 | 56 -> 56 |
| bryony `--all` | 450/1063 (42.3%) | 148/515 (28.7%) | no -> no | - | 83 -> 83 | 42 -> 42 |
| coffee-shop-api | 35/35 | 35/35 (root unit) | yes -> yes | 0 -> 0 | 90 -> 90 | 81 -> 81 |
| ai-training | 2/79, no api | unchanged (no api file) | no -> no | - | 83 -> 83 | 60 -> 60 |

AC7 hand-check: no repository became measured, so there are no new violations to check by hand.
Why the two monorepos still abstain (diagnosed against the source, not fixed: outside T093's scope):
- kitchd: all 45 unclassified `apps/api` files are `*.module.ts`, `dto/*.dto.ts`, `main.ts`,
  `prisma.service.ts`, `types/prisma-client.d.ts`. They match the curated `shared=` globs, but they
  also match `api=**/api/**` because the app's directory is literally `apps/api`. `layer_of` leaves a
  two-layer match unclassified, so they are counted in the denominator instead of being dropped as
  shared. Checked: `layer_of("src/notes/notes.module.ts") == "shared"`, while
  `layer_of("apps/api/src/notes/notes.module.ts") is None`. The guide's "about 49/87" assumed all 49
  classified files are in `apps/api`; 6 are outside it.
- bryony: the premise does not hold. Inside `backend/`, 148 of 515 files classify, and
  `frontend/`/`design/` were contributing hint-classified files (450 - 148 = 302 of the 548 outside).

**DELTA**: The layer rule's classified share is now taken over backend units only, and the derivation
names the unit(s), the in-unit count and the files left out and where. On the four real repositories
no measured/abstained outcome, rating or overall changed (see table).

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
