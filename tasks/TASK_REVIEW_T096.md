# TASK_REVIEW — T096: A change list is not an architecture description; architecture prose sections count

> Sibling of `tasks/TASK_GUIDE_T096.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | (implementer) tests/test_t096_architecture_doc_shape.py (27 tests; 18 fail on the pre-change documents.py, 9 negative/guard cases pass both ways); tests/test_t089_document_content.py unedited and green |
| Verification command run | ☑ pass (implementer) | full suite `2 failed, 2772 passed, 2 skipped` (the 2 known stale-image container tests); `ruff check src tests` clean. |
| Negative cases hold | ☑ pass | Tables without a change column, and tables without a separator, behave as before. Prose with 2 paths, or with a missing path, does not qualify. URLs and bare words name nothing. An H1 title does not open a section. Supervisor sabotage: `_architecture_section(text, 1)` makes `test_h1_title_naming_architecture_does_not_open_a_section` fail (`1 failed, 29 passed`). |
| verify | ☑ pass | Supervisor 2026-10-13 on `c3f4a2a`: t096 + t089 + t001 -> `126 passed in 11.05s`. Real repos (implementer runs, diff vs BEFORE = 2 citation lines only): every rating identical on fullstack-ts 56/100, node-monorepo 59/83, nest-api 81/90, python-ml 64/83, k8s-ops (abstains), this repo 43/100. pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor review of `core/documents.py` (`CHANGE_COLUMNS`, header tracking in `described_entries`, `prose_paths`, `_architecture_section(min_level)`, `_shape` prose branch). README path unchanged (kind `readme-heading` kept). Regexes are linear. Decisions: fullstack-ts cites `memory/decisions.md` `## Architecture` (real description, accepted); a level-1 title never opens a section. The t001 kind pin was widened by design (AC 7). P0 0 · P1 0. |
| Full smoke suite still green (no regression) | ☑ pass (implementer) | `2 failed, 2772 passed, 2 skipped`; the 2 failures are the known container tests. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend only. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend only. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (implementer, captured 2026-10-13T10:37:15Z-10:38:28Z UTC, before any implementation commit; unmodified worktree HEAD eb81c9c; command per repo, run in background: `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project </dev/null`; python-ml = <real-repos>/python-ml, found in memory/event-trace/T037.jsonl, not in learnings.md; "self" = this worktree; k8s-ops abstains in every dimension):

