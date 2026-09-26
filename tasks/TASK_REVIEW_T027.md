# TASK_REVIEW — T027: MCP detect gate — `needs_input.picks` candidates

> Sibling of `tasks/TASK_GUIDE_T027.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t027_detect_gate.py` (AC1–6, 8, 9 partly, round-trip, CLI never emits); `tests/integration/test_adapter_parity.py::test_combined_score_and_discovery_match_across_adapters` (AC7, updated to declare the `needs_input` exclusion) |
| Verification command run | ☑ pass | `PYTHONPATH=src <main>/.venv/bin/python -m pytest -q` → `668 passed, 2 skipped in 23.93s`; `... -m ruff check src tests` → `All checks passed!` |
| Negative cases hold | ☑ pass | Fully-resolved fixture → no `needs_input` (`test_fully_resolved_repo_yields_no_needs_input`); no-candidate repo → `None` (`test_no_needs_input_when_no_candidate_exists`); vendor/secret/binary all excluded (`test_candidates_exclude_vendor_secret_and_binary`) |
| verify | ☐ pass / ☐ fail / ☐ N/A | Not run by the implementer — user-invocation-only per `memory/MEMORY.md`; Stage 4/5 reviewer to run `Skill({ skill: "verify" })` |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Touched only `core/gate.py` (new), `core/score.py` (added field + one call site), `adapters/mcp_server.py` (`score` tool only), plus the parity test's `needs_input` exclusion. `adapters/cli.py`, `core/judge.py`, `core/redact.py`, `core/budget.py`, `Dockerfile`, `compose.yaml` untouched, matching the guide's Files-Must-NOT-Touch table |
| Full smoke suite still green (no regression) | ☑ pass | Same `668 passed, 2 skipped` run above includes the full pre-existing suite, including T026's tests and the adapter-parity integration tests |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend/MCP task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend/MCP task, no UI component |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend/MCP task, no UI component |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (2026-09-26 16:00:37 UTC — implementation stashed via `git stash -u` on top of
`e630b9c`, the merged T026 tip, then popped back afterward; no implementation commit existed at
capture time). Fixture: a repo containing only `notes/product-brief.md` (an unmatched doc; no file
matches `requirements-doc`/`spec-doc`/`task-breakdown`). Called MCP `score` in-process via
`mcp.call_tool` (the same mechanism `.claude/skills/verify/SKILL.md`'s stdio_client recipe drives,
adapted to call the FastMCP instance directly):

```
$ date -u
Sat Sep 26 04:00:37 PM UTC 2026
has needs_input key: False
has requirement-fidelity abstention: [{'kind': 'rating_abstention', 'dimension': 'requirement-fidelity',
 'reason_code': 'below_coverage_floor', 'reason': 'achieved coverage is below the declared floor',
 'coverage_floor': 0.5, 'achieved_coverage': 0.0,
 'sources_missing': [
   {'source': 'requirements-doc', 'reason': "not found: no file in the repository matched this role's patterns"},
   {'source': 'spec-doc', 'reason': "not found: no file in the repository matched this role's patterns"},
   {'source': 'task-breakdown', 'reason': "not found: no file in the repository matched this role's patterns"}],
 'failure': None, 'unavailable_metrics': [], 'abstentions': []}]
$ date -u
Sat Sep 26 04:00:38 PM UTC 2026
```
The `score` response has no `needs_input` key at all, while `requirement-fidelity` abstains below
its coverage floor because `requirements-doc`/`spec-doc`/`task-breakdown` are unfilled — exactly the
gap this task closes: the caller sees the abstention but is given nothing that could resolve it, and
`notes/product-brief.md` (a real, unmatched candidate sitting right there) is never surfaced.

**AFTER** (2026-09-26 16:00:13 UTC, same fixture, same in-process MCP call, on the implemented
code):

```
$ date -u
Sat Sep 26 04:00:13 PM UTC 2026
has needs_input: True
{
  "picks": {
    "decision-record": {"candidates": [{"path": "notes/product-brief.md", "heading": "Product Brief"}], "omitted": 0},
    "spec-doc": {"candidates": [{"path": "notes/product-brief.md", "heading": "Product Brief"}], "omitted": 0},
    "requirements-doc": {"candidates": [{"path": "notes/product-brief.md", "heading": "Product Brief"}], "omitted": 0},
    "readme": {"candidates": [{"path": "notes/product-brief.md", "heading": "Product Brief"}], "omitted": 0},
    "task-breakdown": {"candidates": [...]}
  }
}
$ date -u
Sat Sep 26 04:00:13 PM UTC 2026
```
`score` now returns `needs_input.picks` naming `requirements-doc` (among the other unfilled
doc-shaped roles) with `notes/product-brief.md` as a redacted `{path, heading}` candidate, alongside
the unchanged full ratings/overall payload. A follow-up call with
`agent_input={"picks": {"requirements-doc": ["notes/product-brief.md"]}}` (see
`tests/test_t027_detect_gate.py::test_picks_round_trip_raises_coverage_and_shows_provenance`)
returns `needs_input=None` and shows `requirement-fidelity` provenance
`"rules + agent picks (1 file)"`.

**DELTA**: A calling agent can now discover, from `score`'s own response, which unfilled source
roles have a real repository file that could fill them — and resolve that in one extra round trip —
instead of seeing only an unexplained abstention with no path forward. A fully-resolved repo, or a
repo with genuinely nothing eligible, spends zero extra tokens (no `needs_input` key at all).

**WITNESS**: backend-developer (implementing agent), both BEFORE and AFTER captures run in this
session, 2026-09-26, `feat/T027-detect-gate` worktree at
`/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T027`.
