# PROJECT_SPEC — easy-verifier Landing Site (v1)

**Scope boundary:** this document governs the public static site only. It is a separate scope from
the verifier engine (Hard-Stop Gate 4: different deployment target — Vercel). Engine work stays on
`PROJECT_KANBAN.md` / `PROJECT_SPEC.md`; site work stays on `PROJECT_KANBAN_SITE.md` / this file.

Registered 2026-10-19 from the user's request: *"wanna deploy the verifier as the landing page like
https://personal-agentic-claude.vercel.app/ for https://github.com/thunderkds/personal-agentic-claude"*.
Pattern reference: the kit's own site in `~/workspace/pets/personal-agentic-claude` (`site/index.html`,
`vercel.json`, `.vercelignore`, `PROJECT_SPEC_SITE.md`, `tests/test_site_content.py`).

---

## Purpose

A single public page that answers, for someone arriving from the GitHub link:

1. **What is this?** — an offline, rule-based repository verifier exposed as an MCP server and CLI:
   it rates a repo (or a change) per dimension from declared rules over measured metrics, and abstains
   instead of guessing. The engine makes no model call and no network request (NFR-001, FR-040).
2. **How do I run it?** — the shared-container path (`docker compose up -d scorer` from a clone +
   `claude mcp add --transport http ...`), the stdio alternative, and the CLI.
3. **What does it measure?** — the 13 rated dimensions (+ `change-risk`) and the 32 evaluation areas,
   with which areas have a rule today, which are pack-gated, and which have none.
4. **How does scoring work?** — declared rules over measured metrics, coverage floors, abstentions,
   the improvement plan, source tags/citations.
5. **What does a result look like?** — one sample scorecard: easy-verifier scoring **itself** at
   `project` scope, labelled with the commit and date it was taken.

It is a **reference surface, not a project surface.** It never shows KANBAN rows, task IDs, memory
contents, DDR internals, or in-flight work.

## Decisions (user, 2026-10-19)

| Question | Answer |
|---|---|
| Content | What it is + install; dimensions + 32 areas; sample score report; how scoring works (all four) |
| Deploy | Vercel Git integration, production from `main` (same as the kit) |
| Location | `site/` in this repo, own spec + board (this file, `PROJECT_KANBAN_SITE.md`) |
| Sample report subject | easy-verifier scoring itself (Supervisor default, stated to the user; another public repo may replace it on request). Not personal-agentic-claude — not published without explicit OK. |

## Audience

Developers evaluating the verifier from a GitHub link. Assume they know git, Docker and that Claude
Code / MCP exist; assume they know nothing about this repo's vocabulary (dimension, pack, abstention,
coverage floor) — the page defines each term the first time it is used.

## Non-goals (v1)

- No search, no client-side routing, no framework, no build step, no `package.json`.
- No analytics, no cookies, no forms, no external asset hosts (fonts, CDNs, images all inline/local).
- No live scoring from the page; the sample scorecard is a static committed snapshot.
- ~~No pull-and-run Docker Hub instructions~~ — superseded 2026-10-19 by T118 (user: "let build it
  for now and use the 0.1.0 also"): the page leads with pulling `temvar/easy-verifier-mcp:0.1.0`, a
  current-code image the operator publishes. Commands on the page must still appear verbatim in the
  docs (drift test).
- No CI workflow in this repo deploys the site. Deploy is Vercel's Git integration: a push to `main`
  deploys production.

## Stack decision

Plain HTML + CSS in `site/index.html`, no build — same rationale as the kit: the content is one page
of lists and tables, and the repo has no node toolchain. Vercel serves `site/` as-is via
`vercel.json` `outputDirectory`. `.vercelignore` is an **allowlist** (`*`, then `!site/`,
`!site/**`, `!vercel.json`) so `memory/`, `tasks/`, `reports/`, KANBANs and `src/` are never
uploaded by a CLI deploy.

## The drift constraint (the load-bearing one)

The page lists facts that live in code. A hand-maintained copy goes stale on the next rule change
(the kit's README drifted for months — kit T081). So the site content is **asserted against the
source of truth by an automated test** (`tests/test_site_content.py`, the Gate 5 test):

| Site content | Source of truth |
|---|---|
| Dimension list | `easy_verifier.dimensions.DIMENSIONS` keys |
| 32 evaluation areas | `easy_verifier.core.judge.AREAS` (order and text) |
| Per-area status (ruled / pack-gated + pack name / no rule) | `judge.RATING_RULES`, `judge.DOCUMENTATION_RULES`, `judge.PACK_FLOORS`, `judge.areas_without_rule(...)` |
| Install / run commands | must appear verbatim in `README.md` or `docs/DOCKER_MCP_GUIDE.md` / `docs/LOCAL_MCP_GUIDE.md` |
| Sample scorecard numbers | `site/sample-score.json` (committed snapshot) — overall, per-dimension values and abstentions on the page equal the snapshot |

Adding an area rule, a dimension, or a pack without updating the page must fail the suite.

**Snapshot regeneration** is a manual, documented command (in `RUNBOOK.md`/`docs/RELEASE_GUIDE.md`
section added by T116), not a test: the snapshot is a dated record, so the test checks the page
matches the snapshot, not that the snapshot matches today's engine output.

## Safety constraints

- Nothing under `site/` may contain an absolute host path (`/home/`, `/Users/`, `/workspace`), an
  email address, or a token-shaped string. The sample snapshot is reduced to the fields the page
  shows (ratings, abstention reason codes, overall, areas, provenance commit/date) — the full 1 MB
  payload with excerpts is never committed under `site/`.
- External links only to `github.com/thunderkds/easy-verifier-mcp` and cited standards already in
  the reference registry.

## Release dependency

Production deploys from `main`, and `github/main` is still the initial commit (develop is ~866
commits ahead as of 2026-10-19). The site goes live only after a develop → `main` release, which is
a separate `ship` step owned by the operator — not part of T115/T116. Connecting the repo in the
Vercel dashboard is also an operator action (the Vercel CLI is not installed on this machine).

## Glossary (site-facing terms)

| Term | Meaning on the page |
|---|---|
| Dimension | One independently rated aspect (e.g. `architecture`, `security`) |
| Evaluation area | One of the 32 cited review areas a rule can measure |
| Pack | A dimension's rule set; `finance`, `healthcare`, `frontend-a11y` are optional and only run when the repo shows that domain |
| Abstention | No number given, with a reason code, because evidence was below the declared floor |
| Improvement plan | Unmet rules ordered by the declared, recomputed gain of fixing each |
