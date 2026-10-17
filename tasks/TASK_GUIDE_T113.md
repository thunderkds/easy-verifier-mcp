# TASK_GUIDE — T113: One full code scan per run; code metrics over whole files
**Date**: 2026-10-17
**Complexity Level**: C3
**Risk Level**: Medium (moves project-scope ratings on every repo; touches the shared read path)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, `memory/MEMORY.md`, this file, `.claude/agents/backend.md`
2. Apply the C3 process (general-agent-template Complexity matrix)
3. Read `PRD.md` FR-085 (added with this guide), NFR-001, FR-022, FR-062; DDR-0010 (batches)
4. Read the existing whole-file path: `core/context.py` `whole_file_excerpt`, `dimensions/data.py` /
   `api.py` / `infrastructure.py` (`context.whole_file`, the T045/T075/T076 pattern), `core/batches.py`
   (purpose-class + churn order, `--all`), `core/budget.py` (byte budget, tiers), `core/metrics.py`
   (`WHOLE_SET` vs `EVIDENCE_LOCAL`, the "whole-set-dependent: the byte budget truncated this pack"
   abstention)

---

## Requirement (Pillar 1)

User, 2026-10-17, after the `node-api` run: *"I dont see you scan the code base. just
refer the docs, and the code that related to your checking points. Not all, so the point for the blast
radius is not good at all."* → Supervisor proposal "one full code scan per run … metrics on whole
files … blast-radius at project scope", user: *"looks good, let spawn"*. Tokens: the scan is local
(no model, NFR-001); only metrics, refs and a few excerpts reach the agent.

**Restated intent**:
> Today each dimension reads only files matching its roles, then the byte budget clips them; on
> node-api test-strategy matched 110 test files, read 50, and abstained on "byte budget truncated",
> and code metrics describe a sample. Build **one repository code index per run**: every source and
> test file (registry code kinds, `.gitignore`/third-party exclusions and secret handling as today)
> read **once**, shared by all dimensions. **Code metrics that today are `WHOLE_SET`** (test ↔ source
> correspondence and ratio, assertion density, tests without assertions, skipped tests, CCN,
> import cycles, layer violations, type escapes, TODO share, sink/reliability scans) are computed
> over the index, never over budget-clipped excerpts. The byte budget then governs **only the
> excerpts sent to the agent**. Caps are **deterministic** (no wall clock — replay must stay
> byte-equal): at most `MAX_INDEX_FILES = 5000` code files and `MAX_INDEX_BYTES = 50 MB`, files over
> `MAX_INDEX_FILE_BYTES = 1 MB` skipped; order = `batches` order (purpose class, churn, path);
> anything cut is disclosed in the payload's `capped` list and the affected metrics say "lower
> bound" / abstain as they do today when evidence is partial.

**Out of scope**: blast-radius project-scope rules (T114), new rules or thresholds, model calls,
changing which documents/config roles are read.

**Requirement Refs**: FR-085 (new), FR-062, FR-022, NFR-001, US-006.

### Requirement Fidelity Gate
- [x] Restated intent confirmed (user 2026-10-17 "looks good, let spawn")
- [x] Domain terms align with `PROJECT_SPEC.md`
- [x] Every AC traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T112
**Entry point**: `score_repository` (CLI/MCP `score`, `write_report`) at every scope

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | A single index module builds the code-file set once per `score` call (count reads: each code file opened at most once per run, asserted by a test that counts `read_source` / file opens) |
| 2 | Every metric listed in the Restated intent is computed from the index; none abstains with "the byte budget truncated this pack" when the index is complete — test on a synthetic repo whose code exceeds the byte budget |
| 3 | Caps are deterministic and disclosed: a synthetic repo over `MAX_INDEX_FILES` gives `capped: [{dimension:"index", role:"code", matched, read}]` and the same payload twice (byte-equal) |
| 4 | Narrow scopes (`changes`/`worktree`/`task`) keep measuring only the scope's files (T107 behaviour) but read them through the index; T107–T112 tests green |
| 5 | Excerpts in packs still respect the byte budget; the MCP payload size for this repo at project scope does not grow by more than 10 % versus `develop` (sizes pasted) |
| 6 | Secret handling and redaction unchanged: T029/T100 guards and redaction tests green; secret-classified files never enter the index text |
| 7 | **Real repos, pre-registered** (write expectations first; background, one at a time): node-api (test-strategy now rates; was "30 % of rule weight measured"), fullstack-ts (code-quality/test-strategy no longer abstain on byte-budget truncation — the old 💡 backlog item), node-monorepo, python-ml, nest-api. Paste old → new for every dimension and the run time of each |
| 8 | Run time on node-monorepo (largest) stated; if over 2× `develop`, report it before optimising |
| 9 | Changed expectations in existing tests listed and justified one by one in TASK_REVIEW (authorised only where the old value came from budget truncation) |
| 10 | `tests/test_t113_code_index.py` covers AC1–AC6 on synthetic repos |

---

## Evaluation & Acceptance

```bash
PYTHONPATH=src:<main>/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest -q tests/test_t113_code_index.py
# full suite in background; read the exit code directly
/usr/bin/python3.12 -m ruff check src tests
```
Known env failures (also on develop): T014 `test_module_import_emits_nothing_to_stdout`, 3 T101 HTTP tests (`No module named 'mcp'`).

### Evidence
> **Moved.** `tasks/TASK_REVIEW_T113.md`.

## Demonstration
> **Moved.** `tasks/TASK_REVIEW_T113.md`. BEFORE = node-api project score: test-strategy
> "only 30% of its rule weight was measured", `capped` test-file 110→50.

## UI / Design Acceptance Criteria
> N/A — backend. All three UI Evidence rows ☐ N/A.

---

## Approach

**Pattern reference**: the T045/T075/T076 `context.whole_file` path — generalise it into one shared
index rather than adding a per-dimension read loop. Port the hardening of the existing walk
(`roles` walk / `context._walk`: symlink containment, third-party exclusion, secret classification) —
do not write a new walker.

1. BEFORE capture. 2. Index + read-once test (AC1). 3. Move metrics to the index one family at a time,
test-first (AC2). 4. Caps + disclosure (AC3). 5. Narrow scopes (AC4). 6. Size check (AC5).
7. Real repos (AC7–8).

## Edge Case Checklist
- [ ] Binary / minified / generated files (existing exclusions) stay out
- [ ] File unreadable or not UTF-8 → skipped and counted, not a crash
- [ ] Monorepo project boundaries unchanged for correspondence
- [ ] A metric that was `EVIDENCE_LOCAL` stays evidence-local (only `WHOLE_SET` metrics move)

## Files to Change (Predicted)
| File | Change |
|------|--------|
| `src/easy_verifier/core/index.py` (new) or `core/context.py` | the shared code index |
| `core/metrics.py`, `core/budget.py`, `core/pipeline.py` | metrics read the index; budget only for excerpts |
| `dimensions/test_strategy.py`, `code_quality.py`, `architecture.py`, `security.py`, `reliability.py` | use the index |
| `tests/test_t113_code_index.py` | new |

## Files Must NOT Touch
| File | Reason |
|------|--------|
| `core/judge.py` thresholds/weights | no rule changes |
| `dimensions/blast_radius.py` rules | T114 |

## Completion Checklist
- [ ] Committed on `feat/T113-code-index` (commit WIP early — the step-limit hook stops at 90 calls)
- [ ] AC7 expectations written before the runs
- [ ] T100 guard green
- [ ] Supervisor notified
