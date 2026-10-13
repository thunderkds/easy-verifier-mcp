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
| Verification command run | ☐ pass / ☐ fail | (implementer) full suite: 3 failed, 2768 passed, 2 skipped in 486s; ruff check src tests: All checks passed. The 3 failures: two container tests (stale Docker image, missing=['api','data','infrastructure','operations','supply-chain'], known and unrelated) and tests/test_t001_pipeline.py::test_architecture_pack_against_this_repo, which pinned kind == "content"; edited to accept "architecture-heading" too (reason: this repo's role is now filled by prose); rerun green (123 passed across t001/t089/t096) |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (implementer, captured 2026-10-13T10:37:15Z-10:38:28Z UTC, before any implementation commit; unmodified worktree HEAD eb81c9c; command per repo, run in background: `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project </dev/null`; ai-training = /home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training, found in memory/event-trace/T037.jsonl, not in learnings.md; "self" = this worktree; scraping-devops abstains in every dimension):

```
== kitchd
overall 56 | api=38, architecture=100, blast-radius=None, code-quality=70, data=70, infrastructure=None, operations=50, reliability=0, requirement-fidelity=60, security=59, solution-fit=None, supply-chain=55, test-strategy=None
  value None | source role 'architecture-doc' is filled by tasks/TASK_GUIDE_T029.md (content: line 163: | `apps/web/src/App.tsx` | Mount `<ErrorDialogProvider>` |; line 164: | `apps/web/src/features/tasks/api.ts` | Call `notifyApiError()` in error branch |; line 165: | `apps/web/src/features/team/api.ts` | Call `notifyApiError()` in error branch |; line 166: | `apps/web/src/features/notes/api.ts` | Call `notifyApiError()` in error branch |; line 167: | `apps/web/src/components/LowStockWidget/api.ts` | Call `notifyApiError()` in error branch |)
== bryony
overall 59 | api=None, architecture=83, blast-radius=None, code-quality=67, data=40, infrastructure=None, operations=None, reliability=61, requirement-fidelity=None, security=50, solution-fit=None, supply-chain=35, test-strategy=75
  value None | source role 'architecture-doc' is filled by backend/scripts/README.md (content: line 8: - `/common`: contain common scripts.; line 9: - `/companies`: contain scripts to work with `dbcompanies`.; line 10: - `/crunchbase`: contain scripts to work with `dbcrunchbasecompanies`; line 12: - `/similarweb`: contain scripts to work with SimilarWeb data)
== scraping
overall None | api=None, architecture=None, blast-radius=None, code-quality=None, data=None, infrastructure=None, operations=None, reliability=None, requirement-fidelity=None, security=None, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 6: - bin: helper scripts; line 7: - elk: needed scripts and code for elk services; line 8: - vagrant: needed files for vagrant (team's not using it right now); line 9: - docker-registry: needed files for self-host docker-registry; line 10: - rancher: needed compose files for controller stack (rancher))
== coffee
overall 81 | api=100, architecture=90, blast-radius=None, code-quality=71, data=100, infrastructure=None, operations=None, reliability=100, requirement-fidelity=50, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 69: common/                   cross-cutting, reusable across ≥2 modules; line 70: entities/               shared base entities (BaseEntity: id/createdAt/updatedAt/deletedAt); line 71: enums/                  shared enums (UserRole, UserStatus, ...); line 72: constants/              non-secret default values (DEFAULT_PORT, ...) and ERROR_MESSAGES; line 73: guards/                 HTTP guards (AuthGuard, RolesGuard))
== aitraining
overall 64 | api=75, architecture=83, blast-radius=None, code-quality=77, data=40, infrastructure=None, operations=None, reliability=100, requirement-fidelity=12, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by src/docs/implementation-schedule.md (content: line 50: | 2.0h | Unit tests: write/read, nested paths, `exists`, `append` | `tests/test_vfs.py` |; line 190: | 2.0h | E2E test: START → … → HITL → persist → END (mocked LLM / Tavily) | `tests/test_e2e_happy_path.py` |; line 191: | 1.0h | Test fixtures: temp workspace + checkpointer | `tests/conftest.py` |; line 207: | 2.0h | Integration tests: `write_todos` gate, Tavily research path, partial rerun, happy path (mocked) | `tests/integration/` |; line 208: | 2.0h | **`scripts/ragas_benchmark.py`** — batch N sample queries, aggregate faithfulness scores, CSV/JSON report | `scripts/ragas_benchmark.py` |)
== self
overall 43 | api=0, architecture=100, blast-radius=None, code-quality=31, data=40, infrastructure=None, operations=50, reliability=50, requirement-fidelity=20, security=50, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by tasks/TASK_GUIDE_T001.md (content: line 170: | `pyproject.toml` | New — package metadata, Python 3.11+, deps (`mcp`), `[dev]` extra (pytest), src layout |; line 171: | `src/easy_verifier/__init__.py` | New — version only |; line 172: | `src/easy_verifier/core/models.py` | New — `Excerpt`, `EvidencePack`, `DimensionDescriptor` dataclasses |; line 173: | `src/easy_verifier/core/pipeline.py` | New — `run_dimension()`, the choke point |; line 174: | `src/easy_verifier/core/redact.py` | New — documented passthrough seam with T004's final signature |)
```

**AFTER** (implementer, 2026-10-13 same command and repos, worktree code with the T096 change; long citation lines cut at 1100 chars): overall and every per-dimension rating of all six runs are identical to BEFORE (a `diff` of the two summaries differs only on the two citation lines below). Changed citations: kitchd (tasks/TASK_GUIDE_T029.md change-list table -> memory/decisions.md "## Architecture" prose section) and this repo (tasks/TASK_GUIDE_T001.md "Files to Change" table -> tasks/TASK_GUIDE_T001.md H1-title prose section; see Notes). bryony, scraping-devops, coffee-shop-api and ai-training citations unchanged.

```
== kitchd
overall 56 | api=38, architecture=100, blast-radius=None, code-quality=70, data=70, infrastructure=None, operations=50, reliability=0, requirement-fidelity=60, security=59, solution-fit=None, supply-chain=55, test-strategy=None
  value None | source role 'architecture-doc' is filled by memory/decisions.md (architecture-heading: line 8: **Decision**: KitchenOS MVP is a monorepo (`/apps/web` React+TS, `/apps/api` NestJS, `/packages/shared` shared DTO/types) with PostgreSQL, custom JWT auth (org/role model), Socket.IO for realtime Task/Comment/Announcement updates, and a nightly cron job materializing recurring Task rows (not virtual/on-the-fly recurrence instances).; line 20: **Files**: `/apps/web/vite.config.ts`, `tasks/TASK_GUIDE_T001.md`, `tasks/TASK_GUIDE_T003.md`, `T007`, `T008`, `T011`, `T012`, `T015`, `T016`, `T018`, `T021`; line 23: **Decision**: The `easy-ui-mcp` server (a sibling repo/container at `/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-ui-mcp`, providing the `mcp__easy-ui-mcp__*` browser tools) must run with `network_mode: host` in its `docker-compose.yml`, not a default bridge network with a published
== bryony
overall 59 | api=None, architecture=83, blast-radius=None, code-quality=67, data=40, infrastructure=None, operations=None, reliability=61, requirement-fidelity=None, security=50, solution-fit=None, supply-chain=35, test-strategy=75
  value None | source role 'architecture-doc' is filled by backend/scripts/README.md (content: line 8: - `/common`: contain common scripts.; line 9: - `/companies`: contain scripts to work with `dbcompanies`.; line 10: - `/crunchbase`: contain scripts to work with `dbcrunchbasecompanies`; line 12: - `/similarweb`: contain scripts to work with SimilarWeb data)
== scraping
overall None | api=None, architecture=None, blast-radius=None, code-quality=None, data=None, infrastructure=None, operations=None, reliability=None, requirement-fidelity=None, security=None, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 6: - bin: helper scripts; line 7: - elk: needed scripts and code for elk services; line 8: - vagrant: needed files for vagrant (team's not using it right now); line 9: - docker-registry: needed files for self-host docker-registry; line 10: - rancher: needed compose files for controller stack (rancher))
== coffee
overall 81 | api=100, architecture=90, blast-radius=None, code-quality=71, data=100, infrastructure=None, operations=None, reliability=100, requirement-fidelity=50, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by README.md (content: line 69: common/                   cross-cutting, reusable across ≥2 modules; line 70: entities/               shared base entities (BaseEntity: id/createdAt/updatedAt/deletedAt); line 71: enums/                  shared enums (UserRole, UserStatus, ...); line 72: constants/              non-secret default values (DEFAULT_PORT, ...) and ERROR_MESSAGES; line 73: guards/                 HTTP guards (AuthGuard, RolesGuard))
== aitraining
overall 64 | api=75, architecture=83, blast-radius=None, code-quality=77, data=40, infrastructure=None, operations=None, reliability=100, requirement-fidelity=12, security=59, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by src/docs/implementation-schedule.md (content: line 50: | 2.0h | Unit tests: write/read, nested paths, `exists`, `append` | `tests/test_vfs.py` |; line 190: | 2.0h | E2E test: START → … → HITL → persist → END (mocked LLM / Tavily) | `tests/test_e2e_happy_path.py` |; line 191: | 1.0h | Test fixtures: temp workspace + checkpointer | `tests/conftest.py` |; line 207: | 2.0h | Integration tests: `write_todos` gate, Tavily research path, partial rerun, happy path (mocked) | `tests/integration/` |; line 208: | 2.0h | **`scripts/ragas_benchmark.py`** — batch N sample queries, aggregate faithfulness scores, CSV/JSON report | `scripts/ragas_benchmark.py` |)
== self
overall 43 | api=0, architecture=100, blast-radius=None, code-quality=31, data=40, infrastructure=None, operations=50, reliability=50, requirement-fidelity=20, security=50, solution-fit=None, supply-chain=None, test-strategy=None
  value None | source role 'architecture-doc' is filled by tasks/TASK_GUIDE_T001.md (architecture-heading: line 14: 1. Read `PROJECT_SPEC.md`; line 15: 2. Read `memory/MEMORY.md`; line 19: 6. **C2** — read `memory/codebase-map.md` (baseline snapshot; the repo has no product code yet, so expect it to be near-empty); line 21: Also read `BRAINSTORMING_LOG.md` § Option D — this task implements that decision literally.; line 61: - [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above)
```

**DELTA**: A table with a Change/Action/Status-style column no longer counts as an architecture description, and a section headed "Architecture" in any document counts when it names three real paths in prose, so kitchd is no longer credited with a task's edit list.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T096.jsonl`, never the
implementing agent alone]
