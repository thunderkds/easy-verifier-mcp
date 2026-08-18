# TASK_REVIEW — T007: Shared doc-extraction helper + solution-fit, requirement-fidelity, code-quality

> Sibling of `tasks/TASK_GUIDE_T007.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t007_doc_dimensions.py` — `55 passed in 0.38s`, covering all 10 ACs plus standalone docs-first/code fallback, real source-file redaction, task-guide glob safety, nested requirement sections, truthful secret-file miss reasons, resolved-target secret aliases, and non-Markdown config extraction. `tests/test_t001_pipeline.py::test_registry_is_a_plain_dict_of_descriptors` covers the expanded registry. |
| Verification command run | ☑ pass | Supervisor rerun in the assigned worktree: `PATH=.venv/bin:$PATH PYTHONPATH=src pytest tests/test_t007_doc_dimensions.py -q` → `55 passed in 0.38s`. All four CLI dimensions were run independently with `PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli <dimension> --repo . --budget-bytes 256`; each returned a well-formed kit-aware pack and exit 0. |
| Negative cases hold | ☑ pass | Empty repo yields no invented evidence; escaping symlinks are not followed; absent/escaping/directory secret-shaped paths retain truthful reasons; `.env*`/key files are never read; safe-name symlinks resolving to secret-bearing targets are excluded in direct, discovered-doc, and task-glob paths; standalone code fallback fingerprints a runtime-assembled fake credential in a real `.py` source while `.env` remains unread. |
| verify | ☑ pass | Supervisor Stage 5 equivalent (Codex cannot invoke Claude's built-in `verify`): focused `55 passed in 0.38s`; full `279 passed in 1.01s`; `ruff check src tests` → `All checks passed!`; changed-file `ruff format --check` → `4 files already formatted`; `git diff --check develop...HEAD` → exit 0. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `dimensions/_doc_extract.py` (new), `dimensions/{solution_fit,requirement_fidelity,code_quality,architecture}.py`, `dimensions/__init__.py`, `core/context.py` (DDR-0002 exclusion added to `read_source`, the only shared-code change), `tests/test_t007_doc_dimensions.py`, one assertion update in `tests/test_t001_pipeline.py`. Skipped: `core/pipeline.py`, `core/budget.py`, `core/redact.py`, `core/scope.py` — untouched, contract unchanged, exercised only through their existing public seams. |
| Full smoke suite still green (no regression) | ☑ pass | `279 passed in 1.01s` (224-test develop baseline; +55 T007 tests) |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | No UI in this project (PROJECT_SPEC.md Constraint 11) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No UI in this project |
| **UI: Responsiveness at target viewports** | ☐ N/A | No UI in this project |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-17T03:20:27Z, before any T007 implementation commit):
```
$ PYTHONPATH=src python -m easy_verifier.adapters.cli code-quality --repo .
usage: easy-verifier [-h] [--repo REPO] [--budget-bytes BUDGET_BYTES]
                     {architecture}
easy-verifier: error: argument dimension: invalid choice: 'code-quality' (choose from 'architecture')
```
Only `architecture` was registered; `solution-fit`, `requirement-fidelity` and `code-quality` did
not exist as CLI choices at all.

**AFTER** (captured 2026-08-17T03:26:54Z):
```
$ PATH=.venv/bin:$PATH PYTHONPATH=src pytest tests/test_t007_doc_dimensions.py -q
.......................................................                  [100%]
55 passed in 0.38s

$ for d in architecture solution-fit requirement-fidelity code-quality; do \
    PYTHONPATH=src python -m easy_verifier.adapters.cli "$d" --repo . | head -5; done
{
  "dimension": "architecture",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
{
  "dimension": "solution-fit",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
{
  "dimension": "requirement-fidelity",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
{
  "dimension": "code-quality",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
```

**DELTA**: A caller can now request evidence packs for all four document-shaped dimensions
(`architecture`, `solution-fit`, `requirement-fidelity`, `code-quality`) — not just
`architecture` — each with a distinct, auditable `sources_sought` checklist and distinct coverage
score, all four sharing one extraction helper (`dimensions/_doc_extract.py`) that neither invented
content nor bypassed secret exclusion (DDR-0002) or redaction (NFR-010) to produce them.

**WITNESS**: Backend-Implementer (`backend-developer`), 2026-08-17, ran both captures directly in
`/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-t007` as part of this task.

---

## Stage 4 Review Summary

- **P0: 0.**
- **P1: 7 fixed.** The original review fixed under-matched `.env*` / `credentials*` patterns. The resumed review fixed six additional contract defects: secret exclusion ordering, missing standalone docs/code fallback, omitted task acceptance criteria, hierarchy-blind section boundaries, safe-name symlink aliases to secret files, and non-Markdown comments suppressing configuration evidence.
- **P2: 2 accepted.** (1) The architecture snapshot was committed with the refactor rather than carrying independently verifiable pre-refactor provenance; it remains a useful regression lock but is weaker evidence for AC #8. (2) A clipped subsection's marker mixes absolute file line positions with a section-relative total; citations remain accurate, but the explanatory wording can be clearer. Neither changes pack safety or acceptance behavior.
- **P3: 0.**
- Final independent re-review after commit `39edbd3` / cherry-pick `3c953b7`: **P0 0, P1 0**. No blocking findings remain.
