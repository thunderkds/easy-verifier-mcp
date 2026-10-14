# TASK_GUIDE — T096: A change list is not an architecture description; architecture prose sections count
**Date**: 2026-10-13
**Complexity Level**: C2
**Risk Level**: Medium (changes which document fills `architecture-doc`; architecture reads it)
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `tasks/TASK_GUIDE_T089.md` (merged; this refines its architecture-doc shape) and `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (local; read it from the main checkout)

---

## Requirement (Pillar 1 — Adapt the requirement)

The KANBAN follow-up from T089 found that on kitchd, and on this repo, `architecture-doc` is filled by a task guide's **Files to Change** table. The kitchd citation is `tasks/TASK_GUIDE_T029.md`: `| apps/web/src/App.tsx | Mount <ErrorDialogProvider> |`.

The table names real paths followed by ≥ `MIN_DESCRIPTION_WORDS` words. That makes it a "described entry" (`core/documents.py` `_table_entry`). It also lists many directories, so it wins the T089 "most distinct directories" ranking. But it is a **plan of edits**, not a description of the system.

Meanwhile kitchd's real architecture description is prose: `PROJECT_SPEC.md` "## Architecture Summary" names `/apps/api`, `/apps/web` and `/packages/shared` inline. That prose never qualifies, because only list items, tree lines and table rows are entries.

**Restated intent** (Supervisor decision 2026-10-13; this changes citations only, see AC 6):
> 1. **Change-list tables are not descriptions.** A table whose header row has a column titled as a change or plan column is not a source of described entries. The titles are `Change`, `Changes`, `Action`, `Edit`, `Modification`, `Status`, `Todo`, `Reason`, matched case-insensitively. `Reason` covers "Files Must NOT Touch". The list is a module constant with a one-line rationale. Tables without such a column behave as now.
> 2. **Architecture prose sections count.** In any candidate document (not only a README, as T089 had), a section under a heading matching the existing `ARCHITECTURE_HEADING` qualifies when it names ≥ `MIN_DESCRIBED_ENTRIES` distinct real paths in prose (inline code or bare path tokens that resolve through `_resolve`). Leading `/` is stripped, as `normalize_path` already does. The kind is `KIND_README_HEADING` renamed or generalised to an "architecture-heading" kind; keep the payload's kind string stable for READMEs. Its size for ranking is the distinct directories those paths name.
> 3. Ranking stays T089's: most distinct directories, then entries, then scan priority.

**Out of scope**:
- decision-record and requirements-doc shapes;
- new rating rules or weights;
- recognising architecture from diagrams (images, mermaid).

**Requirement Refs**: FR-076, DDR-0012.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user "yes" 2026-10-13 to continue with the follow-ups; the specific rule is a Supervisor decision under "ask only score-affecting confusion": AC 6 pins the score)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T089 (merged)

**Entry point**: `core/documents.py` `scan_document_roles` → `_scan_role` → `_shape`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | A table with header `\| File \| Change \|` and 5 rows naming real files in 4 directories yields 0 described entries; the same rows under `\| File \| Purpose \|` yield 5 | change list |
| 2 | Header matching is case-insensitive and cell-trimmed (`\| **Change** \|`); a header row is the row directly above the `\|---\|` separator | change list |
| 3 | A `## Architecture Summary` prose paragraph naming `` `/apps/api` ``, `` `/apps/web` ``, `` `/packages/shared` `` (all existing) in `PROJECT_SPEC.md` fills `architecture-doc`, citing the section's lines; the same paragraph under `## Notes` does not | prose section |
| 4 | Prose naming only 2 real paths, or 3 paths of which one does not exist, does not qualify | threshold |
| 5 | A README with an "Architecture" section keeps exactly today's kind string and cited lines (bryony and scraping-devops citations unchanged) | no regression |
| 6 | kitchd: `architecture-doc` is filled by `PROJECT_SPEC.md` (or by another document whose cited lines are a real description, never a change list; paste the citation). kitchd architecture rating stays 100 and overall stays 56. bryony (59/83), scraping-devops, coffee-shop-api (81/90) and ai-training (60/83) keep their ratings. Paste before/after `architecture-doc` citations for all 5 repos and this repo | real-repo goal |
| 7 | Existing T089 tests pass with expectations unedited, except any test that pinned a change-list table as an architecture doc, which is listed with its reason | no regression |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | AC 1–5 fixtures | as stated | automated tests |
| 2 | kitchd | PROJECT_SPEC.md cited; ratings unchanged | real-repo run (background) |
| 3 | other repos | citations/ratings unchanged or justified | real-repo run (background) |

### Verification Command (exact, runnable)

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T096.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T096.md`.

BEFORE commands (before any code change; paste timestamped output): for the five real repos and this repo, run `--scope project </dev/null` and extract the `architecture-doc` derivation, plus the overall and architecture ratings (in the background).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

Same as `tasks/TASK_GUIDE_T094.md` "Real repos".

---

## Approach

Make the smallest change in `core/documents.py`:
- `described_entries` tracks the current table's header row and skips the table when the header is a change list.
- `_shape(ARCHITECTURE_DOC)` checks the architecture-heading section in any document, using a prose path scan that reuses `_TOKEN` and `_resolve`.

---

## Edge Case Checklist

- [ ] Table without a separator row (not a GFM table) → treated as today
- [ ] Two tables in one document; only the change-list one is skipped
- [ ] Architecture heading at any level (`#`–`######`); the section ends at the next same-or-higher heading (`_section_at`)
- [ ] Prose paths inside a fenced code block in the section still count once each
- [ ] URLs (`https://…/apps/api`) are not paths

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/documents.py` | change-list tables skipped; architecture prose section |
| `tests/test_t096_architecture_doc_shape.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `core/roles.py` | T094 in parallel |
| `core/redact.py` | T095 in parallel |
| `core/judge.py` weights | no rating change |

---

## Test Plan

Fixture tests for AC 1–5, the T089 suite, and real-repo citations for AC 6.

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T096.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
