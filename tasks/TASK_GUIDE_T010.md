# TASK_GUIDE — T010: blast-radius dimension (bespoke)
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2** — apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md` — it is itself a blast-radius artifact and a useful model for this dimension's output

> **Naming note**: this dimension is *code-dependency* blast radius — what else a change could break.
> It is **not** the kit's `blast-radius` **skill**, which analyses data-breach impact. Do not
> implement the skill's behaviour here.

---

## Requirement (Pillar 1 — Adapt the requirement)

Gather evidence about what a change can reach, so the calling agent can judge how far its
consequences travel.

**Restated intent**:
> The `blast-radius` dimension returns citable evidence about the reach of the files in the active
> scope — who imports or references them, which entry points sit downstream, and which files git
> history shows change alongside them. It surfaces the reachable set; it does not rate the risk.

**Out of scope**:
- Data-breach impact analysis (that is the kit's `blast-radius` skill).
- Risk scoring, severity, or a "this change is dangerous" verdict (FR-013).
- Full static analysis or type resolution — reference evidence, not a compiler.

**Requirement Refs**:
- FR-010: `blast-radius`, 1 of 7
- FR-011: structured pack — files read, citable excerpts, miss list
- FR-013: evidence only, no verdict
- FR-006/FR-008: scope-driven; `changes` scope is its primary use
- FR-016: declared `sources_sought`
- NFR-007: never execute target-repo code

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-08-24)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary — "scope", "excerpt", "sources_sought"/"miss list" used as the kit defines them; the guide's naming note correctly separates *code-dependency* blast radius from the kit's data-breach `blast-radius` **skill**
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above — verified by grep: FR-003/004/006/008/009/010/011/013/016/016a and NFR-002/007/009/012 all present

> **Gate defect found at sign-off, not blocking**: the Verification Command below reads
> `--range HEAD~1..HEAD`, but the CLI's flag for `changes` scope is `--ref` (`--ref REF`, per
> `easy-verifier --help`). The command as written fails with an unrecognized-argument error. Use
> `--ref HEAD~1..HEAD` and correct the guide in passing.

---

## Dependencies & Reachability

**Depends on**: T003 — `Scope` supplies the changed-file set this dimension expands from; T005 — `budget()` for lazy bounded output.

**Entry point**: `collect` (in `dimensions/blast_radius.py`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Ships as a descriptor + `collect`, **bespoke** — does not import `_doc_extract` | FR-009, Constraint 8 |
| 2 | For each file in the active scope, surfaces referencing files with citable path + line evidence for the reference itself | FR-011 |
| 3 | Surfaces git-history co-change evidence (files historically committed alongside the scope files), derived from local git only | FR-008, NFR-012 |
| 4 | Identifies downstream entry points (CLI entries, route definitions, exported public API, `__init__` re-exports) where discoverable, and lists what it looked for but did not find | FR-011, FR-016a |
| 5 | Reference discovery is **textual and honest**: it may over-report (same-named symbols) but must state its method, and must never claim a resolved import graph it did not compute | NFR-002 |
| 6 | No risk score, severity, danger rating or verdict field | FR-013 |
| 7 | `project` scope produces a meaningful pack (repo-wide hotspots) rather than an error | FR-006 |
| 8 | `collect` returns a lazily-consumed `Iterable[Excerpt]` — critical here, since the naive implementation greps the whole repo per scope file | Critical Constraint 3, NFR-009 |
| 9 | Works in standalone mode with the limited-context warning | FR-003, FR-004 |
| 10 | Executes nothing from the target repo; git calls are read-only and contact no remote | NFR-007, NFR-012 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Temp repo where `b.py` and `c.py` both import `a.py`, scope = `a.py` | Both referencing files surfaced with the citing line | automated test |
| 2 | This repo, `changes` scope over the last commit | Referencing files and co-change evidence present, bounded by the budget | automated test |
| 3 | Scope file that nothing references | Valid pack stating zero referencing files found — not an empty pack implying it was not checked | automated test |
| 4 | A repo with 5,000 files under a small budget | Terminates promptly, `truncated=True`, generator not fully consumed | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t010_blast_radius.py -q && \
  python -m easy_verifier.adapters.cli blast-radius --repo . --scope changes --ref HEAD~1..HEAD | head -30
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T010.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T010.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/security.py` (T008) for bespoke structure; `memory/codebase-map.md` and the `map-codebase` skill for the co-change/hotspot technique, which is already proven in this kit.

Two evidence sources, deliberately cheap: **textual reference search** (module name, file stem,
exported symbol names) and **git co-change history** (`git log --name-only` over the scope files,
counting co-occurrence). Neither requires parsing or executing the target's code, which is what
keeps this dimension usable on arbitrary repos in any language — a real import-graph resolver would
be per-ecosystem, enormous, and would still fail on the dynamic cases.

Over-reporting is acceptable here, silence is not; but AC #5 requires the method be stated so the
reviewing agent knows it is reading textual matches rather than a resolved graph, and can calibrate
accordingly. That admission *is* the product.

AC #8 deserves care: the obvious implementation is O(scope files × repo files) and eagerly builds
the whole result before the budget sees it. Yield per match instead, and let `budget()` stop the
work.

---

## Edge Case Checklist

- [ ] Scope file that nothing references → explicit zero, not an empty pack (AC #3)
- [ ] Very common file stem (`utils.py`, `index.js`) → floods matches; budget must contain it and the truncation must be honest
- [ ] Renamed file in the diff → co-change history across the rename (`git log --follow`) or an admitted limitation
- [ ] Deleted file in scope → referencing files are the *interesting* result; do not skip deleted files
- [ ] Repo with no git history (or a single commit) → co-change evidence absent, listed in the miss list, textual references still work
- [ ] Shallow clone → history-derived evidence is partial; say so rather than reporting a small number as fact
- [ ] Binary files matching a text search → excluded
- [ ] `node_modules` / `.venv` / vendored trees → excluded, or every match is third-party noise
- [ ] Self-reference (a file importing itself, or matching its own definition line) → excluded from its own reference list
- [ ] Case-insensitive filesystems producing duplicate paths
- [ ] Symbol names that are English words (`test`, `main`, `run`) → will over-match; bounded and method-stated
- [ ] `project` scope, where "the changed set" is the whole repo → must not attempt every-file-against-every-file

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/blast_radius.py` | New — bespoke descriptor + `collect` |
| `tests/test_t010_blast_radius.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/dimensions/_doc_extract.py` | Owned by T007, capped at four callers |
| `src/easy_verifier/core/scope.py` | Owned by T003 — consume it, do not edit |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t010_blast_radius.py` — temp repos with known reference graphs for the correspondence
cases, a generated large repo for AC #4's termination test, and this repo (real git history) for the
co-change path. Include the AC #8 laziness assertion with an instrumented generator, matching T005's
technique; without it, a fully-eager implementation passes every other test in this file.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T010.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
