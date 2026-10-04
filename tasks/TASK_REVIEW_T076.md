# TASK_REVIEW — T076: Whole-file code metrics below the cap

> Sibling of `tasks/TASK_GUIDE_T076.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t076_whole_file_metrics.py` (5 tests: truncated under-cap pack still computes cycles/CCN; oracle equals direct computation; 'all N source files' disclosure, no sample/samples/continue_batches; secret-bearing file refused; zero sources abstain). 3 of 5 fail on pre-fix src (agent stash check) — pass |
| Verification command run | ☑ pass | Agent full suite 1956 passed, 2 skipped, 2 failed (known stale-Docker container tests); ruff clean — pass |
| Negative cases hold | ☑ pass | secret-bearing source still refused; zero sources abstain; t068 under-cap snapshot: no rating/overall change; type_escapes_per_kloc 19.71→15.99 = removal of double-counted overlapping excerpts (true count 17) — pass |
| verify | ☑ pass | Supervisor 2026-10-04 10:58 UTC CLI score: coffee-shop-api overall 70 (architecture 80, code-quality 71); bryony 69 (architecture 83, code-quality 67); kitchd 37→61 (architecture insufficient_measured_weight→100 from import cycles over all 185 source files; code-quality insufficient_measured_weight→70) — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed _code_extract.record_sample under-cap path, EvidencePack.whole_file (omitted when absent), compute_metrics merge, pipeline one-liner, test updates. code-review: P0/P1 none. Accepted: new `whole_file` pack key instead of reusing `sample` (keeps AC2). Noted pre-existing: excerpt-based metrics in a non-owning dimension's pack still abstain on truncation (not rated there); doc reads may repeat in files_read — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1956 passed; only the 2 pre-existing container failures — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | no UI change |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | no UI change |
| **UI: Responsiveness at target viewports** | ☐ N/A | no UI change |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (Supervisor, 2026-10-04 10:43 UTC, plan/code-derived-rules at T074): kitchd architecture `insufficient_measured_weight`; `top_level_import_cycles` and `layer_direction_violations` abstained: "whole-set-dependent: the byte budget truncated this pack, so any ratio, density or share computed here describes what survived the budget, not the repository". kitchd architecture pack: 140 files read, 140 excerpts, 119,366 bytes, truncated (omitted 1) — identical before and after T074.

**AFTER** (Supervisor, 2026-10-04 10:58 UTC, `09a2d84`): kitchd architecture 100 (import cycles over all 185 source files), code-quality 70, overall 61; coffee-shop-api and bryony unchanged from T074 (70 / 69).

**DELTA**: small repositories get their code structure metrics computed over whole files, so a truncated excerpt budget no longer hides them.

**WITNESS**: Supervisor, 2026-10-04 — three real-repo score runs.
