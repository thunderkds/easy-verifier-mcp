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

**AFTER**: captured 2026-10-08T05:01Z by backend-developer on worktree HEAD `e03aa2f` (same command, same fixture as BEFORE 1).

```
== AFTER (worktree HEAD e03aa2f) 2026-10-08T05:01:38Z
-- without .easy-verifier.toml (same fixture as BEFORE)
sha256 7d0a86698541262e0506b054e640b72eb54dfaa3bdaee6835cf5b6fb3a3ed4a3 | registry_entries: null
 architecture.layer_direction_violations value: {'abstained': False, 'value': 0}
 derivation: 0 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api). 2 of 3 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (curated layer_paths only: no local-layer or .easy-verifier.toml layer paths were declared); shared and unclassified files never count, and a file stem shared by files of
-- with .easy-verifier.toml [conventions] layer_paths = ["api=**/endpoints/**"]
sha256 a8079ba3324f941bf233a50b4ecbefcb69bc0d7c27001c1066756ffe1e0bf118 | registry_entries: [{"language": "conventions", "field": "layer_paths", "value": ["api=**/endpoints/**"], "citation_url": ".easy-verifier.toml", "source_tag": "user-supplied"}]
 architecture.layer_direction_violations value: {'abstained': False, 'value': 1}
 derivation: 1 import statement(s) from a lower to a higher layer (data -> service, service -> api, data -> api), e.g. app/repositories/user_repo.py:1 (data -> api). 3 of 3 non-shared source file(s) quoted here classify into a layer (api, service, data) by the declared layer_paths conventions (curated layer_paths plus 1 from the repository's .easy-verifier.toml, listed in registry_entries); shared and unclassi
```

Replay (AC 5). The same fixture, with `.easy-verifier.toml` git-ignored so the file is not evidence. Scored with the toml on machine A, toml deleted, then replayed on empty machine B:

```
== replay on the gitignored-toml copy: score with toml (machine A) -> delete toml -> replay entries (machine B)
 machine-B local layer files before replay: 0
 replay exit=0
 machine-B local layer files after replay: 0
6e0acc2c4a9882bbe08c72428be5cd0811b1584cca6e1ba3b5630981dc5a07c3  r_orig.json
27d8d9c9d606e6640a967a3211af01e5618c74202e6d6553b78e89198cdf0dec  r_bare.json
6e0acc2c4a9882bbe08c72428be5cd0811b1584cca6e1ba3b5630981dc5a07c3  r_replay.json
 original == replay: BYTE-EQUAL
 original != bare (toml deleted, no replay): the entries made the difference
```

CLI vs MCP parity (AC 6), in-process `mcp.call_tool("score")` vs CLI stdout:

```
MCP vs CLI (toml in repo): MCP-only keys dropped ['needs_input']; equal = True; registry_entries = [{"language": "conventions", "field": "layer_paths", "value": ["api=**/endpoints/**"], "citation_url": ".easy-verifier.toml", "source_tag": "user-supplied"}]
MCP vs CLI (toml deleted + replayed entries): MCP-only keys dropped ['needs_input']; equal = True; registry_entries = [...same...]
local layer files written: 0
```

Real repos, no toml, empty local layer (AC 4). The hash changes only through the AC 7 disclosure string. Swapping that one string in the BEFORE payload reproduces AFTER byte-for-byte:

```
coffee before 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce after 2a12a8c9830ad14a0aa42d61883ae16ea7df368588ecc21811a216c216880c74
  old-note occurrences before: 2 | after: 0 | new-note after: 2
  before with ONLY the disclosure string swapped: 2a12a8c9830ad14a0aa42d61883ae16ea7df368588ecc21811a216c216880c74 == after: True
kitchd before 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9 after d1384151fc663671df1618755b5ee817e9e22116722ca0730bfababced87156f
  old-note occurrences before: 4 | after: 0 | new-note after: 4
  before with ONLY the disclosure string swapped: d1384151fc663671df1618755b5ee817e9e22116722ca0730bfababced87156f == after: True
```

**DELTA**: A repository's `.easy-verifier.toml` `[conventions]` and the local layer's `conventions.toml` now change the score: layer paths, route tokens, requirement-item and issue-reference patterns. Every extra value used is embedded in `registry_entries`, so replaying those entries with `--agent-input` on a machine without the toml or the local layer reproduces the payload byte-for-byte. A replayed toml value applies to that call only and is never written to disk.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
