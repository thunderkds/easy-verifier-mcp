# TASK_REVIEW — T123: Report sensitivity notice names where the report was actually written

> Sibling of `tasks/TASK_GUIDE_T123.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t123_advisory_location.py` (7 tests: default text in HTML + advisory, unset/empty env = default, env set = outside-repo text identical in HTML and advisory and no 'inside', NFR-011 phrases in both). Run 2026-10-21: `9 passed, 3300 deselected` for `-k "report and advisory"` |
| Verification command run | pass | `uv run --python 3.12 --extra dev python -m pytest tests -k "report and advisory" -q` -> `9 passed, 3300 deselected in 2.02s`; ruff check clean |
| Negative cases hold | pass | empty `EASY_VERIFIER_REPORTS_DIR` gives the default text; env-mode text never contains 'inside the evaluated repository' |
| verify | pass | Skill not invoked by the implementer; end-to-end check by running real `write_report` with env set and unset (AFTER capture): HTML notice equals returned advisory, text correct - pass. Supervisor re-run at Stage 5 still required. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Affected set: report.py notice/selection, T013/T070/T120/T001 report and env-read tests (130 passed) plus the full suite. `code-review` skill not run by the implementer. |
| Full smoke suite still green (no regression) | pass | `3306 passed, 3 skipped in 679.80s`, exit 0 (container-parity test did not fail here) |
| **UI: Visual regression (diff or verdict pasted)** | N/A | The existing notice element's text changes, not its layout. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | The existing notice element's text changes, not its layout. |
| **UI: Responsiveness at target viewports** | N/A | The existing notice element's text changes, not its layout. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-21T12:24:25Z on the unmodified branch (`write_report` on a tiny fixture repo, once with the env unset, once with `EASY_VERIFIER_REPORTS_DIR=<tmp>/shared`; the HTML notice and the returned `advisory` printed):

```
mode: env
advisory: Sensitivity notice: this report is written inside the evaluated repository, so it can be committed ... [identical to the default mode, 'same: True']
html notice: Sensitivity notice: this report is written inside the evaluated repository, so it can be committed ...
```
With the env set the report was written under `<tmp>/shared/target/`, yet the notice still said "inside the evaluated repository" (both modes print the identical text).

**AFTER**: captured 2026-10-21T12:26:03Z, same script, env set (HTML notice and returned `advisory` identical, `same: True`):

```
advisory: Sensitivity notice: this report is written outside the evaluated repository, in the shared reports directory, so it can be copied from there, attached to a ticket, or pasted into a pull request — and in MCP mode the same evidence also reaches the calling agent, which may be a hosted model outside your control. Secrets detected while gathering evidence are replaced by non-reversible fingerprints before they reach this document, but excerpts still quote real source code and file paths from this repository. Review before sharing it anywhere either destination can carry it.
```
With the env unset the text is the unchanged `SENSITIVITY_ADVISORY` ("written inside the evaluated repository").

**DELTA**: A reader of a report written to the shared reports directory is now told it sits outside the evaluated repository, instead of being told it is inside it.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
