# TASK_REVIEW — T041: supply-chain dimension (#20, #21, #22)

> Sibling of `tasks/TASK_GUIDE_T041.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t041_supply_chain.py` (20 tests: AC1 discovery + five roles; AC2 cited rules by area, weights 100, rollback documentation rule; AC3 patterns from registry/generic layer; AC4 floor pinned in `tests/test_judge.py::test_floor_table_is_complete_static_data_and_matches_live_discovery`; AC5 all-met fixture rates 100, no-roles fixture abstains naming every miss; sabotage pair per predicate; D1 Drone `image:` tag+digest and GitHub `services: image:` cases, both failing on pre-fix code: `2 failed, 18 passed`). Run: `20 passed` within the full suite below. |
| Verification command run | ☑ pass | `cd <worktree> && COMPOSE_FILE=compose.yaml:<scratch>/compose.t041.yaml PYTHONPATH=src <main>/.venv/bin/python -m pytest -q` → `2233 passed, 2 skipped in 262.09s (0:04:22)`, exit 0. `python -m ruff check src tests` → `All checks passed!` (2026-10-07, commit 633f874). |
| Negative cases hold | ☑ pass | No roles → abstains `below_coverage_floor` naming all five misses; no CI → CI rules abstain and the dimension abstains `insufficient_measured_weight` (measured_share 0.35, T067); workflow without external refs → pin rule abstains (zero denominator); `uses:` in a comment not counted; local `./` and `@sha256` digests not unpinned. |
| verify | ☑ pass | Supervisor Stage 5, 2026-10-07 07:55 UTC, commit 3130c41 — pass: `list-dimensions` → 9 dims incl. `supply-chain`; MCP stdio `tools/list` → 13 tools incl. `supply-chain`; `supply-chain --repo kitchd --scope project` CLI vs MCP `structuredContent` identical (parity True), 10 excerpts, sources_missing ['release-config']. Independent full-suite re-run: `2235 passed, 2 skipped in 254.24s`; ruff `All checks passed!`. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor Stage 4 code-review over `git diff f5df736..HEAD` (42 files): core roles/metrics/metric_tables/registry/judge/improve/report, dimensions/supply_chain, curated TOMLs, docs, tests; unrelated dimensions not reviewed. Findings: P1 licence-file globs matched source code (`src/licenseService.ts` etc.) → fixed 3130c41; P2 `\bimage:` matched `base-image:` → fixed 3130c41; P0/P3 none. Security review (manual — built-in needs origin/HEAD): all reads via `read_source` (containment + secret exclusion), CI excerpts redacted centrally in `core/budget.py`, registry tokens go through `token_regex` (no regex injection), new action-reference regex linear — no findings. |
| Stage 4 fixes | ☑ pass | P1: licence-file role now lists conventional names only (LICENSE/LICENCE/COPYING/UNLICENSE and case forms, bare or .md/.txt/.rst, dash-suffix `LICENSE-*`, `LICENSES/**`), so `src/licenseService.ts`, `app/Models/License.php`, `web/src/components/LicenseBadge.tsx` no longer fill it. P2: `action_reference` keys use `(?<![\w-])` instead of `\b`, so `base-image:` is not `image:` while `- image:` / `- uses:` still match. New tests `test_licence_role_matches_licence_files_never_source_code`, `test_a_hyphenated_image_key_is_not_an_image_reference` failed on pre-fix code (`2 failed, 20 passed`), pass after (`22 passed`). Full suite (t041 image): `2235 passed, 2 skipped in 267.65s`, exit 0; ruff `All checks passed!`. Re-score unchanged: bryony supply-chain 35 / overall 62, kitchd 55 / 57, ai-training and coffee still abstain (licence_file_missing 1). |
| Full smoke suite still green (no regression) | ☑ pass | Same run: 2233 passed. Container tests pass only on an image built from this branch (`easy-verifier-mcp:t041` via compose override); on the stale shared `easy-verifier-mcp:0.1.0` they fail `missing=['supply-chain']` — see Known limitations. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Pure backend task, no UI (Constraint 11). |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | Pure backend task, no UI (Constraint 11). |
| **UI: Responsiveness at target viewports** | ☐ N/A | Pure backend task, no UI (Constraint 11). |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured Thu Oct  1 08:31:54 AM UTC 2026, before any implementation commit, from worktree `/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T041` at develop 7a49a98:
`date -u; PYTHONPATH=src .../.venv/bin/python -m easy_verifier.adapters.cli list-dimensions`
Output (full JSON is ~480 lines; top-level dimension entries and their roles, abridged to the dimension names here; no `supply-chain` entry exists):
```
Thu Oct  1 08:31:54 AM UTC 2026
dimensions listed (7): architecture, blast-radius, code-quality, requirement-fidelity, security, solution-fit, test-strategy
```

