# TASK_REVIEW — T084: breaking metric counts read files only

> Sibling of `tasks/TASK_GUIDE_T084.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | tests/test_t084_breaking_read_only.py (7 tests, AC1-6); with test_t044_api.py: 27 passed |
| Verification command run | pass | full suite: 2 failed (pre-existing container tests test_adapter_parity/test_redaction_proof), 2536 passed, 2 skipped; ruff clean |
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

**BEFORE** (captured 2026-10-08T07:27:58Z, unmodified code at branch base, before any implementation commit):
Temp git repo: 22 dirs `svcNN/openapi.yaml`, each loses 3 spec lines (`/v1/bNN`, `get`, `summary`) in `HEAD~1..HEAD`; api pack reads only `MAX_SPEC_FILES`=20.
`python -m easy_verifier.adapters.cli score --repo <tmp> --scope changes --ref HEAD~1..HEAD </dev/null` -> api `breaking_api_changes_observed`:
`outcome.value = 66`, `computed_from` = svc01..svc20 (20 files), derivation "66 endpoint(s) or specification field(s) removed and not re-added in the diff: svc01/openapi.yaml:9 /v1/b01, ..." -- 66 = 22 x 3, so 6 of the removals come from svc21/svc22 which are not cited (uncited value).
coffee-shop-api `--scope project` sha256 baseline: sha256 2a12a8c9830ad14a0aa42d61883ae16ea7df368588ecc21811a216c216880c74 (2026-10-08T07:28:09Z).

**AFTER** (same repo and command, post-change): api `value = 60`, `computed_from` = svc01..svc20 (20 files); derivation "60 endpoint(s) ... removed ...; not counted (changed file(s) with removals this pack did not read): svc21/openapi.yaml (3), svc22/openapi.yaml (3); a removed route is ...". coffee-shop-api `--scope project` sha256 AFTER = 2a12a8c9...880c74, identical to BEFORE.

**DELTA**: the breaking-change count now equals exactly what it cites; removals in unread changed files are named as "not counted", and repo `route_tokens` conventions find removed custom routes.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
