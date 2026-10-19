# PROJECT_KANBAN — easy-verifier Landing Site (v1)

> Separate board per Hard-Stop Gate 4: the static site deploys to Vercel, a different target from
> the verifier engine. Engine tasks live on `PROJECT_KANBAN.md` and are never mixed in here.
> Spec: `PROJECT_SPEC_SITE.md`.
>
> Task IDs stay in the shared, monotonic `Txxx` namespace because the spawn-validation hooks parse
> that exact pattern.

## Todo

- [ ] **T119** — **Landing page: "Easy Verifier" name, tab icon, visual scoring, pull-and-run first.** User 2026-10-19 (four asks). Title/h1/brand "Easy Verifier"; `site/favicon.svg`; `#scoring` step diagram (repository → evidence → rules → coverage check → rating | abstention → overall → plan) + worked example from the snapshot; `#run` leads with Pull → Run → Register copied verbatim from T118's docs, other ways below. (Depends on: T118) | frontend-developer | C2 | Risk: Low | P1 | Guide: `tasks/TASK_GUIDE_T119.md`

## In Progress


## Ready for Review


## Done

- [x] **T117** — **Restyle the landing page in the kit's theme.** User 2026-10-19: "keep the theme like personal agentic claude". Re-skin `site/index.html` with the kit's dark neon tokens, sticky sidebar nav (mobile collapse via inline script), header card, cyan uppercase h2, pill tags, green install blocks; dark-only like the kit; `--muted` lightened only as needed for 4.5:1. No content, id, data-* or snapshot change — T115 drift tests stay green unchanged; new theme tests pin tokens, nav and no-external-script. (Depends on: T115) | frontend-developer | C1 | Risk: Low | P1 | ✅ Done 2026-10-19 (merged e7bd53e; 12 new theme tests + 16 site-content + 7 deploy + 3 t100 = 38 passed, T115 drift tests unchanged; Stage 4 Supervisor review P0/P1/P2 0, one cosmetic P3 left; screenshots 375/768/1280 + kit-1280 inspected; deviations for AA: --muted #8080b0, --purple-text #ae5ff8; security review N/A Risk Low) | Guide: `tasks/TASK_GUIDE_T117.md`

- [x] **T116** — **Vercel deploy configuration + runbook.** `vercel.json` (`outputDirectory: site`, no build command), `.vercelignore` allowlist (`*`, `!site/`, `!site/**`, `!vercel.json`), a "Landing site" section in `docs/RELEASE_GUIDE.md` with the operator's exact steps (connect repo in Vercel dashboard, production branch `main`, snapshot regeneration command), and a test that pins both config files. The Supervisor plans; **the operator executes** the dashboard connection and the develop → `main` release — no agent pushes or deploys. (Depends on: T115) | common-infrastructure | C1 | Risk: Med | P1 | ✅ Done 2026-10-19 (merged 96c14bd; test_site_deploy_config 7 tests, with site content + test_t100 = 26 passed; Stage 4 code-review 1 P2 + 2 P3 fixed; security review manual (built-in needs origin/HEAD), no findings; reports reports/*_feat-T116-vercel-config_20261019T120221.html; verify N/A until Vercel is connected, snapshot reduce.py exercised on withheld + real input; README untouched pending project name) | Guide: `tasks/TASK_GUIDE_T116.md`

- [x] **T115** — **Static landing page (`site/index.html`) + self-score snapshot + drift test.** One page, plain HTML/CSS, no build, no external hosts. Sections: what it is, run it (shared container from a clone, stdio, CLI), dimensions, the 32 evaluation areas with per-area status (ruled / pack-gated / no rule), how scoring works, sample scorecard from `site/sample-score.json` (easy-verifier scoring itself, commit + date shown). `tests/test_site_content.py` asserts dimensions, areas, per-area status, commands and scorecard numbers against their sources of truth, and that `site/` holds no host paths/emails/secrets. User decisions 2026-10-19 (all four content blocks; site/ in this repo). | frontend-developer | C2 | Risk: Low | P1 | ✅ Done 2026-10-19 (merged f1b9989; test_site_content 16 tests + test_t100 = 19 passed; Stage 4 code-review: 1 P1 + 2 P3 fixed, report reports/code-review_feat-T115-landing-site_20261019T114147.html; Stage 5 verify pass in headless Chrome; snapshot = self-score @ 8062b35, overall 47; contrast worst 5.75:1 light / 6.98:1 dark; observation: 32-areas Status column off-screen at 375px until swiped) | Guide: `tasks/TASK_GUIDE_T115.md`

## Blocked

| Task | Blocked by | Since |
|------|-----------|-------|
| (go-live) | develop → `main` release (operator, `ship`) and Vercel dashboard connection (operator) | 2026-10-19 |
