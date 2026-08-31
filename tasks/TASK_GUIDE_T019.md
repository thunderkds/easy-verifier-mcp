# TASK_GUIDE — T019: `core/metrics.py` — measured facts computed over the evidence pack
**Date**: 2026-08-26
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` — especially Critical Constraints 1, 1a and 1b, and the Domain Glossary entries **Metric**, **Rating**, **Coverage score**
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Read `docs/ddr/0003-abstain-from-rating-below-coverage-floor.md` — this task implements item 5 of its Decision
6. C2: read `memory/codebase-map.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

The user's request (2026-08-26):

> "wanna make sure my input will be the source code, or the feature as can be, the verifier will run
> through and output the analytics score and number to identify the quality of the verify things."

This task builds the **measured facts** half of that. It does not score anything.

**Restated intent**:
> `core/metrics.py` computes measured, citable facts about the target — test strength, security
> surface, evidence coverage, and code shape — **exclusively from the evidence pack a dimension
> already produced**. Each metric carries the file references it was computed from, and each
> declares whether it is whole-set-dependent or evidence-local, so a metric over a truncated pack
> abstains rather than lying about the repository.

**Out of scope**:
- Any rating, threshold, weighting or judgment — that is T020. A metric is a fact, never an opinion.
- Reading any file. Metrics see the pack, nothing else (see AC #2 — this is structural, not a rule).
- Adding a callable to the dimension descriptors. Descriptors stay `sources_sought` + `collect`.

**Requirement Refs**:
- FR-027: metrics computed exclusively from the evidence pack; every number cites its evidence
- FR-027a: whole-set-dependent vs. evidence-local; whole-set metrics abstain on a truncated pack
- NFR-001 / Critical Constraint 1a: arithmetic only, no inference

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary — **Metric** is the term; do not write "score"
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T012 — `combined_pack()` supplies the multi-dimension input; all seven dimensions ship.

**Entry point**: `compute_metrics`
> Called by `judge.rate()` in T020 and surfaced through the `score` operation in T022. This task
> ships it unreachable from an adapter by design — T022 owns that wiring — which is a **known and
> accepted** reachability gap, unlike T013's, because the consumer task is already scheduled.

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `compute_metrics(pack)` returns a `MetricSet` of individual `Metric` values, each carrying `name`, `value` **or** an abstention, `kind` (`whole_set` / `evidence_local`), and `computed_from` — the file refs it was derived from | FR-027 |
| 2 | The module imports nothing that reads the filesystem — no `open`, no `Path.read_*`, no `RepoContext`. Asserted **structurally** by a test over the module's imports and AST, not by convention | FR-027 |
| 3 | The four families ship: **test strength**, **security surface**, **evidence coverage**, **code shape** | FR-027, user selection 2026-08-26 |
| 4 | Every `whole_set` metric abstains when `pack.truncation` reports truncation, naming the omitted count as a **lower bound** ("≥40 items omitted") | FR-027a |
| 5 | Every `evidence_local` metric still computes over a truncated pack, because its truth does not depend on what else was read | FR-027a |
| 6 | An abstention is a **distinct type**, not `0`, `None`, or a sentinel number. A consumer cannot obtain a numeric value from an abstaining metric without explicitly handling the abstention | FR-027a, Constraint 1b |
| 7 | `computed_from` is non-empty for every non-abstaining metric, and every ref in it appears in `pack.files_read` or `pack.excerpts` — a metric cannot cite what the pack never read | FR-027 |
| 8 | **Test strength** measures whether assertions can distinguish correct from broken code, not merely that test files exist: at minimum, test-to-source ratio, modules with zero covering test, and assertion density per test | user direction 2026-08-26 |
| 9 | Metrics are deterministic — the same pack yields byte-identical metrics across runs and processes | FR-022 |
| 10 | Every metric value is recomputable by hand from the pack contents printed beside it | Constraint 1a |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | A complete, untruncated pack from `test-strategy` on this repo | All four families produce values; each cites refs present in the pack | automated test |
| 2 | The same pack with `truncation.truncated=True` | Every `whole_set` metric abstains naming the lower-bound omitted count; every `evidence_local` metric still computes | automated test |
| 3 | A pack with `files_read=[]` and no excerpts | Every metric abstains or reports an honest zero-with-citation; **no metric raises** | automated test |
| 4 | A fabricated metric implementation citing a path absent from the pack | AC #7's test **fails** — the citation guard is real, not decorative | automated test (negative) |
| 5 | Two runs over the same pack in separate processes | Byte-identical serialized metrics | automated test |

### Verification Command (exact, runnable)

```bash
cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_metrics.py -q
```

---

## Approach

**Pattern reference**: `src/easy_verifier/core/synthesis.py` — a pure module that consumes packs and
does arithmetic over them, raising nothing into the pipeline and owning no I/O. Imitate its shape,
its docstring discipline about what it may not do, and its dataclass style.

Model the abstention on `CoverageSummary`'s DDR-0004 lesson: put the *reason* **inside** the value
object, so a renderer cannot reach a number without also reaching why it might be absent. That
structural guarantee is necessary but — per T013's Stage 4 P1 — **not sufficient**; AC #6 must be
tested at the consumer boundary too, not only asserted about the dataclass.

Keep the metric definitions as declared data where you can, so T020's rules can reference metrics by
name without importing implementation.

---

## Edge Case Checklist

- [ ] A pack whose dimension **failed** (`slot.pack is None`) — metrics must not be invented for it
- [ ] `omitted_count` is a **lower bound**, never a count. Never phrase an abstention as if it were exact
- [ ] A repo with tests but no source, and source but no tests — ratio denominators of zero
- [ ] A pack that is untruncated but empty (a legitimately empty scope) vs. one that is truncated to empty
- [ ] `coverage_score is None` (the dimension sought nothing) vs. `0.0` (it sought and found nothing) — these are different and must not collapse
- [ ] A file counted twice — `files_read` is known to duplicate 2× on a default invocation (T009/T010 residue). A metric that counts files **must** dedupe or it silently doubles

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | New. `Metric`, `MetricAbstention`, `MetricSet`, `compute_metrics()` |
| `tests/test_metrics.py` | New. Including the structural no-I/O test and the negative citation test |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/dimensions/*.py` | Descriptors stay `sources_sought` + `collect`. Adding a third field is the rejected Option B from grilling |
| `src/easy_verifier/core/pipeline.py` | The choke point is not this task's to change; metrics run after it |
| `src/easy_verifier/core/models.py` | Pack schema is locked (DDR-0004). Metrics are a new type in a new module |

---

## Test Plan

Unit tests over hand-built packs — do **not** build fixtures by running the real pipeline, or the
test becomes a test of the dimensions. Per this project's most persistent defect: for every metric,
**hardwire the predicate it depends on to both extremes and re-run**. A test that passes with
`truncated=True` and `truncated=False` is pinning nothing, and this project has shipped that exact
green-test-that-cannot-fail five times (T005, T008, T010, T018).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk — no new filesystem, subprocess or network primitive; state so explicitly in the review file)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T019.md`'s Evidence table
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated
- [ ] Supervisor notified: task ready for Stage 4 review
