# TASK_REVIEW — T078: Repo conventions in scoring, replayable

> Sibling of `tasks/TASK_GUIDE_T078.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured 2026-10-08T04:27Z by backend-developer on worktree HEAD `71fd4a1` (no T078 code yet).
Command: `EASY_VERIFIER_SOT=<empty dir> PYTHONPATH=<worktree>/src .venv/bin/python -m easy_verifier.adapters.cli score --repo <r> --scope project --all </dev/null`

1. Temp git repo (`requirements.txt`; `app/endpoints/users.py` -> imports `app.services.user_service`; `app/services/user_service.py` -> imports `app.repositories.user_repo`; `app/repositories/user_repo.py` -> imports `app.endpoints.users`, a data -> api import). Curated `layer_of`: endpoints `None`, services `service`, repositories `data`.

```
== BEFORE (worktree HEAD 71fd4a1) 2026-10-08T04:27:17Z
-- without .easy-verifier.toml
sha256 dd5ac6a50d5cd0225635eb28723a9fe66dfb6c9fb410262f1419cbfe7a4b2df1 | registry_entries in payload: False
 architecture.layer_direction_violations value: {'abstained': False, 'value': 0}
 derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 2 of 3 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (only the curated layer_paths apply: local-layer and .easy-verifier.toml layer paths are not used in scoring until conventions are embedded for replay (T075)); shared and unclassified files n
-- with .easy-verifier.toml [conventions] layer_paths = ["api=**/endpoints/**"]
sha256 9eebe62f310971f1ee8819ec97a6ddd4c9f622f4599ccd1cb3161a8cc37f5e04 | registry_entries in payload: False
 architecture.layer_direction_violations value: {'abstained': False, 'value': 0}
 derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 2 of 3 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (only the curated layer_paths apply: local-layer and .easy-verifier.toml layer paths are not used in scoring until conventions are embedded for replay (T075)); shared and unclassified files n
```

The toml extra is ignored: still "2 of 3" classified, 0 violations (the data -> api import is invisible), no `registry_entries`, "only the curated layer_paths apply" disclosure present. (The two payload hashes differ only because the toml file itself is a repository file in scope.)

2. Real repos, no `.easy-verifier.toml`, empty local layer (no-regression baseline):

```
coffee exit=0 2026-10-08T04:27:31Z 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  -
coffee2 exit=0 2026-10-08T04:27:34Z 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  -
kitchd exit=0 2026-10-08T04:27:43Z 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  -
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
