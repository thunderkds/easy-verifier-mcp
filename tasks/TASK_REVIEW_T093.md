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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
