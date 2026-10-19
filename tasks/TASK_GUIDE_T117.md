# TASK_GUIDE — T117: Restyle the landing page in the kit's theme
**Date**: 2026-10-19
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: frontend-developer
**Agent guide**: `.claude/agents/frontend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC_SITE.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/frontend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-19: *"keep the theme like personal agentic claude"* — the landing page (`site/index.html`, T115) should look like the kit's landing page (`https://personal-agentic-claude.vercel.app/`, source `~/workspace/pets/personal-agentic-claude/site/index.html`).

**Restated intent**:
> Re-skin `site/index.html` in the kit's visual theme — its dark neon palette, sticky left sidebar navigation (collapsible on mobile), header card, cyan uppercase section headings, pill tags, and green install `<pre>` blocks — without changing any page content, section id, `data-*` marker, or the sample snapshot, so every T115 drift test still passes unchanged.

**Out of scope** (this task does NOT do):
- Any change to the page's words, commands, tables' rows, sample scorecard values, `site/sample-score.json`
- `vercel.json`, `.vercelignore`, `docs/**`, `src/**`
- Copying the kit's text, brand name, SVG pipeline diagram, or sections that have no counterpart here
- A light-mode variant (the kit is dark-only; follow it)

**Requirement Refs**: `PROJECT_SPEC_SITE.md` §Purpose, §Safety constraints, §Non-goals (no build, no external hosts). T115 ACs 1–9 remain binding.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-10-19)
- [x] Domain terms align with `PROJECT_SPEC_SITE.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] Requirement Refs exist and are covered

---

## Dependencies & Reachability

**Depends on**: T115 — `site/index.html` exists on develop

**Entry point**: `site/index.html`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `:root` defines the kit's tokens by name and value: `--bg #0a0a12`, `--surface #111128`, `--surface2 #16162e`, `--border #1e1e42`, `--text #e2e2f0`, `--cyan #00d4ff`, `--green #00ff88`, `--amber #ffb800`, `--purple #a855f7` (+ the `-dim` rgba variants used). `--muted` keeps the kit's hue but may be lightened **only as far as needed** to reach ≥ 4.5:1 on `--bg` and `--surface` (the kit's `#6b6b9a` measures ≈ 3.9:1 on `#0a0a12` — record the chosen value and measured ratios) | dark neon palette |
| 2 | No `prefers-color-scheme` block remains (dark-only, like the kit); every color in rules is a `var(--…)` reference (raw hex/rgba only inside `:root`) | dark-only theme |
| 3 | Layout = the kit's shell: `.layout` grid with a sticky `.sidebar` (`aside`) holding a brand link + a `nav` listing all six sections (`#what`, `#run`, `#dimensions`, `#areas`, `#scoring`, `#sample`) and the GitHub repo link; below 768px the sidebar stacks on top and collapses behind a `.nav-toggle` button. The nav is open in the markup; an **inline** script (no `src=`) collapses it and marks the active link, like the kit's | sticky sidebar navigation |
| 4 | Header is the kit's `.header` card (surface, 2px cyan top border, glow shadow); `h2` cyan uppercase with bottom border; `code` cyan on `--cyan-dim`; command `<pre>` blocks green on `--surface2` with `white-space: pre-wrap; overflow-wrap: anywhere`; area status tags use the kit's pill tags — ruled → green, `pack:*` → amber, none → purple (or amber/purple per contrast) | header card, headings, tags, install blocks |
| 5 | Skip link + `:focus-visible` cyan outline as in the kit; `prefers-reduced-motion` respected | kit's accessibility details |
| 6 | All existing tests pass unchanged: `tests/test_site_content.py` (16), `tests/test_site_deploy_config.py` (7), `tests/test_t100_no_personal_identifiers.py`. Section ids, `data-*` attributes, text and commands are byte-identical in meaning (the tests are the proof) | no content change |
| 7 | New test(s) in `tests/test_site_content.py` (or a new `tests/test_site_theme.py`) pin AC 1–3: the kit token values present in `:root`; no `prefers-color-scheme`; no raw colors outside `:root`; the sidebar nav links exactly the six section ids; `<script>` tags carry no `src`. Negative: a monkeypatched/edited copy with a missing nav link or a hex color outside `:root` fails | tests (Gate 5) |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | develop tree + this change | site + theme + deploy + t100 tests pass | automated |
| 2 | Page at 375 / 768 / 1280 px | 1280/768: sidebar left, content right; 375: sidebar stacked + toggle, no page-level horizontal scroll, tables scroll inside `.table-wrap` | headless Chrome screenshots + vision verdict |
| 3 | Side-by-side with the kit's page at 1280 px | same palette, sidebar, header card and heading style — recognisably the same theme | screenshot comparison verdict |

