# TASK_REVIEW — T022: shared score operation and report panel

## Evidence

| Check | Result | Notes / output snippet |
|---|---|---|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | Pass | `tests/test_score_operation.py` contains 8 tests covering no-findings CLI scoring, all-abstained exit 0, CLI/MCP parity, findings file/stdin, assessments/divergences, numeric and abstaining report states, failed-dimension escaping, self-containment, path scrubbing, and structural adapter thinness. |
| Verification command run | Pass with environment substitution | The isolated clone has no `.venv`; `PYTHONPATH=src <compatible-venv>/bin/python -m pytest tests/test_score_operation.py -q` → **8 passed, 1 upstream warning in 0.76s**. |
| Negative cases hold | Pass | A deliberately empty standalone repo returns seven typed `rating_abstention` objects, no numeric `value` on any of them, an overall `no_dimension_rated` abstention, and exit 0. A fabricated collector failure renders as `dimension_failed`, is styled separately from a floor abstention, and escapes injected HTML. |
| verify | Pass via real CLI substitution | `score --repo . --scope project` at the real CLI exited 0 and returned seven numeric ratings, **77 cited metrics**, overall **65**, and disclosure `7 of 7 dimensions contributed ... none abstained`. The named `verify` skill is unavailable in this Codex session. |
| Review scope bounded to the change's blast radius | Pass | Reviewed the new core composition boundary, CLI/MCP registrations, report renderer and path/redaction chokepoints, changed tool-count assertions, README contract, and T013–T015/T018 compatibility. T019/T020/T021 arithmetic modules were not changed. Manual P0–P3 result: P0 0 / P1 0 / P2 0. The named `code-review` skill is unavailable in this Codex session. |
| Full smoke suite still green (no regression) | Pass | `PYTHONPATH=src <compatible-venv>/bin/python -m pytest -q` → **570 passed, 1 upstream Pydantic warning in 11.14s**. Ruff check passed, Ruff format passed, and `git diff --check` is clean. |
| **UI: Visual regression (diff or verdict pasted)** | N/A | No interactive UI exists (PROJECT_SPEC Constraint 11). The static HTML report is covered by parsed-document assertions and a generated all-abstained artifact; sandboxed Snap Chromium could not start because `/run/user/1000` is read-only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | No design system or UI surface; the report extends the existing self-contained inline CSS and adds no dependency. |
| **UI: Responsiveness at target viewports** | N/A | No application UI. The static report retains its viewport metadata and uses an auto-fit score grid; structural report tests pass. |

## Security review

N/A by task risk policy (Low). Direct substitution found no new filesystem, subprocess, network,
model-client, or outbound-request primitive. Findings still pass through `validate_findings`,
caller-authored prose through `_Ctx.agent_text`, metric paths through `_Ctx.path`, and failures
through `_Ctx.esc`. The score core delegates all reads to the pre-existing combined-pack pipeline.

## Demonstration

**BEFORE (2026-09-12):** focused test collection failed with
`ModuleNotFoundError: No module named 'easy_verifier.core.score'`; neither adapter registered a
`score` operation and reports had no quality panel.

**AFTER (2026-09-12):** the real CLI returned exit 0 with seven ratings, 77 cited metrics, overall
65, and its contributor/abstention disclosure. The same payload is returned by MCP; optional
findings add separate assessments and divergences; a report renders these signals without external
resources or container paths.

**DELTA:** an operator can now point either adapter at a repository and receive the complete,
inspectable quality result without an agent or findings, while reports render the same declared
signals.

**WITNESS:** Codex Supervisor, 2026-09-12, using the isolated `feat/t022-score` checkout and a
compatible provisioned Python environment.

## Review findings and remediation

| Severity | Finding | Remediation |
|---|---|---|
| P1 | The first renderer branch identified a numeric overall through an attribute that only the abstention type has, so a real numeric result would raise `AttributeError`. | Replaced attribute probing with exact typed branches and added a numeric-overall report regression test. |
| P1 | A failed dimension initially shared the same visual class as a below-floor abstention, leaving two distinct absence causes differentiated only by prose. | Added the validated reason code to the card class, a red failure treatment, and an escaped hostile-failure regression test. |
| P2 | `README.md` still claimed that the approved engine never returns a score. | Reframed the promise as no inferred verdict, documented declared ratings/assessments/divergence, and added the runnable score command to the existing doc-truth gate. |

Post-remediation result: P0 0 / P1 0 / P2 0.
