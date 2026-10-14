# TASK_REVIEW — T071: Evaluation docs

> Sibling of `tasks/TASK_GUIDE_T071.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t071_evaluation_docs.py` — Supervisor re-run 2026-10-04: 77 passed (required guide sections; README section ≤25 lines + link; SCORING_FLOW sections link the guide; links/anchors resolve; every backticked identifier declared and found in src/; examples tied to real runs, blend example marked illustrative; no marketing adjectives / no 'judges quality' claim). Negative: renamed identifier BORDERLINE_BANDX → test failed naming it (agent) — pass |
| Verification command run | ☑ pass | `pytest tests/test_t071_evaluation_docs.py -q` → 77 passed; full suite (agent) 1869 passed, 2 failed = the 2 known stale-Docker container tests — pass |
| Negative cases hold | ☑ pass | undeclared backticked identifier fails the declared-list test; missing identifier fails the src-existence test — pass |
| verify | ☐ N/A | docs-only task (no src/ change); Supervisor read-through instead: guide answers the four questions (overall, trust, warnings, what to fix first); numbers match 2026-10-04 runs (nest-api 65 / 71 / 59, +21/+9/+5; node-monorepo 66 = round(65.5)) — N/A, read-through pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed docs/EVALUATION_GUIDE.md (165 lines), README 'Reading a report' (16 lines) + docs table row, SCORING_FLOW 'Evidence warnings' + 'Acting on the plan', new test. code-review: P0–P3 none. Accepted agent correction: false secret matches lower (not inflate) security — pass |
| Full smoke suite still green (no regression) | ☑ pass | docs + one test only; agent full suite 1869 passed with only the 2 pre-existing container failures — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | no UI change — docs only |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | no UI change — docs only |
| **UI: Responsiveness at target viewports** | ☐ N/A | no UI change — docs only |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (Supervisor, 2026-10-04, develop `88c883d`, verbatim headings before any T071 change; `docs/EVALUATION_GUIDE.md` does not exist):

```
README.md
1:# easy-verifier-mcp
9:## What it refuses to do
22:## The seven dimensions
36:## Scopes
52:## Two modes: kit-aware and standalone
61:## Running it
71:### CLI — no server or container required
104:#### How each dimension is rated
159:#### Source roles — any language, no configuration required
239:### MCP — stdio by default
254:### Docker — read-only target, writable reports only
267:### Final release gate
282:## Where reports go
292:## Documentation
302:## License

docs/SCORING_FLOW.md
1:# Scoring session flow (MCP)
12:## Flow
43:## The rounds
68:## Large repositories: priority batches
95:## Improvement plan
```

**AFTER** (branch `760af22`): new `docs/EVALUATION_GUIDE.md` sections — What you received / The overall number / When to trust a number / Warnings: what could not be measured / Large repositories: batches / Improvement plan / Engine text and agent text / The report, top to bottom / Act on it / Worked examples. README gains `## Reading a report`; SCORING_FLOW gains `## Evidence warnings` (Reading a warning) and 'Acting on the plan'.

**DELTA**: a reader who receives a score or report has one page that says what each part means, when to trust a number, and what to fix first.

**WITNESS**: Supervisor (main session), 2026-10-04 — test re-run and full read-through; not the implementing agent alone.
