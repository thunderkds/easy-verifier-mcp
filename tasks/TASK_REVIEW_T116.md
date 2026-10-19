# TASK_REVIEW — T116: Vercel deploy configuration + runbook

> Sibling of `tasks/TASK_GUIDE_T116.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_site_deploy_config.py` (AC 1-3, Success 3; 7 tests). AC 4 is docs, reviewed by Supervisor. AC 5: README untouched (no confirmed project name). |
| Verification command run | ☑ pass | `PYTHONPATH=src:<main-checkout>/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest tests/test_site_deploy_config.py tests/test_t100_no_personal_identifiers.py -q` -> `10 passed in 2.81s`; `ruff check` -> `All checks passed!`; `ruff format --check` -> `1 file already formatted` |
| Negative cases hold | ☑ pass | `test_negative_extra_readmit_is_detected` (`!memory/`, `!tasks/**` added -> violations), `test_negative_removed_star_is_detected` (`*` removed -> violation); `test_gitignored_reports_and_memory_not_admitted`. |
| verify | ☐ N/A | No runnable surface until the operator connects Vercel; Supervisor re-runs at Stage 5. Config verified statically by the admitted-set test (exactly `site/**` + `vercel.json` on the real tree) - pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: vercel.json, .vercelignore, test, RELEASE_GUIDE section, absolute-path scan (t100). Skipped: site/**, src/** (untouched). |
| Full smoke suite still green (no regression) | ☐ fail (environment only) | Full `pytest -q --tb=line`: `1 failed, 3209 passed, 3 skipped, 3 errors in 776.79s`. Failures are the known environment ones under the workaround interpreter, not T116: `test_t014_mcp_server.py::test_module_import_emits_nothing_to_stdout` (`ModuleNotFoundError: No module named 'mcp'`) and 3 errors in `test_t101_shared_container.py`. The full run predates `ruff format` of the new test file (7 passed in it then); the 10-test run above is post-format. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | config + docs only, no rendered surface |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | config + docs only, no rendered surface |
| **UI: Responsiveness at target viewports** | ☐ N/A | config + docs only, no rendered surface |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-19 04:44:02 UTC in the T116 worktree, before any implementation commit:
```
$ date -u; ls vercel.json .vercelignore tests/test_site_deploy_config.py; grep -n "Landing site" docs/RELEASE_GUIDE.md
Mon Oct 19 04:44:02 AM UTC 2026
ls: cannot access 'vercel.json': No such file or directory
ls: cannot access '.vercelignore': No such file or directory
ls: cannot access 'tests/test_site_deploy_config.py': No such file or directory
(grep: no match, exit=1)
```

**AFTER**: same files present in the T116 worktree: `vercel.json` = `{"outputDirectory": "site"}`; `.vercelignore` = `*`, `!site/`, `!site/**`, `!vercel.json`; `tests/test_site_deploy_config.py` -> `10 passed in 2.81s` (with t100); `docs/RELEASE_GUIDE.md` has `## Landing site`.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T116.jsonl`, never the
implementing agent alone]