**AFTER**: captured 2026-10-07 from the same worktree at 633f874, same command:
```
Wed Oct  7 07:43:17 AM UTC 2026
dimensions listed (9): architecture, blast-radius, code-quality, reliability, requirement-fidelity, security, solution-fit, supply-chain, test-strategy
supply-chain keys: ['name', 'purpose', 'roles', 'sources_sought']
roles: ['package-manifest', 'lockfile', 'ci-workflow', 'licence-file', 'release-config']
```
(Seven at BEFORE; reliability arrived from T043 on the rebased base, supply-chain from this task.)

Real repositories, CLI `score --scope project`, before = base f5df736, after = this branch
(bryony/kitchd re-run after D1 at 633f874; ai-training/coffee at cfbf05e, unaffected by D1: no CI file):

| repo | coverage vs floor 0.40 | lockfile_missing | licence_file_missing | ci_actions_unpinned_share | ci_lockfile_install_missing | ci_provenance_step_missing | supply-chain | overall before → after |
|---|---|---|---|---|---|---|---|---|
| kitchd | 4/5 = 0.80 (release-config missing) | 0 | 0 | 1.0 (13 of 13: 12 `uses:` @v4 + `image: postgres:16-alpine`) | 0 (3 `--frozen-lockfile` lines) | 1 | 55 | 58 → 57 |
| bryony | 4/5 = 0.80 | 0 | 0 | 1.0 (1 of 1: `.drone.yml:7 bryony/li-tool-backend-base:master`) | 1 | 1 | 35 | 67 → 62 |
| ai-training | 2/5 = 0.40 (no CI, licence, release config) | 0 | 1 | abstain (no CI file) | abstain | abstain | abstains `insufficient_measured_weight` (0.35) | 64 → 64 |
| coffee-shop-api | 2/5 = 0.40 (same) | 0 | 1 | abstain (no CI file) | abstain | abstain | abstains `insufficient_measured_weight` (0.35) | 72 → 72 |

Rollback documentation result: missing on all four. Areas measured: kitchd 13→15, bryony 12→14,
ai-training 11→12, coffee 11→12. No other dimension's rating changed on any repo.

**Known limitations**
- A templated image reference (`image: ${{ matrix.image }}`) is counted as an unpinned external reference (the unresolved template text is the reference).
- The container tests (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`) need the image rebuilt from this code: the shared local `easy-verifier-mcp:0.1.0` (built 2026-10-06 from the T043 base) fails `missing=['supply-chain']`. Verified here with a separately tagged `easy-verifier-mcp:t041` (compose override), leaving the shared tag untouched; that image predates the D1 data change, which the container tests do not exercise.
- A repository without any CI file gets no supply-chain number (CI rules hold 65 of 100 weight; DDR-0010 measured-weight floor).

**DELTA**: A user can now rate a repository's dependency pinning and licence, CI reproducibility (actions/images pinned, lockfile-faithful install) and provenance/SBOM/signing steps with cited rules, and see whether a rollback document exists, as a ninth dimension.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T041.jsonl`, never the
implementing agent alone]