```
== fullstack-ts
overall 56 | api=38, architecture=100, blast-radius=None, code-quality=70, data=70, infrastructure=None, operations=50, reliability=0, requirement-fidelity=60, security=59, solution-fit=None, supply-chain=55, test-strategy=None
  value None | source role 'architecture-doc' is filled by tasks/TASK_GUIDE_T029.md (content: line 163: | `apps/web/src/App.tsx` | Mount `<ErrorDialogProvider>` |; line 164: | `apps/web/src/features/tasks/api.ts` | Call `notifyApiError()` in error branch |; line 165: | `apps/web/src/features/team/api.ts` | Call `notifyApiError()` in error branch |; line 166: | `apps/web/src/features/notes/api.ts` | Call `notifyApiError()` in error branch |; line 167: | `apps/web/src/components/LowStockWidget/api.ts` | Call `notifyApiError()` in error branch |)
== node-monorepo
overall 59 | api=None, architecture=83, blast-radius=None, code-quality=67, data=40, infrastructure=None, operations=None, reliability=61, requirement-fidelity=None, security=50, solution-fit=None, supply-chain=35, test-strategy=75
  value None | source role 'architecture-doc' is filled by backend/scripts/README.md (content: line 8: - `/common`: contain common scripts.; line 9: - `/companies`: contain scripts to work with `dbcompanies`.; line 10: - `/crunchbase`: contain scripts to work with `dbcrunchbasecompanies`; line 12: - `/similarweb`: contain scripts to work with SimilarWeb data)
== scraping
overall None | api=None, architecture=None, blast-radius=None, code-quality=None, data=None, infrastructure=None, operations=None, reliability=None, requirement-fidelity=None, security=None, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 6: - bin: helper scripts; line 7: - elk: needed scripts and code for elk services; line 8: - vagrant: needed files for vagrant (team's not using it right now); line 9: - docker-registry: needed files for self-host docker-registry; line 10: - rancher: needed compose files for controller stack (rancher))
== nest-api
overall 81 | api=100, architecture=90, blast-radius=None, code-quality=71, data=100, infrastructure=None, operations=None, reliability=100, requirement-fidelity=50, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 69: common/                   cross-cutting, reusable across ≥2 modules; line 70: entities/               shared base entities (BaseEntity: id/createdAt/updatedAt/deletedAt); line 71: enums/                  shared enums (UserRole, UserStatus, ...); line 72: constants/              non-secret default values (DEFAULT_PORT, ...) and ERROR_MESSAGES; line 73: guards/                 HTTP guards (AuthGuard, RolesGuard))
== python-ml
overall 64 | api=75, architecture=83, blast-radius=None, code-quality=77, data=40, infrastructure=None, operations=None, reliability=100, requirement-fidelity=12, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by src/docs/implementation-schedule.md (content: line 50: | 2.0h | Unit tests: write/read, nested paths, `exists`, `append` | `tests/test_vfs.py` |; line 190: | 2.0h | E2E test: START → … → HITL → persist → END (mocked LLM / Tavily) | `tests/test_e2e_happy_path.py` |; line 191: | 1.0h | Test fixtures: temp workspace + checkpointer | `tests/conftest.py` |; line 207: | 2.0h | Integration tests: `write_todos` gate, Tavily research path, partial rerun, happy path (mocked) | `tests/integration/` |; line 208: | 2.0h | **`scripts/ragas_benchmark.py`** — batch N sample queries, aggregate faithfulness scores, CSV/JSON report | `scripts/ragas_benchmark.py` |)
== self
overall 43 | api=0, architecture=100, blast-radius=None, code-quality=31, data=40, infrastructure=None, operations=50, reliability=50, requirement-fidelity=20, security=50, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by tasks/TASK_GUIDE_T001.md (content: line 170: | `pyproject.toml` | New — package metadata, Python 3.11+, deps (`mcp`), `[dev]` extra (pytest), src layout |; line 171: | `src/easy_verifier/__init__.py` | New — version only |; line 172: | `src/easy_verifier/core/models.py` | New — `Excerpt`, `EvidencePack`, `DimensionDescriptor` dataclasses |; line 173: | `src/easy_verifier/core/pipeline.py` | New — `run_dimension()`, the choke point |; line 174: | `src/easy_verifier/core/redact.py` | New — documented passthrough seam with T004's final signature |)
```

**AFTER** (implementer, 2026-10-13, final code incl. the Supervisor-requested H1 fix: a level-1 heading is a title and never opens a prose architecture section; only `##`-`######` do; long lines cut at 1100 chars): overall and every per-dimension rating of all six runs are identical to BEFORE (a `diff` against BEFORE differs only on the two citation lines). fullstack-ts: tasks/TASK_GUIDE_T029.md change-list table -> memory/decisions.md "## Architecture" (accepted by Supervisor). This repo: tasks/TASK_GUIDE_T001.md table -> BRAINSTORMING_LOG.md (a described file list), architecture stays 100, overall 43. node-monorepo, k8s-ops, nest-api, python-ml citations unchanged.

