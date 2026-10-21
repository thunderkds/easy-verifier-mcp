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
| verify | ☑ pass | Supervisor Stage 5, 2026-10-21: MCP stdio `write_report` (findings=[], worktree scope) on a throwaway git repo. Env unset → advisory 'written inside the evaluated repository', HTML marker "…repository's reports/ directory". `EASY_VERIFIER_REPORTS_DIR` set → advisory 'written outside the evaluated repository, in the shared reports directory', HTML marker '…folder in the shared reports directory', no 'inside' text — pass |
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

**WITNESS**: Supervisor (main session), 2026-10-21 — the independent MCP stdio run above, traced in `memory/event-trace/T123.jsonl`. Implementer full suite 3306 passed / 3 skipped before the marker follow-up; after the follow-up the report test files gave 133 passed.

---

## Addendum (Supervisor decision 2026-10-21): first-write marker

The first-write marker follows the same `reports_dir.is_relative_to(repo)` decision as the notice (`_notice_texts`, computed once in `write_report`). Inside the repo it is unchanged; with the shared dir it reads "This is the first report written into this repository's folder in the shared reports directory." An env dir inside the repo gets the inside texts (pinned by a test).

Run 2026-10-21 (ruff check: All checks passed):
```
-k "report and advisory": 12 passed, 3300 deselected in 2.61s
tests/test_t001_pipeline.py test_t013_report.py test_t070_report_readability.py test_t120_report_json.py test_t123_advisory_location.py: 133 passed in 15.15s
```
Full suite not re-run for this change (per Supervisor); the earlier full run was 3306 passed, 3 skipped.

## Stage 4 — Supervisor review (2026-10-21)

- code-review: P0 0 · P1 0 · P2 0 · P3 0. The text is chosen once (`_notice_texts`, from the resolved `reports_dir.is_relative_to(repo)`) and passed to both the HTML and the returned `advisory`; `_reports_dir` stays the only env reader (pinned by `test_package_never_reads_the_environment`); `SENSITIVITY_ADVISORY` is unchanged byte for byte. Scope grew by the first-write marker (Supervisor decision: same defect). An env dir inside the repo gets the "inside" text, and a test pins it.
- security-review: Low risk, not required. The NFR-011 exposures (hosted model, excerpts quote real source) are kept in both texts, and a test checks that. — pass
