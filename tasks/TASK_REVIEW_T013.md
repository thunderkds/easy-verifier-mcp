# TASK_REVIEW — T013: report.py — self-contained multi-dimension HTML report

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t013_report.py` — 39 tests, one or more per AC #1–#15 plus the edge-case checklist (read-only `reports/`, symlinked target repo, `reports/` symlinked out of the repo, zero findings, 300 findings, non-ASCII). `39 passed in 0.34s`, exit 0. |
| Verification command run | ☑ pass | `pytest tests/test_t013_report.py -q` → `39 passed`; the trailing `grep -cE 'https?://\|<script src\|@import'` on `/tmp/evtest/reports/*.html` prints **2**, and both hits are the fixture's URL rendered as *escaped text* inside an excerpt (`LOGO = &quot;https://cdn.example.com/logo.png&quot;`) — exactly the loose-grep false positive the guide's Test Plan predicted. The AC #2 check is the parsing scan in `_external_references()`, which returns `[]` on the same file. |
| Negative cases hold | ☑ pass | Six sabotages, each reverted after capture: **(A)** an external `<link>` in `<head>` → `test_report_requests_nothing_from_the_network` FAILED; **(B)** `O_EXCL`→`O_TRUNC` → `test_an_existing_filename_is_never_overwritten` FAILED; **(C)** a bare `pack.coverage_score` rendered in the pack-meta block → `test_every_rendered_score_sits_with_its_named_miss_list` FAILED (`assert 5 == 3`, "a coverage score appears outside a coverage entry"); **(D)** write-then-validate → both AC #9 tests FAILED; **(E)** `_Ctx.esc` returning text unescaped → 4 escaping tests FAILED; **(F)** a "helpful" Markdown subset added to `esc` → `test_no_markdown_subset_is_honoured` FAILED. |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☑ pass | `pytest tests -q` → `378 passed` (339 pre-existing + 39 new), exit 0. `ruff check src tests` + `ruff format --check` clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI in this project (`PROJECT_SPEC.md` Critical Constraint 11). This task renders a static document from structured data — no component, no interaction, no design system. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | As above — N/A per Critical Constraint 11. |
| **UI: Responsiveness at target viewports** | ☑ N/A | As above — N/A per Critical Constraint 11. The inlined CSS does carry a fluid `max-width` and `white-space: pre-wrap` on excerpts, but no viewport testing is claimed. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-25T09:53:41Z in worktree `easy-verifier-mcp-t013` at `5d61f46`, before
any implementation commit — `report.py` does not exist and the verification command's test file is
absent, so `write_report` cannot be called at all):

```
$ date -u
Tue Aug 25 09:53:41 AM UTC 2026
$ /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t013_report.py -q
ERROR: file or directory not found: tests/test_t013_report.py

no tests ran in 0.00s
exit=4
$ ls src/easy_verifier/core/report.py
ls: cannot access 'src/easy_verifier/core/report.py': No such file or directory
exit=2
```

**AFTER** (captured 2026-08-25T10:03:25Z, same worktree, at `6b5d401`+):

```
$ date -u
Tue Aug 25 10:03:25 AM UTC 2026
$ .venv/bin/python -m pytest tests/test_t013_report.py -q
.......................................                                  [100%]
39 passed in 0.34s
exit=0
$ ls -l /tmp/evtest/reports/
-rw-r--r-- 1 hungnguyenhuu hungnguyenhuu 9667 Aug 25 17:00 evidence-report-project-20260825T100038-582758Z.html
```

**DELTA**: A caller can hand validated findings plus a multi-dimension `CombinedPack` to
`write_report` and get one self-contained, collision-proof HTML report written into the *evaluated*
repository's `reports/` — every coverage score shown with its named miss list, every caller-supplied
string escaped, and nothing fetched from the network when the file is opened.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T013.jsonl`, never the
implementing agent alone]