```
== fullstack-ts
overall 56 | api=38, architecture=100, blast-radius=None, code-quality=70, data=70, infrastructure=None, operations=50, reliability=0, requirement-fidelity=60, security=59, solution-fit=None, supply-chain=55, test-strategy=None
  value None | source role 'architecture-doc' is filled by memory/decisions.md (architecture-heading: line 8: **Decision**: The MVP is a monorepo (`/apps/web` React+TS, `/apps/api` NestJS, `/packages/shared` shared DTO/types) with PostgreSQL, custom JWT auth (org/role model), Socket.IO for realtime Task/Comment/Announcement updates, and a nightly cron job materializing recurring Task rows (not virtual/on-the-fly recurrence instances).; line 20: **Files**: `/apps/web/vite.config.ts`, `tasks/TASK_GUIDE_T001.md`, `tasks/TASK_GUIDE_T003.md`, `T007`, `T008`, `T011`, `T012`, `T015`, `T016`, `T018`, `T021`; line 23: **Decision**: The `easy-ui-mcp` server (a sibling repo/container at `<pets>/easy-ui-mcp`, providing the `mcp__easy-ui-mcp__*` browser tools) must run with `network_mode: host` in its `docker-compose.yml`, not a default bridge network with a published
== node-monorepo
overall 59 | api=None, architecture=83, blast-radius=None, code-quality=67, data=40, infrastructure=None, operations=None, reliability=61, requirement-fidelity=None, security=50, solution-fit=None, supply-chain=35, test-strategy=75
  value None | source role 'architecture-doc' is filled by backend/scripts/README.md (content: line 8: - `/common`: contain common scripts.; line 9: - `/companies`: contain scripts to work with `dbcompanies`.; line 10: - `/crunchbase`: contain scripts to work with `dbcrunchbasecompanies`; line 12: - `/similarweb`: contain scripts to work with SimilarWeb data)
== scraping
overall None | api=None, architecture=None, blast-radius=None, code-quality=None, data=None, infrastructure=None, operations=None, reliability=None, requirement-fidelity=None, security=None, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 6: - bin: helper scripts; line 7: - elk: needed scripts and code for elk services; line 8: - vagrant: needed files for vagrant (team's not using it right now); line 9: - docker-registry: needed files for self-host docker-registry; line 10: - rancher: needed compose files for controller stack (rancher))
== nest-api
overall 81 | api=100, architecture=90, blast-radius=None, code-quality=71, data=100, infrastructure=None, operations=None, reliability=100, requirement-fidelity=50, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 69: common/                   cross-cutting, reusable across ≥2 modules; line 70: entities/               shared base entities (BaseEntity: id/createdAt/updatedAt/deletedAt); line 71: enums/                  shared enums (UserRole, UserStatus, ...); line 72: constants/              non-secret default values (DEFAULT_PORT, ...) and ERROR_MESSAGES; line 73: guards/                 HTTP guards (AuthGuard, RolesGuard))
== python-ml
overall 64 | api=75, architecture=83, blast-radius=None, code-quality=77, data=40, infrastructure=None, operations=None, reliability=100, requirement-fidelity=12, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by src/docs/implementation-schedule.md (content: line 50: | 2.0h | Unit tests: write/read, nested paths, `exists`, `append` | `tests/test_vfs.py` |; line 190: | 2.0h | E2E test: START → … → HITL → persist → END (mocked LLM / Tavily) | `tests/test_e2e_happy_path.py` |; line 191: | 1.0h | Test fixtures: temp workspace + checkpointer | `tests/conftest.py` |; line 207: | 2.0h | Integration tests: `write_todos` gate, Tavily research path, partial rerun, happy path (mocked) | `tests/integration/` |; line 208: | 2.0h | **`scripts/ragas_benchmark.py`** — batch N sample queries, aggregate faithfulness scores, CSV/JSON report | `scripts/ragas_benchmark.py` |)
== self
overall 43 | api=0, architecture=100, blast-radius=None, code-quality=31, data=40, infrastructure=None, operations=50, reliability=50, requirement-fidelity=20, security=50, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by BRAINSTORMING_LOG.md (content: line 215: - `src/easy_verifier/core/pipeline.py` — `run_dimension()`; owns redaction, budgeting, coverage; line 216: - `src/easy_verifier/core/context.py` — kit detection, kit-aware vs. standalone loading (FR-001…005); line 217: - `src/easy_verifier/core/scope.py` — task | changes | worktree | project resolution (FR-006…008); line 218: - `src/easy_verifier/core/redact.py` — evidence-layer fingerprinting (NFR-010, DDR-0001); line 219: - `src/easy_verifier/core/budget.py` — relevance ordering, lazy truncation (FR-011a/b))\n```\n\n**DELTA**: A table with a Change/Action/Status-style column no longer counts as an architecture description, and a section headed "Architecture" in any document counts when it names three real paths in prose, so fullstack-ts is no longer credited with a task's edit list.

**WITNESS**: Supervisor re-ran the t096/t089/t001 tests and an H1 sabotage on the branch, 2026-10-13 (event trace T096).
implementing agent alone]
