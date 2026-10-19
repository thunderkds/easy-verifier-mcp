# PROJECT_KANBAN — easy-verifier Landing Site (v1)

> Separate board per Hard-Stop Gate 4: the static site deploys to Vercel, a different target from
> the verifier engine. Engine tasks live on `PROJECT_KANBAN.md` and are never mixed in here.
> Spec: `PROJECT_SPEC_SITE.md`.
>
> Task IDs stay in the shared, monotonic `Txxx` namespace because the spawn-validation hooks parse
> that exact pattern.

## Todo

- [ ] **T116** — **Vercel deploy configuration + runbook.** `vercel.json` (`outputDirectory: site`, no build command), `.vercelignore` allowlist (`*`, `!site/`, `!site/**`, `!vercel.json`), a "Landing site" section in `docs/RELEASE_GUIDE.md` with the operator's exact steps (connect repo in Vercel dashboard, production branch `main`, snapshot regeneration command), and a test that pins both config files. The Supervisor plans; **the operator executes** the dashboard connection and the develop → `main` release — no agent pushes or deploys. (Depends on: T115) | common-infrastructure | C1 | Risk: Med | P1 | Guide: `tasks/TASK_GUIDE_T116.md`

## In Progress

- [ ] **T115** — **Static landing page (`site/index.html`) + self-score snapshot + drift test.** One page, plain HTML/CSS, no build, no external hosts. Sections: what it is, run it (shared container from a clone, stdio, CLI), dimensions, the 32 evaluation areas with per-area status (ruled / pack-gated / no rule), how scoring works, sample scorecard from `site/sample-score.json` (easy-verifier scoring itself, commit + date shown). `tests/test_site_content.py` asserts dimensions, areas, per-area status, commands and scorecard numbers against their sources of truth, and that `site/` holds no host paths/emails/secrets. User decisions 2026-10-19 (all four content blocks; site/ in this repo). | frontend-developer | C2 | Risk: Low | P1 | 🔄 In Progress 2026-10-19 (worktree `../easy-verifier-mcp-T115`, branch `feat/T115-landing-site`) | Guide: `tasks/TASK_GUIDE_T115.md`

## Ready for Review

## Done

## Blocked

| Task | Blocked by | Since |
|------|-----------|-------|
| (go-live) | develop → `main` release (operator, `ship`) and Vercel dashboard connection (operator) | 2026-10-19 |
