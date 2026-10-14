# TASK_REVIEW — T085: a11y framework-default browser targets

> Sibling of `tasks/TASK_GUIDE_T085.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t085_a11y_default_browsers.py` (7 tests: Next, Nuxt not credited, explicit wins, neither, test-path not credited, two Next configs deterministic, cited field + local-layer shape) |
| Verification command run | pass | `ruff check src tests` -> All checks passed!; full suite: `2 failed, 2536 passed, 2 skipped in 399.92s` (the 2 known container failures in tests/integration) |
| Negative cases hold | pass | explicit .browserslistrc + next.config → explicit wins; neither → value 1 unchanged; nuxt.config.ts alone → value 1 (Nuxt dropped); config under test paths not credited; local layer rejects bare glob — pass |
| verify | pass | Supervisor 2026-10-08 independent tapchat-web `score --scope project --agent-input {packs:[frontend-a11y]}` on T085 src (Next-only): overall 64, frontend-a11y 60 (was 45), browser metric 0 'Next.js framework default'; pack off sha256 767479ce… identical to BEFORE — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Stage 4 code-review (Supervisor): frontend_a11y _patterns/_scan/_metrics, registry PACK_FIELDS/_VALUE_SHAPES/_PREFIXED_FIELDS, pack toml, SCORING_RULES. Finding P1 (citation does not support claim): Nuxt cited to esbuild transform target `esnext`, not a browser target → Nuxt dropped (99e3fa3). Low risk; paths redacted — pass |
| Full smoke suite still green (no regression) | pass | Supervisor rerun after Nuxt drop: 2 failed (known stale-image container tests), 2536 passed, 2 skipped; T049 tests unedited — pass |
| **UI: Visual regression (diff or verdict pasted)** | N/A | pure backend task |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | pure backend task |
| **UI: Responsiveness at target viewports** | N/A | pure backend task |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-08T07:29:05Z-07:29:45Z by backend-developer at worktree HEAD 4d2223f, no code changed; real repo `/home/hungnguyenhuu/workspace/project/beautifly/github/tapchat-web`, `score --repo R --scope project`, pack on via `--agent-input {"packs": ["frontend-a11y"]}` file):

```text
pack on : exit=0  overall 60, contributors architecture 67, code-quality 70, security 59, frontend-a11y 45
  browser_support_declaration_missing value=1
    derivation: "no browser-support declaration (a browserslist query, a package.json browserslist key, a Babel targets option or a Vite build.target) in 14 candidate file(s)"
    computed_from: 14 package.json files
pack off: exit=0  sha256 767479ce04a0915be59eee6915ee1636d48d1a72a8936e8aaf7303a520d316a9
```

**AFTER** (2026-10-08T07:53:11Z-07:54:01Z, same repo and commands, worktree with the change):

```text
pack on : exit=0  overall 64, frontend-a11y 45 -> 60 (other contributors unchanged: 67/70/59)
  browser_support_declaration_missing value=0
    derivation: "no explicit browser-support declaration; apps/admin-dashboard/next.config.ts is a Next.js config, so the targets are the Next.js framework default (the pack's browser_support_default_entries)"
    computed_from: ['apps/admin-dashboard/next.config.ts']
pack off: exit=0  sha256 767479ce04a0915be59eee6915ee1636d48d1a72a8936e8aaf7303a520d316a9  (identical to BEFORE)
```

**Nuxt dropped (Supervisor review, 2026-10-08)**: the only official Nuxt statement found was `esbuild.options.target = "esnext"` (https://nuxt.com/docs/api/nuxt-config#esbuild), a transform target, not a documented default browser target; per the guide's STOP condition the Nuxt entry was removed. A `nuxt.config.ts` with no explicit declaration still rates 1 (test `test_nuxt_config_is_not_credited_no_documented_default`). The tapchat-web AFTER above is Next.js-only and unaffected. Tests after the change: `97 passed` (t049 + t085 + t047), `ruff check src tests` clean.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: Supervisor reran tapchat-web pack on/off independently 2026-10-08 on the final (Next-only) branch.
