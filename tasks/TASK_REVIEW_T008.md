# TASK_REVIEW — T008: Security dimension

> Sibling of `tasks/TASK_GUIDE_T008.md`. Everything here is filled during Stage 4/5 review.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_t008_security.py` — 13 tests. Stage 4 remediation added two regressions pinning the confirmed P1s: `test_relevant_sources_outrank_alphabetically_earlier_filler` (AC #6, Critical Constraint 3) and `test_declared_sources_are_probed_so_miss_reasons_are_truthful` (AC #7/#11/#13). Both **failed on the pre-fix commit** (`29945d6`) and pass after: <br>`FAILED ...::test_relevant_sources_outrank_alphabetically_earlier_filler` <br>`FAILED ...::test_declared_sources_are_probed_so_miss_reasons_are_truthful` <br>`E  assert 'not examined...his dimension' == 'not found in...et repository'` <br>`2 failed, 11 deselected in 0.13s` |
| Verification command run | ☒ pass | `pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project \| head -30` → `13 passed in 0.26s`, then a valid JSON pack (`"dimension": "security"`, `"mode": "kit-aware"`, `"scope": "project"`, 77 `files_read`). The trailing `BrokenPipeError` is `head` closing the pipe on the CLI, not a dimension failure — unchanged from before this task. |
| Negative cases hold | ☒ pass | Miss list on this repo is now truthful in all three states — 9 declared sources report `not found in the target repository` (previously all fabricated as `not examined: the byte budget was reached before this source was read`), `git history (out of scope for v1)` reports `out of scope for v1: git history is not searched by this dimension`, and a seeded `.env` reports `excluded: secret-bearing; operator approval required` with one `ApprovalRequest` and zero raw values in the serialized pack (AC #11/#12 gate re-verified, not regressed). |
| verify | ☒ pass | Ran the dimension live against this repo post-fix: `coverage 0.0909…`, `found ('pyproject.toml',)`, `files_read 77 excerpts 15`, and every one of the 10 misses carries a reason that reflects what was actually checked. Pre-fix the same run reported four non-existent files (`.env`, `Dockerfile`, `package.json`, `src/auth.py`) as budget-exhausted. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Reviewed: `src/easy_verifier/dimensions/security.py` (the only source file changed) and `tests/test_t008_security.py`. Deliberately **not** changed: `core/pipeline.py::_missing_sources` (its `not examined` default is correct for the doc dimensions — the defect was security.py never probing), `core/redact.py` and `dimensions/_doc_extract.py` (Files Must NOT Touch), `core/context.py` (no new API needed; the pseudo-source and out-of-scope reasons append to the public `context.sources_missing` record). No shared machinery was touched. |
| Full smoke suite still green (no regression) | ☒ pass | `PATH=…/.venv/bin:$PATH PYTHONPATH=src python -m pytest -q` → `292 passed in 1.24s`, exit code `0` read directly (not piped). Baseline before the fix was 290 passed; the delta is exactly the two new regression tests. `ruff check .` → `All checks passed!`, exit `0`. |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Responsiveness at target viewports** | ☒ N/A | Pure backend task; no UI exists in v1. |

---

## Demonstration

**BEFORE**: 2026-08-19T03:09:11Z — `PYTHONPATH=src PATH=/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin:$PATH pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project | head -30`

```text
ERROR: file or directory not found: tests/test_t008_security.py


no tests ran in 0.00s
```

Exit status: 4.

**AFTER**: 2026-08-20 — `PYTHONPATH=src PATH=/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin:$PATH pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project | head -30`

```text
.............                                                            [100%]
13 passed in 0.26s
{
  "dimension": "security",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
    "pyproject.toml",
    "src/easy_verifier/dimensions/security.py",
    "AGENTS.md",
    ...
```

Exit status: 0 (the CLI's trailing `BrokenPipeError` is `head` closing the pipe, not a dimension failure).

Post-fix miss list on this repo (`scope=project`), which is the substance of the remediation:

```text
coverage 0.09090909090909091
found ('pyproject.toml',)
files_read 77 excerpts 15
 - requirements.txt :: not found in the target repository
 - package.json :: not found in the target repository
 - package-lock.json :: not found in the target repository
 - poetry.lock :: not found in the target repository
 - src/auth.py :: not found in the target repository
 - Dockerfile :: not found in the target repository
 - compose.yaml :: not found in the target repository
 - .github/workflows/ci.yml :: not found in the target repository
 - .env :: not found in the target repository
 - git history (out of scope for v1) :: out of scope for v1: git history is not searched by this dimension
```

**DELTA**: On a repository larger than the 200-file candidate cap the `security` dimension now returns its manifests, container and CI configuration instead of silently returning nothing, and every declared source in the miss list states what was actually checked — `not found`, `excluded: secret-bearing`, or `out of scope for v1` — rather than a fabricated "the byte budget was reached".

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T008.jsonl`, never the implementing agent alone]
