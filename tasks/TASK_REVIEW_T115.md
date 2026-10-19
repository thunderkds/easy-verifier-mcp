# TASK_REVIEW — T115: Static landing page + self-score snapshot + drift test

> Sibling of `tasks/TASK_GUIDE_T115.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_site_content.py` (14 tests, AC 1-9): `14 passed in 0.39s`. After the Stage 4 P3 fixes (015ada2): 16 tests; Supervisor re-run with test_t100: `19 passed in 0.91s`, ruff `All checks passed!` |
| Verification command run | ☑ pass | `PYTHONPATH=src:<venv-site-packages> /usr/bin/python3.12 -m pytest tests/test_site_content.py -q` -> `14 passed`; `ruff check` -> `All checks passed!` |
| Negative cases hold | ☑ pass | `test_extra_area_makes_check_fail`, `test_extra_dimension_makes_check_fail`, `test_wrong_status_makes_check_fail` pass (injected fake area/dimension/status makes the check raise naming it); `test_site_files_are_publication_safe` scans every file under `site/` for host paths, emails and `redact.scan` hits |
| verify | ☑ pass | page served with `python -m http.server` and loaded in headless Chrome at 375/768/1280: no page-level horizontal scroll, body 16px system font, tables scroll inside `.table-wrap` — pass Supervisor Stage 5 re-run on 015ada2 (2026-10-19): served site/ on 127.0.0.1:8799, headless Chrome --dump-dom shows all six sections (what, run, dimensions, areas, scoring, sample) and data-overall="47"; server log shows only GET / (plus the browser's favicon 404), no other asset fetched; 375px screenshot read: commands and tables scroll inside their containers, no page-level horizontal scroll. Observation (not a defect): at 375px the 32-areas Status column starts off-screen and needs a horizontal swipe. Result: pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the three new files only (`site/index.html`, `site/sample-score.json`, `tests/test_site_content.py`); no `src/` change, no importers |
| Full smoke suite still green (no regression) | ☑ pass (with 4 environment failures, not regressions) | Full run on the pre-merge branch: `1 failed, 3199 passed, 3 skipped, 1 deselected, 3 errors`. The failure was test_t100 (a host path in the T115/T116 guides, fixed on develop in 90c2b11, merged in 6d0fcda). Post-merge targeted rerun: test_t100 passes; the remaining `test_t014::test_module_import_emits_nothing_to_stdout` failure and 3 `test_t101_shared_container` errors are environment failures: their subprocesses cannot import `mcp` under the broken-venv PYTHONPATH workaround. test_t014 fails identically on develop without T115 files (implementer baseline). They must be re-confirmed in a rebuilt venv (RUNBOOK pre-release check 1). T115 touches no file those tests exercise. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | Playwright is not installed; used headless Chrome full-page screenshots (no baseline, new page). Agent-vision verdict: all six sections present, scorecard legible, areas table shows `rule` / `pack: <name>` / `no rule` markers distinctly. Shots kept in the scratchpad (not committed) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | Colors are `:root` custom properties with an `@media (prefers-color-scheme: dark)` variant; computed body font 16px, system font stack, monospace for code. Contrast measured by the Supervisor at Stage 4 (WCAG 2 relative-luminance formula over every text token × background token pair, i.e. text/muted/accent/ok/warn/none on bg/surface/code-bg): worst light pair 5.75:1 (accent on code-bg), worst dark pair 6.98:1 (muted on code-bg, alpha ignored, i.e. opaque, which is the darker and thus conservative case). All pairs ≥ 4.5:1, so pass |
| **UI: Responsiveness at target viewports** | ☑ pass | Headless Chrome via a same-origin iframe of exact width (Chrome's minimum window is 500px): 375, 768, 1280 -> `scrollWidth == clientWidth` each (no overflow); tables scroll inside their container, `<pre>` scrolls inside itself |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured Mon Oct 19 03:16:02 AM UTC 2026 in the T115 worktree, before any implementation commit:
```
$ date -u; ls site/ tests/test_site_content.py
Mon Oct 19 03:16:02 AM UTC 2026
ls: cannot access 'site/': No such file or directory
ls: cannot access 'tests/test_site_content.py': No such file or directory
```

**AFTER**:
```
$ ls site/ tests/test_site_content.py
site/:
index.html  sample-score.json
tests/test_site_content.py
$ pytest tests/test_site_content.py -q
14 passed
```

**DELTA**: A newcomer can open one static page that explains easy-verifier, how to run it, its 14 dimensions, 32 areas with per-area status and a real sample scorecard, and a test fails if any engine fact on it drifts.

**WITNESS**: the Supervisor (not the implementer), 2026-10-19. Re-ran `tests/test_site_content.py` + `tests/test_t100_no_personal_identifiers.py` on 015ada2 -> `19 passed`, with the active-task state file set to T115 so the trace hook attributes it; served site/ and rendered it in headless Chrome (all six sections, data-overall="47"); measured contrast (worst 5.75:1 / 6.98:1).



---

## Notes for T116 / Supervisor

- Interpreter used (worktree has no `.venv`): `PYTHONPATH=src:<main-checkout>/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest ...`.
- **Snapshot regeneration** (T116 to document). Score, then reduce (script body below, saved as `reduce.py`):
  `python -m easy_verifier.adapters.cli score --repo . --scope project </dev/null > self.json`
  `python reduce.py self.json "$(git rev-parse --short HEAD)" "$(date -u +%F)" site/sample-score.json`
  ```python
  import json, sys
  d = json.load(open(sys.argv[1]))
  out = {"commit": sys.argv[2], "date": sys.argv[3], "scope": "project",
         "overall": d["overall"]["value"],
         "ratings": [({"dimension": r["dimension"], "value": r["value"]} if r.get("value") is not None
                      else {"dimension": r["dimension"], "reason_code": r["reason_code"]}) for r in d["ratings"]],
         "areas_measured": list(d["areas_measured"]), "areas_without_rule": list(d["areas_without_rule"])}
  json.dump(out, open(sys.argv[4], "w"), indent=2); open(sys.argv[4], "a").write("\n")
  ```
  The snapshot was taken at commit `8062b35`, overall 47, 22 of 32 areas measured.
- Placeholder decision (edge case): `#run` keeps README's `/home/you/code` verbatim; AC 8's host-path check exempts exactly that string and nothing else.
- Page sections are hand-written; the dimension/area/sample rows were generated once from the engine tables (generator not committed). The test, not the generator, is the guard.

## Stage 4 P3 fixes (per-scope weight claim, pinned dimension count)

Evidence: `pytest tests/test_site_content.py tests/test_t100_no_personal_identifiers.py -q` -> `19 passed in 0.86s`; `ruff check tests/test_site_content.py` -> `All checks passed!`. New tests: `test_dimension_count_pinned`, `test_scope_weight_claim_holds_in_engine` (each SCOPE_RULE_GROUPS group, or the whole table, sums to 100; solution-fit has no rules; engine confirmed: blast-radius [100, 100], all others 100).
