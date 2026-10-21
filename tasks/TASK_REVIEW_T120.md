# TASK_REVIEW — T120: Score JSON sidecar next to each HTML evidence report

> Sibling of `tasks/TASK_GUIDE_T120.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t120_report_json.py` (13 tests, one per AC 1-6 plus env dir/non-ASCII, collision, guard) |
| Verification command run | pass | `uv run --python 3.12 --extra dev python -m pytest tests -k "report and json" -q` -> `9 passed, 3268 deselected in 2.13s` |
| Negative cases hold | pass | Unevidenced finding -> ValidationError, no `reports/` dir; JSON open denied -> no files left (sabotage: removing the HTML unlink makes `test_report_json_failure_leaves_no_half_pair` fail); canary absent from JSON; abstain is `null`, never 0 |
| verify | ☐ N/A | not run by the implementing agent; the Demonstration AFTER shows the pair written (pass), but the rescoring regression above is open |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Diff reviewed directly: `core/report.py` only (write path, `_scope_label` extracted from `_filename`); `_render_*`, `SENSITIVITY_ADVISORY`, dimensions untouched. Built-in security-review not run (resolves origin/HEAD). The JSON holds numbers and reason codes only |
| Full smoke suite still green (no regression) | pass | `uv run --python 3.12 --extra dev python -m pytest tests -q` -> `3278 passed, 3 skipped in 667.98s (0:11:07)`. Includes the two replay tests and the existing project-scope snapshot/byte-equality tests (no sidecar in those repos, so payloads unchanged). Earlier run (before the walk fix) had 2 replay regressions caused by the sidecar being re-ingested |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | no UI |
| **UI: Responsiveness at target viewports** | ☐ N/A | no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (2026-10-21T10:57:49Z, develop code at 5a19bd2, no implementation commit yet; script
`demo.py` builds a 2-file repo, `combined_pack` over all dimensions, `write_report([], ...)`):

```
$ EASY_VERIFIER_REPORTS_DIR=$D/reports PYTHONPATH=src uv run --python 3.12 python demo.py $D
wrote $D/reports/demo-repo/evidence-report-project-20261021T105750-225561Z.html
$ ls -la $D/reports/demo-repo
-rw-r--r-- 1 user user 90210 Oct 21 17:57 evidence-report-project-20261021T105750-225561Z.html
```
Only the `.html` exists; no JSON sibling.

**AFTER** (2026-10-21T11:21:31Z, same command, commit 770fa38):

```
wrote $D/reports/demo-repo/evidence-report-project-20261021T112131-779658Z.html
-rw-r--r-- 1 user user 90210 Oct 21 18:21 evidence-report-project-20261021T112131-779658Z.html
-rw-r--r-- 1 user user  1419 Oct 21 18:21 evidence-report-project-20261021T112131-779658Z.json
{"dimensions":[{"abstained":true,"dimension":"api","rating":null,"reason_code":"below_coverage_floor"},
 ... ], "generated_at":"2026-10-21T11:21:31Z", "overall":{...}, "schema_version":1, "scope":"project"}
```

**DELTA**: A program (easy-personal) can read a report's scores from a JSON file next to the HTML instead of parsing HTML.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]

## Scope extension (authorised by Supervisor 2026-10-21: prevent sidecar re-ingestion)

The JSON sidecar was being walked as a source file on the next score of the same repo (file counts
changed, filename redacted as high-entropy). One predicate `_is_report_artifact` (`core/context.py`,
regex of the exact generated name `evidence-report-<scope>-<UTC>[-N].json`, any directory) is now used
in `context._walk`, `scope._walk_files` and `roles._in_excluded_dir`. User files `evidence-report.json`
and `report.json` still walk. Tests in `tests/test_t120_report_json.py` pin the predicate against the
real written names, the walks, the role check and a rescore that ignores the previous sidecar.
