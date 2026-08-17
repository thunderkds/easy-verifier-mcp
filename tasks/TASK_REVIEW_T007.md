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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t007_doc_dimensions.py` (40 tests, all 10 ACs + full Edge Case Checklist) + 1 pre-existing test updated for the growing registry, `tests/test_t001_pipeline.py::test_registry_is_a_plain_dict_of_descriptors` |
| Verification command run | ☑ pass | `PYTHONPATH=src python -m pytest tests/test_t007_doc_dimensions.py -q` → `40 passed in 0.20s`; `for d in architecture solution-fit requirement-fidelity code-quality; do PYTHONPATH=src python -m easy_verifier.adapters.cli "$d" --repo . \| head -5; done` → all 4 print a well-formed pack header (`dimension`, `mode: kit-aware`, `scope: project`, `files_read`), exit 0 |
| Negative cases hold | ☑ pass | Empty repo → `coverage_score == 0.0`, no invented content (`test_code_quality_with_no_lint_config_has_zero_coverage_no_invention`, `test_requirement_fidelity_standalone_with_no_frs_states_the_miss_plainly`); symlink escape not followed (`test_symlink_to_outside_the_repo_is_not_followed`); `.env`/`id_rsa`/`.pem`/etc. never read (`test_secret_bearing_patterns_cover_the_ddr_list`, `test_secret_in_pyproject_is_fingerprinted_and_dotenv_is_never_read`) |
| verify | ☑ pass | Full repo test suite run post-implementation: `PYTHONPATH=src python -m pytest -q` → `264 passed in 0.81s` (0 regressions across T001–T006's suites) — skill run, feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `dimensions/_doc_extract.py` (new), `dimensions/{solution_fit,requirement_fidelity,code_quality,architecture}.py`, `dimensions/__init__.py`, `core/context.py` (DDR-0002 exclusion added to `read_source`, the only shared-code change), `tests/test_t007_doc_dimensions.py`, one assertion update in `tests/test_t001_pipeline.py`. Skipped: `core/pipeline.py`, `core/budget.py`, `core/redact.py`, `core/scope.py` — untouched, contract unchanged, exercised only through their existing public seams. |
| Full smoke suite still green (no regression) | ☑ pass | `264 passed in 0.81s` (was 224 pre-T007 per develop baseline; +40 new tests) |
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
$ PYTHONPATH=src python -m pytest tests/test_t007_doc_dimensions.py -q
........................................                                 [100%]
40 passed in 0.20s

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
