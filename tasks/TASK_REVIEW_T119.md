# TASK_REVIEW — T119: Landing page — "Easy Verifier" name, tab icon, visual scoring, pull-and-run first

> Sibling of `tasks/TASK_GUIDE_T119.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass | `tests/test_site_content.py` (14 new tests, AC 1-5, 7): `test_product_name_is_easy_verifier`, `test_favicon_link_and_file`, `test_favicon_with_external_reference_fails`, `test_quick_start_is_first_and_verbatim`, `test_quick_start_command_missing_from_docs_fails`, `test_quick_start_reordered_fails`, `test_other_ways_keep_stdio_cli_and_build`, `test_scoring_step_diagram`, `test_diagram_missing_step_fails`, `test_worked_example_matches_snapshot`, `test_worked_example_with_wrong_number_fails`. Written red first (8 failed, 19 passed before the page change), then green. |
| Verification command run | ☒ pass | `tests/test_site_content.py` 27 passed in 0.30s; `test_site_theme.py` 12 passed; `test_site_deploy_config.py` 7 passed; `test_t100_no_personal_identifiers.py` 3 passed; `test_t118_pull_and_run.py` 29 passed. `ruff check` + `ruff format --check` on the test file: All checks passed. |
| Negative cases hold | ☒ pass | Favicon with external href / `<image href>` / `<script>` / over 2 KB fails; Quick-start line removed from docs fails ("not verbatim"); steps reordered fails; diagram step renamed fails (names "Coverage check"); example overall or rating +1 vs snapshot fails. |
| verify | ☒ pass | Page served locally (python http.server) and rendered in headless Chrome at 375/768/1280: name, Quick start first, diagram, example all observed - pass. Document scrollWidth == clientWidth at all three widths (360/768/1280, 15 px scrollbar). |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Touched only `site/index.html`, `site/favicon.svg`, `tests/test_site_content.py`, this file. Re-ran all five site/T118 suites. Full engine suite not run (no engine code touched). |
| Full smoke suite still green (no regression) | ☒ pass | The five suites above are the affected set; all green. |
| **UI: Visual regression (diff or verdict pasted)** | ☒ pass | `<scratchpad>/t119/before-1280.png` vs `after-1280.png`, `scoring-1280.png`, `scoring-768.png`, `scoring-375.png`, `example-375.png`. Viewed all three: header/sidebar read "Easy Verifier"; `#run` opens with 1 Pull / 2 Run / 3 Register then a collapsed "Other ways to run it"; `#scoring` shows a vertical step diagram (Repository, Evidence, Rules, Coverage check, yes to Rating 0-100 or no to Abstention, Overall, Improvement plan) then the worked example (architecture 100, test-strategy 75, security 50, supply-chain abstained, overall 47 of 10 rated). Legible at all widths. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ pass | `test_site_theme.py` unchanged, 12 passed (no raw colour outside `:root`; six nav links). New CSS uses only `var(--...)`; SVG styled by classes. Only raw colours are in `site/favicon.svg` (#0a0a12, #1e1e42, #00d4ff). Contrast (WCAG, computed): title text #e2e2f0 on --surface2 13.78:1; sub text --muted on --surface2 4.74:1; "yes" green on --bg 14.70:1; "no" amber on --bg 11.37:1; arrows --muted on --bg 5.29:1. All >= 4.5:1. |
| **UI: Responsiveness at target viewports** | ☒ pass | 375 (iframe, true mobile width), 768, 1280. No page-level horizontal scroll (scrollWidth == clientWidth). 375: Quick-start blocks wrap inside `<pre>`, diagram scales to width, worked-example table uses `table.compact` (no inner scroll). 1280: diagram centred, max 26rem. Existing dimension/area tables still scroll inside their own wrapper at 375 (unchanged). |

### Changed existing assertions

