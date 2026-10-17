# TASK_REVIEW — T112: Agent-confirmed test ↔ changed-symbol pairs

> Sibling of `tasks/TASK_GUIDE_T112.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t112_test_symbol_pairs.py` — 55 tests (AC1–7, AC10); 51 fail on c457c70 (4 no-gate cases pass there by design). Supervisor re-run 2026-10-17: T112 + T107–T110 + T055 + T100 → `261 passed in 58.14s`, exit 0 |
| Verification command run | ☑ pass | `pytest -q tests/test_t112_test_symbol_pairs.py …` exit 0 (261 passed); `ruff check src tests`: All checks passed (agent) |
| Negative cases hold | ☑ pass | substring, cross-project, self-declared helper, short/common symbols, deleted test, malformed/duplicate/off-change/ref-less/bad-ref answers all rejected without changing the pair set (tests listed above) |
| verify | ☑ pass | Supervisor drove the real CLI on the scratch demo repo (`cli score --scope changes --ref HEAD`): no answer → change_risk 100 (detected symbol pair); `test_pairs` reject → 0 (fail); confirm with `ref tests/test_api.py:9` → 100 — pass. AC8: project payload sha256 byte-equal to develop on this repo and fullstack-ts; AC9 3/3 pre-registered expectations matched (agent) |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the diff of change_risk.py, gate.py, score/synthesis/pipeline/models/roles/report, mcp_server.py, blast_radius `_diff_files` headers; manual security pass on untrusted `agent_input.test_pairs` (bounded 200 entries/500 chars, keys redacted+clipped, agent paths never opened — only compared against the change's file set). 0 P0/P1; P3s noted below |
| Full smoke suite still green (no regression) | ☑ pass | Agent full run: 3144 passed, 3 skipped; T101 stub fixed; remaining T014 `test_module_import_emits_nothing_to_stdout` + 3 T101 HTTP errors reproduce identically on `develop` (Supervisor re-run: `ModuleNotFoundError: No module named 'mcp'` in the subprocess — broken `.venv`, not T112) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend task; report gains one text line in the existing change-risk block |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend task |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend task |

---

## Stage 4 code-review (Supervisor, 2026-10-17)

- P0/P1: none.
- P3: test references are counted anywhere in the test text, comments and strings included (`_references`).
- P3: proposals show redacted paths while answers must name raw paths; if redaction ever alters a path the agent cannot answer that pair.
- P2 (accepted deviation): symbol pairs bound projects by manifests only, not test-strategy's layout rule (needed for AC2's own example).

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-17T03:17:04Z by backend-developer on `feat/T112-test-symbol-pairs` at
`c457c70` -- no implementation commit yet). Synthetic repo (built by a scratch script): root
`pyproject.toml`; `utils/dates.py` defines `def parse_date(text)`; `tests/test_api.py` imports and
calls `parse_date`. Commit 1 `chore: initial`; commit 2 `fix: parse_date added one day` edits the
body of `parse_date` and adds `test_parse_date_keeps_the_day` (calling `parse_date`) to
`tests/test_api.py`.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-10-17T03:17:04Z
$ PYTHONPATH=src:<py312 site-packages> python3.12 -m easy_verifier.adapters.cli score \
    --repo <scratch>/demo --scope changes --ref HEAD < /dev/null > before.json   # exit=0
change_risk 0 | kind bugfix detected
  bugfix_without_regression_test = 0 passed=False
    cites: ['utils/dates.py']
    derivation (metrics): "0 matched test files: none of the test files added or changed
    (tests/test_api.py) matches the 1 changed source file(s) cited; a test file counts when it is
    added or changed in this change and its name is a conventional test name of a changed source
    file in the same project (test-strategy's correspondence; project boundaries read from
    manifests anywhere above the files); a deleted test never counts"
```

The changed test calls the changed function, but because its name does not correspond
(`test_api.py` vs `dates.py`) the bugfix scores 0 / fail.

**AFTER** (backend-developer, 2026-10-17T03:34:12Z, branch `feat/T112-test-symbol-pairs`; same
repo, same command):

```
exit=0
change_risk 100 | bugfix_without_regression_test 1 passed= True cites ['tests/test_api.py']
pairs [{"source": "utils/dates.py", "test": "tests/test_api.py", "basis": "symbol",
        "symbol": "parse_date", "ref": "tests/test_api.py:9", "status": "detected"}]
