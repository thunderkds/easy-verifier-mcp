# TASK_GUIDE — T119: Landing page — "Easy Verifier" name, tab icon, visual scoring, pull-and-run first
**Date**: 2026-10-19
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: frontend-developer
**Agent guide**: `.claude/agents/frontend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC_SITE.md` and `memory/MEMORY.md`
2. Read this file completely
3. Read `.claude/agents/frontend.md`
4. Read `tasks/TASK_GUIDE_T118.md` (the pull-and-run commands this page must copy verbatim come from T118's docs)
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-19:
- *"in the how scoring works, let make it more visualize to easy adapt"*
- *"easy-verifier > Easy Verifier"*
- *"add icon for the tab"*
- *"for the guide to install, it looks complicated, let focus on the simple way is pull the docker images and run first, the others comes later"* (image path: T118, `temvar/easy-verifier-mcp:0.1.0` built from current code)

**Restated intent**:
> On `site/index.html`: show the product name as "Easy Verifier" (title, header, sidebar brand); give the tab a favicon; turn `#scoring` into a visual explanation a newcomer grasps at a glance (a step diagram from repository to rating/abstention to overall and plan, plus a small worked example drawn from the real sample snapshot); and restructure `#run` so the first thing shown is pull → run → register (three short blocks), with build-from-source, stdio and CLI moved below under "Other ways". Theme (T117) and all drift guarantees stay.

**Out of scope** (this task does NOT do):
- Changing the engine, the docs' commands (T118 owns them), `site/sample-score.json`
- New external resources (no CDN, no web fonts, no `<script src>`)
- Renaming the package/CLI/MCP server (`easy-verifier` stays in commands and code — only the display name changes)

**Requirement Refs**: `PROJECT_SPEC_SITE.md` §Purpose 2 (run) and 4 (scoring), §Drift constraint (commands verbatim in README/DOCKER_MCP_GUIDE/LOCAL_MCP_GUIDE), §Non-goals (no external hosts). Update §Non-goals' "no Docker Hub/temvar refs" line: superseded by T118 (Supervisor does this on merge).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-10-19)
- [x] Domain terms align with `PROJECT_SPEC_SITE.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] Requirement Refs exist and are covered

---

## Dependencies & Reachability

**Depends on**: T118 — the pull/run/register commands must exist verbatim in `docs/DOCKER_MCP_GUIDE.md` / `README.md` on develop

**Entry point**: `site/index.html`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `<title>` starts with `Easy Verifier`; the header `h1` and sidebar `.brand` read `Easy Verifier`. Commands and code identifiers keep `easy-verifier` | "easy-verifier > Easy Verifier" |
| 2 | `<link rel="icon" href="favicon.svg" type="image/svg+xml">` and `site/favicon.svg` exists: a small, valid SVG (≤ 2 KB, `viewBox`, no external refs, no `<script>`) in the kit palette (e.g. a cyan check mark / shield on `#0a0a12`); it renders at 16 and 32 px | "add icon for the tab" |
| 3 | `#run` begins with a "Quick start" of exactly three numbered steps — **1 Pull**, **2 Run**, **3 Register** — each one `<pre>` block copied verbatim from T118's docs (`docker pull temvar/easy-verifier-mcp:0.1.0`; the `mkdir`/`chown` prep may sit with Run; the `docker run -d ...`; `claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp`), followed by one sentence on how to call it. Build-from-source (compose), stdio and CLI follow under an "Other ways" heading (a `<details>` is fine). Existing test `#run` commands verbatim in docs keeps passing | "pull ... and run first, the others come later" |
| 4 | `#scoring` has an inline SVG (or pure HTML/CSS) step diagram, styled with the theme tokens, showing in order: **Repository → Evidence** (measured metrics, citations) **→ Rules** (weights per scope add up to 100) **→ Coverage check** (enough evidence? yes → **Rating 0–100**; no → **Abstention** with a reason code) **→ Overall** (mean of rated dimensions) **→ Improvement plan** (ordered by declared gain). It has an accessible text equivalent (`<title>`/`aria-label` or a visible ordered list) | "more visual, easy to adapt" |
| 5 | `#scoring` shows a worked example from `site/sample-score.json`: two or three rated dimensions with their values, one abstained dimension with its reason code, and the overall — numbers equal to the snapshot (extend the existing snapshot-match test to cover them) | concrete example |
| 6 | The scoring phrases the existing tests require (rules over measured metrics, coverage floor → abstention, improvement plan by declared gain, no model call / no network, the weights-add-up-to-100 claim) remain present | no drift |
| 7 | All existing site tests pass unchanged except where this guide requires an extension (list each changed assertion and why); new tests cover AC 1–5 incl. a negative (e.g. a Quick-start command not present in docs fails; favicon with an external `href` fails) | Gate 5 |
| 8 | Phone (375px): Quick start blocks wrap inside `<pre>`, the diagram scales to width (no page-level horizontal scroll) | responsive |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | develop with T118 merged + this change | site/theme/deploy/t100 + new tests pass | automated |
| 2 | Page at 375/768/1280 | Quick start is the first thing in `#run`; diagram legible; favicon in the tab | headless Chrome screenshots + vision verdict |
| 3 | A newcomer reads `#scoring` | can say in one sentence how a number (or an abstention) comes out | Supervisor read-through |

### Verification Command

```bash
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_site_content.py tests/test_site_theme.py tests/test_site_deploy_config.py tests/test_t100_no_personal_identifiers.py -q
```

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|-------------------|---------------------|-----------------|
| Header + `#run` + `#scoring` | screenshot before/after at 1280 + vision verdict | name "Easy Verifier"; Quick start first; diagram present and readable |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|-----------|---------------------|-----------------|
| Theme tokens | `tests/test_site_theme.py` (unchanged) + audit of new CSS/SVG | colors only via `var(--…)` (SVG uses CSS classes, like the kit's `svg.pipeline`); no raw colors outside `:root` except inside `favicon.svg` |
| Contrast | computed | diagram text ≥ 4.5:1 on its fill |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|----------|---------------------|-----------------|
| Mobile (375px) | screenshot | blocks wrap, diagram fits width |
| Tablet (768px) | screenshot | as desktop, narrower |
| Desktop (1280px) | screenshot | diagram centred, ≤ content width |

---

## Approach

**Pattern reference**: the kit's `svg.pipeline` diagram (`~/workspace/pets/personal-agentic-claude/site/index.html`, CSS ~lines 150–156 and its SVG markup) for a vertical step diagram with arrows, styled by classes. `tests/test_site_content.py` for how commands and snapshot numbers are pinned.

1. Tests first (red): title/brand, favicon, Quick-start order + verbatim, worked-example numbers.
2. `site/favicon.svg` + `<link rel="icon">`.
3. Restructure `#run`; build the `#scoring` diagram + worked example; keep the required phrases.
4. Screenshots, contrast.

---

## Edge Case Checklist

- [ ] The diagram's branch (rating vs abstention) must stay readable at 375px — a vertical layout is safer than horizontal
- [ ] `.vercelignore` admits `site/**`, so `favicon.svg` deploys (deploy-config test's admitted-set check still passes)
- [ ] Worked-example numbers read from the snapshot in the test, not hard-coded twice
- [ ] Scroll-spy/nav still lists exactly six sections (theme test)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `site/index.html` | name, icon link, `#run` restructure, `#scoring` diagram + example |
| `site/favicon.svg` | new |
| `tests/test_site_content.py` | extensions + new tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `site/sample-score.json`, `src/**`, `docs/**`, `README.md` | out of scope (docs are T118) |
| `PROJECT_KANBAN*.md`, `PROJECT_SPEC_SITE.md`, `memory/**` | Supervisor-only |

---

## Test Plan

New/extended tests in `tests/test_site_content.py` (AC 1–7); theme/deploy/t100 unchanged; screenshots at 375/768/1280.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Risk Low)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T119.md` Evidence (Hard-Stop Gate 5)
- [ ] All three UI Evidence rows filled (Hard-Stop Gate 6)
- [ ] `Skill({ skill: "verify" })` run — page served locally and checked
- [ ] Supervisor notified: task ready for Stage 4 review