### Verification Command

```bash
cd "$(git rev-parse --show-toplevel)"   # repo root
.venv/bin/python -m pytest tests/test_site_content.py tests/test_site_deploy_config.py tests/test_t100_no_personal_identifiers.py -q
.venv/bin/ruff check tests/
```

(In a worktree with no `.venv`, use the main checkout's interpreter: `<main-checkout>/.venv/bin/python`.)

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|-------------------|---------------------|-----------------|
| Full page vs the kit's page | headless Chrome screenshot of both at 1280px + vision verdict | "same theme": palette, sidebar, header card, h2 style match |
| Full page vs T115 baseline | screenshot before/after | all six sections and their content still present |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|-----------|---------------------|-----------------|
| Kit tokens | test (AC 7) + CSS audit | values as AC 1; colors only via `var(--…)` |
| Contrast | computed ratios | `--text` and `--muted` ≥ 4.5:1 on `--bg`/`--surface`/`--surface2`; tag colors ≥ 4.5:1 on their dim background over `--bg` |
| Typography | computed style | kit's system font stack, monospace code, body ≥ 16px |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|----------|---------------------|-----------------|
| Mobile (375px) | screenshot | sidebar stacked, toggle visible, no page-level horizontal scroll |
| Tablet (768px) | screenshot | sidebar layout, tables scroll in container |
| Desktop (1280px) | screenshot | sidebar layout, readable measure |

---

## Approach

**Pattern reference**: `~/workspace/pets/personal-agentic-claude/site/index.html` — the `<style>` block (lines ~9–180), the `.layout`/`aside.sidebar`/`.header` markup (~184–230), and the inline `<script>` at the end (~700–750). Imitate the CSS and shell; adapt nav groups to this page's six sections; do not copy the kit's text.

1. Write the theme test(s) first (red).
2. Replace the `<style>` block and wrap existing `<header>`/sections in the kit's shell. Move existing content, do not rewrite it.
3. Add the inline script (mobile collapse + active link via `IntersectionObserver` or scroll position, as the kit does).
4. Run all site tests; take screenshots; measure contrast.

---

## Edge Case Checklist

- [ ] The existing `<nav aria-label="Sections">` inside the header: replace it with the sidebar nav, don't leave two navs
- [ ] JS-less render: nav fully visible (collapse is applied by script only)
- [ ] Sticky first column of tables uses `--bg`, consistent with the kit
- [ ] The 32-areas table Status column at 375px (T115 observation) — the kit's sticky first column helps; keep the Status column reachable
- [ ] Score figure `.score` / `data-overall` styling still legible in the dark theme

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `site/index.html` | restyle + sidebar shell + inline script |
| `tests/test_site_content.py` or `tests/test_site_theme.py` | theme tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `site/sample-score.json` | content snapshot, unchanged |
| `src/**`, `docs/**`, `vercel.json`, `.vercelignore` | out of scope |
| `PROJECT_KANBAN*.md`, `memory/**` | Supervisor-only |

---

## Test Plan

Theme tests (AC 7) + the existing site/deploy/t100 tests (AC 6); screenshots at 375/768/1280 plus one of the kit at 1280 for the UI rows; contrast computed with a short script, ratios pasted.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Risk Low)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T117.md` Evidence (Hard-Stop Gate 5)
- [ ] All three UI Evidence rows filled (Hard-Stop Gate 6)
- [ ] `Skill({ skill: "verify" })` run — page served locally and checked
- [ ] Supervisor notified: task ready for Stage 4 review
