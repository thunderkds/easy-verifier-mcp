# TASK_REVIEW — T049: Frontend accessibility pack

> Sibling of `tasks/TASK_GUIDE_T049.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t049_a11y_pack.py` (61 tests, red-first per rule: AC1 img/controls/aria-hidden incl. empty alt, spread props, htmlFor, hidden/submit inputs, capitalised components; AC2 viewport + Next default + zoom, browser support pairs; AC3 JSX/Vue/Svelte/Angular/Jinja/ERB; AC4 inactive pack + byte-equal replay; AC5 weights/floor/exact-50 test). Included in the full run below |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!` (implementer); full suite below |
| Negative cases hold | ☑ pass | `alt=""` met; `{...props}` not verifiable (never missing); `<Input>`/`<Select>` components not DOM controls (regression test after a real-repo false positive: tapchat 20 → 1); `type=hidden/submit` not judged; `i<input` comparison not a tag |
| verify | ☑ pass | Supervisor MCP `score`: packs off → no a11y metrics, #19 uncovered; `agent_input.packs=["frontend-a11y"]` → rating 19 with arithmetic consistent (15/80). Real repo tapchat-web: pack off byte-identical to BEFORE (sha256 d05f4709…), pack on 45 / overall 65→60 with 2 real zoom-disabled hits and 1 real unlabeled input — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | reviewed new `packs/frontend_a11y.py` + `registry/packs/frontend-a11y.toml` + wiring in judge/metrics/registry/improve/report/mcp_server (mirrors T048 finance pack), test file, doc/pin edits. Weights 25/25/20/15/15 (WCAG 2.2 SC 1.1.1, 1.3.1+4.1.2, 4.1.2+Using ARIA rule 4, 1.4.4+1.4.10; browser support ISO 25010 + Browserslist, project-default) sum 100, admit exact 50 — accepted under the 2026-10-07 policy. Findings: P0 0 / P1 0 / **P2** viewport credits Next/Nuxt default viewport but not Next's default browser targets (asymmetry; −15 on tapchat) — reported to user / P3 markup cap 500 files disclosed in derivation. Security: pack patterns load from the curated layer only (`load_pack`), so a scanned repo cannot inject regexes; secret-bearing files refused by `read_source`; paths redacted — clean |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor run on 9520b89: `2 failed, 2407 passed, 2 skipped in 342.27s` — failures are the known stale-image container tests (`missing=['api','data','infrastructure','operations','supply-chain']`), pre-existing — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend analysis of target-repo markup; no UI of our own changed (report rows reuse existing layout) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend-only |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend-only |
| Repro loop | ☐ N/A | feature task |
| Regression test | ☑ pass | T047/T071/T072/T082 pins updated for the third pack; all green in the full run |
| Smoke suite | ☑ pass | real-repo pack on/off (verify row) |
---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer before any T049 implementation commit, worktree HEAD = c50955f; real repo = `/home/hungnguyenhuu/workspace/project/beautifly/github/tapchat-web` (pnpm/turbo monorepo, Next.js + React, 832 JSX/TSX/HTML files), read-only):

```text
$ date -u; git rev-parse HEAD
2026-10-08T03:40:49Z
c50955f839d7e6d4dde26a16a698c5c87a3080fd
$ PYTHONPATH=<worktree>/src python -m easy_verifier.adapters.cli score --repo tapchat-web </dev/null > tapchat_before.json
exit=0   (finished 2026-10-08T03:41:07Z)
stderr:
warning [batches]: read batches 1 of 5 (200 of 891 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
overall 65 contributors [['architecture', 67], ['code-quality', 70], ['security', 59]]
areas_measured 14
areas_without_rule ['Financial integrity & historical reconstruction', 'Transactions, concurrency, idempotency', 'PHI minimization, retention, test-data safety', 'Accessibility, responsive UX, browser compat', 'Vendor, BAA, data classification, residency']
detected_stack {'languages': ['js-ts'], 'frameworks': [{'name': 'next', 'language': 'js-ts'}, {'name': 'react', 'language': 'js-ts'}]}
sha256 d05f470941b57176fb20b422564490dd40acd005cb221fc34d7806852829b9f3

$ date -u    # same repo, pack requested via --agent-input {"packs": ["frontend-a11y"]}
2026-10-08T03:41:39Z
exit=0
stderr:
warning [registry]: unknown pack 'frontend-a11y' ignored; known packs: healthcare, finance
warning [batches]: read batches 1 of 5 (200 of 891 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
overall 65
ratings ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'infrastructure', 'operations', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
#19 in areas_without_rule True
cmp tapchat_before.json tapchat_before_on.json -> IDENTICAL
```

The `frontend-a11y` pack is unknown (ignored with a warning), no accessibility metric exists, and area #19 "Accessibility, responsive UX, browser compat" is listed in `areas_without_rule`.

**AFTER** (HEAD 9520b89, same repo; implementer runs, summarised by the Supervisor 2026-10-08 because the implementer hit the step limit):

```text
pack off (2026-10-08T04:04:28Z): sha256 d05f470941b57176fb20b422564490dd40acd005cb221fc34d7806852829b9f3  ← byte-identical to BEFORE (Supervisor sha256sum check)
pack on  (2026-10-08T04:04:50Z, --agent-input {"packs": ["frontend-a11y"]}): overall 60, frontend-a11y rating 45, areas_measured 14 → 15 (#19 leaves areas_without_rule)
  images_without_alt_observed                 0  (1 verifiable img in 500 of 507 markup files; components not followed)
  form_controls_without_label_observed        1  packages/ui/src/components/user/ChatBox/index.tsx:42 (<input>, placeholder only)
  aria_hidden_focusable_observed              0
  viewport_missing_or_zoom_disabled_observed  2  apps/web-regular-user/src/app/layout.tsx:59, apps/web-verified-user/src/app/layout.tsx:54 (maximumScale 1 / userScalable false)
  browser_support_declaration_missing         1  (no browserslist / Babel targets / Vite build.target in 14 candidate files)
```

Supervisor MCP check (fixture repo, `score` via stdio): no packs → `isError False`, no frontend-a11y metrics, #19 uncovered; `agent_input.packs=["frontend-a11y"]` → rating 19 (img 1, control 1, aria-hidden abstains, viewport 0, browser support 1 → earned 15 of 80 measured), #19 measured.

**DELTA**: A user who switches on `frontend-a11y` now gets a cited WCAG 2.2 accessibility rating (alt text, form labels, aria-hidden on focusable elements, zoom/viewport, browser support) with path:line hits; without the pack the output is byte-for-byte unchanged.

**WITNESS**: Supervisor, 2026-10-08 — re-ran the full suite on 9520b89, checked the pack-off sha256 against BEFORE, and drove the MCP `score` tool with the pack on/off; trace attributed via active_task (`memory/event-trace/T049.jsonl`).
