# TASK_REVIEW — T117: Restyle the landing page in the kit's theme

> Sibling of `tasks/TASK_GUIDE_T117.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_site_theme.py` (12 tests: kit tokens in `:root`, dark-only, colours only via `var()`, sidebar nav = exactly the six section ids + `.nav-toggle` + GitHub link + single `<nav>`, inline-only scripts, nav open in markup, skip-link/focus-visible/reduced-motion; negatives: missing nav link, raw hex, raw rgba, `prefers-color-scheme` block, `<script src>` each make the check fail). Written first: 6 failed / 6 passed on the T115 page (red), then green after the restyle. |
| Verification command run | ☑ pass | `PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_site_theme.py tests/test_site_content.py tests/test_site_deploy_config.py tests/test_t100_no_personal_identifiers.py -q` -> `38 passed in 2.05s` (12 theme + 16 site-content + 7 deploy-config + 3 t100, all existing tests unchanged). `ruff check tests/` -> `All checks passed!`; `ruff format --check tests/test_site_theme.py` -> already formatted. |
| Negative cases hold | ☑ pass | the five negative theme tests pass (they assert the checks raise on an edited copy) |
| verify | ☑ pass | page loaded in headless Chrome from file://; DOM probe: aria-expanded=false after load (script collapsed the nav), body font 16px, page scrollWidth <= viewport at 500/768/1280 (485/500, 753/768, 1265/1280, no page-level horizontal scroll), `.table-wrap` scrolls inside its container at 768 (448/439) - pass. Supervisor re-verify at Stage 5. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Changed: `site/index.html`, new `tests/test_site_theme.py`, this file. Run: the four site-related test files. Skipped: engine suite (no `src/` touched). |
| Full smoke suite still green (no regression) | ☐ N/A | engine untouched; site + deploy + t100 suites pass (above). Full suite left to Stage 5. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | Screenshots (headless Chrome): `<scratchpad>/t117/after-1280-top.png` (this page) vs `<scratchpad>/t117/kit-1280.png` (kit); baseline `<scratchpad>/before-1280.png`; also `after-1280.png`, `after-768.png`, `after-375.png`. Verdict: same theme - near-black navy bg, sticky left sidebar with cyan-highlighted active link and left rule, header card with 2px cyan top border and glow, cyan uppercase h2 with rule, cyan code chips, green `<pre>` blocks on surface2. All six sections and their content present (content tests pass). Only differences: no pipeline diagram / nav groups (out of scope), muted text slightly lighter (contrast). |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | Tokens pinned by test (AC1) and CSS audit: raw colours only inside `:root` (test). Contrast (script, WCAG): text #e2e2f0 15.37 bg / 14.43 surface / 13.78 surface2. Kit `--muted` #6b6b9a = 3.94 / 3.70 / 3.53 (fails). Chosen `--muted: #8080b0` (same hue, minimal lift to clear surface2) = 5.29 bg / 4.96 surface / 4.74 surface2. Tags on their 12% dim over bg: green 11.84, amber 9.39, purple #a855f7 4.49 (just under 4.5) so `.tag-none` uses added token `--purple-text: #ae5ff8` = 4.89; cyan code 9.27. System font stack, monospace code, body 16px (probe). |
| **UI: Responsiveness at target viewports** | ☑ pass | 375: sidebar stacked on top, Menu toggle visible, nav collapsed, no page-level horizontal scroll, tables scroll inside `.table-wrap`, Status column reachable by in-container scroll. 768 and 1280: sidebar left, content right, tables scroll inside container only when wider than it. Note: headless Chrome clamps window width to 500 in DOM-probe mode, so numeric 375 overflow was probed at 500; the 375px screenshot shows no overflow. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-19 before any implementation commit (`date -u` below; screenshot of the T115 page at 1280px: `<scratchpad>/before-1280.png`, headless Chrome).

```
Mon Oct 19 07:46:51 AM UTC 2026
$ sed -n '/:root {/,/}/p' site/index.html | head -20
  :root {
    --bg: #ffffff; --surface: #f4f5f8; --border: #c9ccd6;
    --text: #1a1c24; --muted: #4a4f60; --accent: #0b5cad;
    --ok: #12632f; --warn: #7a4a00; --none: #8a1f1f;
    --code-bg: #eceef4; --measure: 72ch;
  }
    :root {
      --bg: #0f1117; --surface: #181b25; --border: #343949;
      --text: #e6e8ef; --muted: #a8aec0; --accent: #6db3ff;
      --ok: #62d68c; --warn: #f0b45c; --none: #ff8f8f;
      --code-bg: #20243180;
    }
$ grep -c 'prefers-color-scheme' site/index.html
1
```

**AFTER**: same checks, post-change: `grep -c 'prefers-color-scheme' site/index.html` -> `0`; `:root` now carries `--bg: #0a0a12; --surface: #111128; --surface2: #16162e; --border: #1e1e42; --text: #e2e2f0; --muted: #8080b0; --cyan: #00d4ff; --green: #00ff88; --amber: #ffb800; --purple: #a855f7` (+ `-dim` variants); screenshot `<scratchpad>/t117/after-1280-top.png`; 38 passed.

**DELTA**: the landing page now renders in the kit's dark neon theme with a sticky (mobile-collapsible) sidebar instead of the T115 light/dark system-theme page, with identical content.

**WITNESS**: Supervisor, 2026-10-19 — `memory/event-trace/T117.jsonl` holds 29 attributed records from the frontend-developer session; the Supervisor independently re-ran the site/theme/deploy/t100 tests on a5a245d (`38 passed in 1.78s`) and inspected the 375/768/1280 and kit-1280 screenshots.

## Stage 4 review (Supervisor)

- Scope: `site/index.html`, `tests/test_site_theme.py`, this file. `src/`, `site/sample-score.json`, deploy config untouched (diff stat: 3 files).
- Reachability: entry point `site/index.html` present.
- Correctness: inline script null-guards nav/toggle, falls back cleanly without IntersectionObserver; `#top` (body) and `#main` targets exist; nav open in markup, collapse only with `.js`. Content markers unchanged — the 16 T115 drift tests pass unmodified.
- Tests: 12 new theme tests (tokens, dark-only, colors only via var(), six-section nav, inline-only scripts, JS-less nav, a11y) with 5 negatives; red-first noted by the agent.
- Visual: 1280 matches the kit (palette, sidebar with cyan active link, header card, uppercase cyan h2, green command blocks); 768 sidebar layout; 375 stacked with Menu toggle, no page-level overflow. Supervisor viewed 768 and 375 (the agent had not).
- Deviations accepted: `--muted #8080b0` (kit #6b6b9a fails AA at 3.94); `--purple-text #ae5ff8` for `.tag-none` (kit purple 4.49 on its dim bg).
- Findings: P0 0, P1 0, P2 0. P3: the kit's sidebar has a sub-brand line and group titles for every group; here only "Source" has one — cosmetic, left as is.
- Security review: N/A (Risk Low); inline scripts only, no external resources (pinned by test).
