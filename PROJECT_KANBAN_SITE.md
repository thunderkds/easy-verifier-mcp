# PROJECT_KANBAN — easy-verifier Landing Site (v1)

> Separate board per Hard-Stop Gate 4: the static site deploys to Vercel, a different target from
> the verifier engine. Engine tasks live on `PROJECT_KANBAN.md` and are never mixed in here.
> Spec: `PROJECT_SPEC_SITE.md`.
>
> Task IDs stay in the shared, monotonic `Txxx` namespace because the spawn-validation hooks parse
> that exact pattern.

## Todo


## In Progress

- [ ] **T116** — **Vercel deploy configuration + runbook.** `vercel.json` (`outputDirectory: site`, no build command), `.vercelignore` allowlist (`*`, `!site/`, `!site/**`, `!vercel.json`), a "Landing site" section in `docs/RELEASE_GUIDE.md` with the operator's exact steps (connect repo in Vercel dashboard, production branch `main`, snapshot regeneration command), and a test that pins both config files. The Supervisor plans; **the operator executes** the dashboard connection and the develop → `main` release — no agent pushes or deploys. (Depends on: T115) | common-infrastructure | C1 | Risk: Med | P1 | 🔄 In Progress 2026-10-19 (worktree `../easy-verifier-mcp-T116`, branch `feat/T116-vercel-config`) | Guide: `tasks/TASK_GUIDE_T116.md`

## Ready for Review


## Done

- [x] **T115** — **Static landing page (`site/index.html`) + self-score snapshot + drift test.** One page, plain HTML/CSS, no build, no external hosts. Sections: what it is, run it (shared container from a clone, stdio, CLI), dimensions, the 32 evaluation areas with per-area status (ruled / pack-gated / no rule), how scoring works, sample scorecard from `site/sample-score.json` (easy-verifier scoring itself, commit + date shown). `tests/test_site_content.py` asserts dimensions, areas, per-area status, commands and scorecard numbers against their sources of truth, and that `site/` holds no host paths/emails/secrets. User decisions 2026-10-19 (all four content blocks; site/ in this repo). | frontend-developer | C2 | Risk: Low | P1 | ✅ Done 2026-10-19 (merged f1b9989; test_site_content 16 tests + test_t100 = 19 passed; Stage 4 code-review: 1 P1 + 2 P3 fixed, report reports/code-review_feat-T115-landing-site_20261019T114147.html; Stage 5 verify pass in headless Chrome; snapshot = self-score @ 8062b35, overall 47; contrast worst 5.75:1 light / 6.98:1 dark; observation: 32-areas Status column off-screen at 375px until swiped) | Guide: `tasks/TASK_GUIDE_T115.md`

## Blocked

| Task | Blocked by | Since |
|------|-----------|-------|
| (go-live) | develop → `main` release (operator, `ship`) and Vercel dashboard connection (operator) | 2026-10-19 |