derivation: 1 matched test file(s): utils/dates.py -> tests/test_api.py (symbol parse_date at
tests/test_api.py:9, detected); a test file counts when it is added or changed ...
```

**DELTA**: a bugfix whose test calls the changed function under a different file name now counts
as tested (cited by symbol and line), and the calling agent can confirm, reject or add pairs.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]

---

## Deviations and edge-case rules (backend-developer; rules 1-8 accepted by the Supervisor 2026-10-17)

1. **Deviation -- project boundary for symbol pairs is manifest-only.** A symbol pair needs the
   source and test to share the deepest directory holding a project manifest (repository root
   when none does). test-strategy's `_project_boundary` also cuts at the first non-layout
   directory, so `utils/dates.py` (project `utils`) and `tests/test_api.py` (project root) would
   be different projects and the guide's own AC2 example could never pair. Name pairs keep
   `_correspondence` unchanged; cross-project tests (separate manifests) still never pair.
2. Enclosing declaration = the nearest declaration above the changed line inside its hunk, else
   the one git names in the hunk header (a header alone misses a small function whose `def`
   line is a context line of the hunk).
3. A symbol under 4 characters or in `COMMON_SYMBOLS` never pairs; a name the test declares
   itself is never a reference.
4. The cited `ref` prefers the first line the diff added to the test that names the symbol,
   else the first line naming it.
5. Worktree scope reads `git diff HEAD` (not used above the changes-diff ceiling); an untracked
   file counts every line as added.
6. `needs_input.test_pairs` is not asked when there is neither a proposal nor an unpaired
   changed test (nothing to judge); asked until at least one answer entry applies.
7. Duplicate answers, rejecting a pair that was not proposed, and added pairs without a valid
   `ref` are listed in `rejected` and change nothing.
8. A bugfix with changed source now reads its changed tests through `_changed_code` (as the
   feature rule already did); a bugfix with no changed source still reads nothing.

## AC9 -- pre-registered expectations (written 2026-10-17, before any AC9 run)

Command per row: `cli score --repo <real-repos>/<alias> --scope changes --ref <ref> < /dev/null`,
run in the background one at a time, on branch `feat/T112-test-symbol-pairs`.

| # | Repo / ref | Expected |
|---|---|---|
| (a) | node-monorepo `09be767d0` (bugfix, no test) | `change_risk` 0, `bugfix_without_regression_test` 0 fail; `test_pairs.pairs` = [], `unpaired_tests` = [] (no proposals; MCP would not ask) |
| (b) | fullstack-ts `522d666` (bugfix with test, T108) | still 100, metric 1; `InventoryPage.tsx -> InventoryPage.test.tsx` now `basis: "symbol"` (symbol `InventoryPage`, from the `export function InventoryPage()` hunk header), status detected; `IngredientFormDialog.tsx` pairs by symbol only if the test names one of its changed symbols -- expected unpaired |
| (c) | fullstack-ts `c2edf83` (no kind prefix -> feature) -- found by the search below | `apps/web/src/components/LowStockWidget/api.ts -> LowStockWidget.test.tsx` `basis: "symbol"` (symbol `fetchLowStock`), a pair the name rule cannot make (`api.ts` vs `LowStockWidget.test.tsx`); `LowStockWidget.tsx -> LowStockWidget.test.tsx` present (symbol or name); the api-side sources (`alerts.*`, dto, module) unpaired |

Search used for (c): a scratch script that, for the newest 300 non-merge commits of a repo, parses
`git show -M <sha>` with `_diff_files`, takes `change_risk.changed_symbols` of each changed source
and lists changed tests that reference one (`_references`) but are not a name match
(`_correspondence`). fullstack-ts: 69 candidate pairs; node-monorepo: none printed (run under a 300 s timeout, so
not proven exhaustive).

### AC9 results (backend-developer, runs started 03:33:27Z / 03:33:41Z / 03:33:47Z, all exit 0)

| # | Headline | Pairs | Matches expectation |
|---|---|---|---|
| (a) | `change_risk` 0, `bugfix_without_regression_test` 0 fail, cites `backend/server/dashboard/controllers/recently-added-companies.js` | `pairs` [], `unpaired_tests` [], `unpaired_sources` [that file] | yes |
| (b) | `change_risk` 100, metric 1 pass, cites `apps/web/src/features/inventory/InventoryPage.test.tsx` | `InventoryPage.tsx -> InventoryPage.test.tsx` (symbol `InventoryPage` at `InventoryPage.test.tsx:279`, detected); `IngredientFormDialog.tsx` unpaired | yes |
| (c) | feature, `change_risk` 0, `new_code_without_test_share` 0.667 fail (4 of 6 api-side sources uncovered) | `LowStockWidget.tsx -> LowStockWidget.test.tsx` (symbol `LowStockWidget` at :3, detected); `api.ts -> LowStockWidget.test.tsx` (symbol `fetchLowStock` at :12, detected) -- the symbol-not-name pair; `inventory-alerts.e2e.spec.ts` unpaired; alerts controller/service/dto/module unpaired | yes |

### AC8 -- project scope byte-equal to `develop` (08ab7fb)

```
2026-10-17T03:32:16Z this-repo develop exit=0 d81329c56c53b3e5fa6fb351177527ce0ff579e33e8a489047b614772ca7448a
2026-10-17T03:32:32Z this-repo t112    exit=0 d81329c56c53b3e5fa6fb351177527ce0ff579e33e8a489047b614772ca7448a
2026-10-17T03:32:50Z fullstack-ts develop exit=0 98b9346acfd541904f4385903ab73056a042eeb30c5da5832a97366f10d095a7
2026-10-17T03:33:07Z fullstack-ts t112    exit=0 98b9346acfd541904f4385903ab73056a042eeb30c5da5832a97366f10d095a7
```

(this repo = a `develop` worktree as the target; the fullstack-ts hash also equals T108's.)
