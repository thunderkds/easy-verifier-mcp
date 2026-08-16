# TASK_REVIEW — T006: findings.py — finding schema + write_report validation

> Sibling of `tasks/TASK_GUIDE_T006.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t006_findings.py` — 29 tests, one named per rejection reason (AC #2/#3/#4/#6/#7/#10), plus multi-error (AC #8), no-write (AC #9), grouping (AC #12), schema (AC #1/#11), and the edge cases from the guide's checklist. |
| Verification command run | ☑ pass | `.venv/bin/python -m pytest tests/test_t006_findings.py -q` → `29 passed in 0.03s` (run 2026-08-15, worktree `agent-adc9574f95a28bdfe`, post-commit `cf0f486`). |
| Negative cases hold | ☑ pass | Missing confidence, missing evidence, both missing, dangling ref, dangling-into-truncated-pack, unrun dimension, out-of-domain/empty/null confidence, non-canonical ref shapes, unknown field, >500-finding payload, malformed JSON string — each is its own named test and each raises `ValidationError`. |
| verify | ☑ pass | **Run independently by the Supervisor at Stage 5, 2026-08-16** — the agent could not (`Skill` disabled in its session, so it left the row unticked rather than claiming a pass). Feature confirmed working against a **real pack from a real `run_dimension()` call**, not a hand-built fixture — `evidence_ref` resolution is only meaningful against genuine excerpt refs, so the check used `run_dimension(architecture, ".")` → ref `PROJECT_SPEC.md:1-138` — **pass**:<br>`valid finding → ACCEPTED (1 finding, by_dimension={'architecture': 1})`<br>`empty list → ACCEPTED (0 findings)`<br>`missing confidence → REJECTED: finding[0] [confidence]: missing confidence value`<br>`dangling ref → REJECTED: finding[0] [evidence_ref]: evidence_ref 'nope.md:1-2' not found in pack`<br>`unrun dimension → REJECTED: finding[0] [dimension]: dimension 'security' was not run`<br>`two problems at once → REJECTED: 2 finding(s) failed validation` — confirms AC #8 reports every problem rather than stopping at the first. Error strings name index, title, field and reason (AC #5). |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `src/easy_verifier/core/findings.py` (new), the 8-line additive `ref` property on `Excerpt` in `src/easy_verifier/core/models.py` (diffed against `develop`'s copy to confirm no other field touched), `tests/test_t006_findings.py` (new). Skipped: `core/context.py`, `core/redact.py`, `dimensions/*` — untouched, owned by T002/T004/other tasks. |
| Full smoke suite still green (no regression) | ☑ pass | `.venv/bin/python -m pytest -q` (whole `tests/` dir, includes T001's and T002's suites) → `78 passed in 0.18s`, same session. |
| **Stage 4 `code-review` (Supervisor-run)** | ☑ pass | Run 2026-08-15. **P0: 0 · P1: 0 · P2: 0 · P3: 0 — no findings.** Independently verified from the main checkout: 78 tests pass; `pipeline.py` untouched; the `models.py` addition is a *property*, not a field, so it cannot conflict with T002's and T004's concurrent field additions in the same file. Validation semantics probed directly rather than read: missing-confidence, missing-evidence_ref, both-missing, empty-string confidence, numeric `"0.9"`, dangling ref, and unrun dimension are each rejected; a valid finding and an empty findings list are accepted; and a 2-problem submission reports **2** errors rather than stopping at the first (AC #8). Error text names index, title, field and reason (AC #5). |
| **Stage 4 `security-review` (Supervisor-run, mandatory at Medium risk)** | ☑ pass | Run 2026-08-15. **0 HIGH, 0 MEDIUM.** No `subprocess`/`eval`/`exec`/`pickle`/`yaml.load`/`shell=True`, no network imports. `findings.py` performs no filesystem writes at all, so AC #9 ("no report written on rejection") holds structurally rather than by convention. `suggestion` is carried as inert text with a type check and is never interpreted (FR-024). `ruff check` clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend-only module; no UI component. UI section not applicable per TASK_GUIDE (pure-backend task). |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend-only module; no UI component. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend-only module; no UI component. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: (2026-08-15T09:50:16Z, `.venv/bin/python -c "from easy_verifier.core import findings"`,
run against the worktree in its state at that moment — before `findings.py` or
`test_t006_findings.py` were written, and before any implementation commit existed)
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ImportError: cannot import name 'findings' from 'easy_verifier.core' (/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.claude/worktrees/agent-adc9574f95a28bdfe/src/easy_verifier/core/__init__.py)
```
`ls src/easy_verifier/core/` at the same timestamp: `context.py __init__.py models.py pipeline.py __pycache__ redact.py` — no `findings.py`. There is no
`validate_findings` anywhere; an LLM-authored finding with a missing or dangling
evidence reference has nothing stopping it from reaching a report today.

**Session-interruption note (honesty, not fiction):** the agent session was terminated by a
session limit shortly after this capture and before any git commit was made. `findings.py`
and `tests/test_t006_findings.py` survived on disk as untracked files; the worktree's branch
was still at the harness's root-commit defect (`0242067`), unrelated to `develop`. On resume,
the branch was re-pointed onto `develop` (`git switch -C ... develop`) after deleting the
stray untracked copies of tracked repo files (`CLAUDE.md`, `PRD.md`, etc. — `develop`'s
versions are authoritative) and backing up the two real deliverables plus this file outside
the worktree first. No BEFORE was re-captured after the interruption: the capture above is the
original, genuine one, taken before the first line of `findings.py` was written, and it is
reproduced verbatim here from the pre-interruption backup rather than staged for effect.

**AFTER**: (2026-08-15T10:47:24Z, `.venv/bin/python -c "from easy_verifier.core.findings import
validate_findings, ValidationError; ..."`, run post-implementation, post-commit `cf0f486`)
```
REJECTED: 2 finding(s) failed validation: finding[0] ('t') [evidence_ref]: missing evidence reference; finding[0] ('t') [confidence]: missing confidence value
```
A finding submitted with neither an evidence reference nor a confidence value is now rejected,
by name and by field, rather than silently reaching a report.

**DELTA**: `write_report`'s eventual caller can no longer get an unevidenced or unconfidenced
finding into a report — `validate_findings` rejects it, naming the finding and the exact missing
or dangling field, before any rendering can happen.

**WITNESS**: Backend-Implementer (this agent), self-run — both captures above were run directly by
this agent in its own worktree; no independent witness available in this session. Stage 4/5
review (Supervisor or an independent agent) should re-run
`.venv/bin/python -m pytest tests/test_t006_findings.py -q` from
`memory/event-trace/T006.jsonl` to confirm independently, per the Evidence table below.