- `test_run_commands_verbatim_from_docs`: removed `assert "temvar/" not in block.text`, `"hub.docker"`-style temvar ban on the page and the final `assert "temvar/" not in PAGE`. Why: T118 supersedes the old no-Docker-Hub rule; the Quick start must show `temvar/easy-verifier-mcp:0.1.0`. Kept the line-by-line "every command line is in the docs" check and the `hub.docker` ban. The stronger contiguous-block check lives in the new `check_quick_start`.
- No other existing assertion changed. Theme, deploy-config, t100 and t118 tests are unmodified.

### Page text changes outside the guide's list

- Two prose uses ("easy-verifier gathers evidence", "easy-verifier scoring itself") became "Easy Verifier" for consistency. Commands and identifiers keep `easy-verifier`.

---

---|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-19 08:42:41 UTC, before any implementation commit; commands run in the T119 worktree root; screenshot `<scratchpad>/t119/before-1280.png`, headless Chrome 1280px, 152258 bytes):

```
$ date -u
Mon Oct 19 08:42:41 AM UTC 2026
$ grep -n '<title>\|<h1\|class="brand"\|rel="icon"' site/index.html
6:<title>easy-verifier: an offline, rule-based repository verifier</title>
180:  <a class="brand" href="#top">easy-verifier</a>
201:  <h1>easy-verifier</h1>
$ ls site/
index.html
sample-score.json
$ sed -n '/<section id="run">/,/<\/section>/p' site/index.html | grep -c '<pre'
3
$ sed -n '/<section id="scoring">/,/<\/section>/p' site/index.html | grep -c '<svg'
0
```

No `rel="icon"` line, no favicon file, `#run` opens with build-from-source (compose) blocks, `#scoring` has zero diagrams.

**AFTER** (2026-10-19, same commands post-change):

```
<title>Easy Verifier: an offline, rule-based repository verifier</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<a class="brand" href="#top">Easy Verifier</a>
<h1>Easy Verifier</h1>
site/: favicon.svg index.html sample-score.json
#run: first <pre> is data-step="1-pull" (docker pull temvar/easy-verifier-mcp:0.1.0); build/stdio/CLI under <details> "Other ways to run it"
#scoring: 1 <svg class="flow"> step diagram + worked example table
```

Screenshots: `<scratchpad>/t119/after-1280.png`, `scoring-1280.png`, `scoring-768.png`, `scoring-375.png`.

**DELTA**: A newcomer sees "Easy Verifier", a tab icon, a three-step pull/run/register quick start, and a diagram plus real numbers showing how a rating or an abstention comes out.

**WITNESS**: Supervisor, 2026-10-19 — `memory/event-trace/T119.jsonl` holds 40 attributed records from the frontend-developer session. Supervisor independently re-ran site_content + site_theme + site_deploy_config + t100 + t118 on 564bea2: `78 passed in 2.22s`, and viewed after-1280, scoring-1280, scoring-375 (pre-fix: example table scrolled) and example-375 (post `table.compact`: no scroll).

## Stage 4 review (Supervisor)

- Scope: site/index.html, site/favicon.svg, tests/test_site_content.py. `src/`, docs, snapshot untouched.
- Name: title/h1/brand "Easy Verifier"; commands keep `easy-verifier`.
- Favicon: 351-byte SVG, viewBox, no external refs/scripts, kit colors; served (`.vercelignore` admits site/**, deploy test green).
- `#run`: Quick start 1 Pull / 2 Run / 3 Register, each block verbatim from docs (new contiguous check), "Other ways" in `<details>`.
- `#scoring`: vertical SVG diagram (role=img, title, desc), theme-token classes, branch yes→Rating / no→Abstention, contrast ≥ 4.74:1; worked example numbers pinned to the snapshot; original scoring phrases kept.
- Changed existing assertion accepted: `temvar/` bans removed from `test_run_commands_verbatim_from_docs` (superseded by T118, user decision); `hub.docker` ban and per-line docs check kept.
- Findings: P0 0, P1 0, P2 0. P3: none blocking.
- Security review: N/A (Risk Low); inline-only, no external resources (pinned).
