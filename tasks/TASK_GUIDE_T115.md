# TASK_GUIDE — T115: Static landing page + self-score snapshot + drift test
**Date**: 2026-10-19
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: frontend-developer
**Agent guide**: `.claude/agents/frontend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC_SITE.md` (this task's spec — the site scope) and skim `PROJECT_SPEC.md` for engine vocabulary
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/frontend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. C2: read `memory/codebase-map.md` for directory layout

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-19: *"wanna deploy the verifier as the landing page like https://personal-agentic-claude.vercel.app/ for https://github.com/thunderkds/personal-agentic-claude"*. Content chosen by the user: **what it is + install**, **dimensions + 32 areas**, **sample score report**, **how scoring works**. Location: `site/` in this repo.

**Restated intent**:
> A single static page at `site/index.html` that tells a newcomer what easy-verifier is, how to run it, what it measures (13 dimensions + `change-risk`, 32 evaluation areas with per-area status), how a score is computed, and shows one real sample scorecard — every engine fact on it pinned to its source of truth by a test, so the page cannot silently drift.

**Out of scope** (this task does NOT do):
- Vercel config, `.vercelignore`, runbook, any deploy (T116 / operator)
- Any change under `src/` (the engine) — if a fact is wrong in the engine, STOP and report
- Pull-and-run Docker Hub instructions (T025 cancelled; build-from-clone only)
- A site navigation restructure, JS interactivity, dark/light toggle, analytics

**Requirement Refs**: `PROJECT_SPEC_SITE.md` §Purpose 1–5, §Drift constraint, §Safety constraints. (Site scope has no PRD FR IDs; the engine FRs the page *describes* — NFR-001, FR-013, FR-040, FR-073 — must be described accurately, not changed.)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, against the user's 2026-10-19 answers)
- [x] Domain terms align with `PROJECT_SPEC_SITE.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] Requirement Refs exist (`PROJECT_SPEC_SITE.md` sections) and are covered by the ACs

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `site/index.html`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `site/index.html` exists, is valid standalone HTML (doctype, `<title>`, charset, viewport meta), loads **no** external resource (no `src=`/`href=` to another host except `github.com/thunderkds/easy-verifier-mcp` and citation links, no `<script src>`, no web fonts) | Stack decision, Non-goals |
| 2 | Page has sections with stable ids: `what`, `run`, `dimensions`, `areas`, `scoring`, `sample` | Purpose 1–5 |
| 3 | Every key of `easy_verifier.dimensions.DIMENSIONS` appears in the `#dimensions` section, and no dimension name appears there that is not a key | Drift: dimension list |
| 4 | All 32 entries of `judge.AREAS` appear in `#areas` in `AREAS` order, text verbatim; each carries a status marker (`data-status="ruled"`, `"pack:<name>"` or `"none"`) that equals the status computed from `RATING_RULES`/`DOCUMENTATION_RULES`/`PACK_FLOORS` (today: 27 ruled, finance 1, healthcare 2, frontend-a11y 1, none 1 — "Transactions, concurrency, idempotency") | Drift: areas + per-area status |
| 5 | Every shell command shown in `#run` (each `<code>`/`<pre>` block there) appears verbatim in `README.md`, `docs/DOCKER_MCP_GUIDE.md` or `docs/LOCAL_MCP_GUIDE.md`; none references `temvar/` or Docker Hub | Drift: commands; Non-goals |
| 6 | `site/sample-score.json` exists: easy-verifier scored at `project` scope, reduced to `{commit, date, scope, overall, ratings:[{dimension, value \| reason_code}], areas_measured, areas_without_rule}`; the overall, every per-dimension value and every abstention reason shown in `#sample` equal the snapshot; the commit short-hash and date are shown | Purpose 5, Drift: scorecard |
| 7 | `#scoring` states: rules over measured metrics, coverage floor → abstention, improvement plan by declared gain, no model call / no network in the engine | Purpose 4 |
| 8 | Negative: no file under `site/` contains `/home/`, `/Users/`, `/workspace`, an email address, or a string matching the engine's own secret patterns | Safety constraints |
| 9 | Negative (the drift test bites): monkeypatching `AREAS` with an extra area, or `DIMENSIONS` with an extra key, makes the test fail | Drift constraint |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | Current `develop` tree | `tests/test_site_content.py` passes | automated |
| 2 | Extra fake area / dimension injected | test fails naming the missing item | automated (AC 9) |
| 3 | Page opened in a browser at 375 / 768 / 1280 px | readable, no horizontal scroll, tables scroll inside their container | Playwright screenshots or LLM-vision verdict |

### Verification Command

```bash
cd /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp
PYTHONPATH=src .venv/bin/python -m pytest tests/test_site_content.py -q
PYTHONPATH=src .venv/bin/python -m pytest -q -x   # full suite, no regression
```

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|-------------------|---------------------|-----------------|
| Full page (new — no baseline) | Playwright full-page screenshot + LLM-vision verdict | "matches spec": all six sections present, scorecard legible, areas table shows status markers distinctly |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|-----------|---------------------|-----------------|
| Colors as CSS custom properties on `:root`, with a `prefers-color-scheme: dark` variant | CSS audit (grep `:root`, `@media (prefers-color-scheme: dark)`) | all colors referenced via `var(--…)`; text/background contrast ≥ 4.5:1 |
| Typography | computed style | system font stack, monospace for code, body ≥ 16px |
| Spacing / layout | visual | content max-width ~ 72ch prose / wider tables; 16px side gutter on mobile |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|----------|---------------------|-----------------|
| Mobile (375px) | Playwright screenshot | single column, long commands wrap or scroll inside `<pre>` (kit T086 lesson), no page-level horizontal scroll |
| Tablet (768px) | Playwright screenshot | single column, tables fit or scroll in container |
| Desktop (1280px) | Playwright screenshot | readable line length, tables full width |

---

## Approach

**Pattern reference**: `~/workspace/pets/personal-agentic-claude/site/index.html` (structure, no-build HTML/CSS) and `~/workspace/pets/personal-agentic-claude/tests/test_site_content.py` (how page content is parsed and asserted against sources of truth). Imitate; do not copy the kit's branding or text.

1. Write `tests/test_site_content.py` first (red): parse `site/index.html` with the stdlib `html.parser` (no new dependency), import `DIMENSIONS`, `AREAS`, `RATING_RULES`, `DOCUMENTATION_RULES`, `PACK_FLOORS`, `areas_without_rule` and derive expected per-area status the same way `judge.areas_without_rule` does (an area is `pack:<name>` when its only rules live in an optional pack in `PACK_FLOORS`).
2. Generate the snapshot: `PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo . --scope project </dev/null > <scratch>/self.json`, then reduce to the AC 6 shape with a short script; add `commit` (`git rev-parse --short HEAD`) and `date`. Commit only the reduced `site/sample-score.json`. Put the reduction script's exact command in the TASK_REVIEW so T116 can document it.
3. Write the page (green). Keep the copy plain and accurate; use README's dimension descriptions as the factual basis.
4. Add the AC 8/9 negative tests.

---

## Edge Case Checklist

- [ ] Area names contain `&` and `,` — compare after HTML-unescaping, not raw source
- [ ] An area ruled in both a core dimension and a pack counts as `ruled`, not pack-gated
- [ ] `change-risk` only rates at `changes`/`worktree` scope — the page must say so; it will be absent from the project-scope sample
- [ ] The self-score run's overall may withhold (abstention) — the scorecard must render an abstained overall correctly
- [ ] Snapshot must not carry `computed_from` paths, excerpts, or warnings text (keeps host paths out, keeps it small)
- [ ] Commands in README contain placeholders like `/home/you/code` — those are allowed in `#run` (they are verbatim from README) but AC 8's host-path check must then exempt exactly that placeholder, or the page should use a placeholder that doesn't trip it; decide and document in TASK_REVIEW

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `site/index.html` | new — the page |
| `site/sample-score.json` | new — reduced self-score snapshot |
| `tests/test_site_content.py` | new — drift + safety tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/**` | engine scope; the page describes it, never changes it |
| `vercel.json`, `.vercelignore`, `docs/RELEASE_GUIDE.md` | T116 |
| `PROJECT_KANBAN*.md`, `memory/**` | Supervisor-only |

---

## Test Plan

`tests/test_site_content.py` (AC 1–9), full suite for regression, Playwright screenshots at 375/768/1280 for the three UI Evidence rows, `/verify` by opening the page locally (`python -m http.server -d site`).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Risk Low) — AC 8 covers the publication-safety check
- [ ] Lint passes (`ruff check tests/test_site_content.py`)
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T115.md` Evidence (Hard-Stop Gate 5)
- [ ] All three UI Evidence rows filled (Hard-Stop Gate 6)
- [ ] `Skill({ skill: "verify" })` run — page served locally and checked
- [ ] Supervisor notified: task ready for Stage 4 review
