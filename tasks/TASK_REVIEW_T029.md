# TASK_REVIEW — T029: Bugfix: redact.py high_entropy_string false positive on ordinary filenames

> Sibling of `tasks/TASK_GUIDE_T029.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t029_redact_filenames.py` — 18 tests (AC1 reproducer, AC2 repo-wide `git ls-files` sweep, AC3 8 still-fingerprinted cases, AC4 role widened + citation resolves); 10 fail on pre-fix code. Supervisor re-run: `758 passed, 2 skipped in 24.94s`, exit 0 |
| Verification command run | ☑ pass | Supervisor, 2026-09-28: `python -m pytest -q` → `758 passed, 2 skipped in 24.94s` (exit 0); `python -m ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Supervisor probes: `see pB4kQ9…vY8w.txt` → `see pB4k…****:264aeebb1563.txt`; AWS key → `wJal…****:78314b11be2e`; `ghp_…12.md` → `ghp_…****:8d6534e05872.md`; 170-segment adversarial name ×50 redacts in 2 ms (no ReDoS) |
| verify | ☑ pass | Real CLI surface 2026-09-28 05:02 UTC: `python -m easy_verifier.adapters.cli architecture --repo . --scope project` cites `BRAINSTORMING_LOG_source-discovery.md`, `BRAINSTORMING_LOG_reference-registry.md`, `BRAINSTORMING_LOG_evaluation-areas.md`, `BRAINSTORMING_LOG.md` unredacted — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/redact.py` (`_entropy_spans` + new patterns, callers `scan`/`redact`), `core/roles.py` decision-record role, new test file. Code review: P0 0, P1 0, P2 0, P3 1 (guide counts stale: 205 paths / 6 affected, not 156 / 4). Security review inline (High risk): named detectors untouched; key-material + hex rules still run on exempt tokens; residual letters-only-before-suffix gap documented in docstring, accepted |
| Full smoke suite still green (no regression) | ☑ pass | full suite 758 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on pre-fix commit `4750b37`, before any implementation commit:

```
$ cd /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T029 && date -u && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('BRAINSTORMING_LOG_source-discovery.md'))"
Mon Sep 28 04:56:31 AM UTC 2026
BRAI…****:54e5675171d4.md
```

**AFTER**: captured by backend-developer on fix commit `e4f2537`:

```
$ cd /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T029 && date -u && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('BRAINSTORMING_LOG_source-discovery.md'))"
Mon Sep 28 05:00:40 AM UTC 2026
BRAINSTORMING_LOG_source-discovery.md
```

**DELTA**: Citations to ordinary word-joined filenames such as `BRAINSTORMING_LOG_source-discovery.md` now survive redaction and resolve, so the decision-record role matches `BRAINSTORMING_LOG*.md` again.

**WITNESS**: Supervisor re-ran the suite, probes and the CLI surface on 2026-09-28 (05:02 UTC), independent of the implementing agent.
