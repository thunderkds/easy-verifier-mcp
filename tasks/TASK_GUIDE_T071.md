# TASK_GUIDE — T071: Evaluation docs — EVALUATION_GUIDE.md, README "Reading a report", SCORING_FLOW interpretation
**Date**: 2026-10-04
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C1 process from `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User brief (2026-10-04, approved plan): docs must answer "how do I evaluate / act on a score?" README gets
a short "Reading a report / Interpreting a score" section; SCORING_FLOW.md expands the improvement-plan
and evidence-warnings sections with interpretation guidance; a new short `docs/EVALUATION_GUIDE.md` is
the single place an agent or human goes when they receive a ScoreResult or HTML report. Precise,
philosophy-aligned, no marketing.

**Restated intent**:
> One guide (plus pointers) that tells a reader exactly what each part of a score or report means, when
> to trust a number, and how to act on it — consistent with the code as merged (T065–T070).

**Out of scope**: code changes; changing any rule, weight, threshold or behaviour; marketing copy.

**Requirement Refs**:
- FR-066.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (user "yes, go ahead", 2026-10-04)
- [x] Domain terms align with the glossary and code names
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T070 — report structure the guide describes
**Entry point**: `docs/EVALUATION_GUIDE.md`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|----------------------|-----------|
| 1 | `docs/EVALUATION_GUIDE.md` exists (force-added; `docs/` is gitignored) and covers: overall (mean of rated dimensions, abstentions excluded, contributor disclosure); when to trust a number (coverage floor, 50% measured-weight floor, sample labels, gated/agent-rated parts); warnings and what to add; batches (`--batches`/`--all`, `continue_batches`); improvement plan (P0/P1/P2, recomputed gain, P2 range, rules-part gain); engine vs agent text; the report's section order (as built by T070); a short "act on it" checklist | FR-066 |
| 2 | README gains a short "Reading a report" section (≤ 25 lines) linking to the guide | FR-066 |
| 3 | SCORING_FLOW.md improvement-plan and evidence-warnings sections gain interpretation guidance, linking to the guide | FR-066 |
| 4 | Every code name, key, flag and constant the docs mention exists in `src/` (a test greps the guide for backticked identifiers from a declared list and asserts each is found in source) | FR-066 |
| 5 | Every numeric example in the guide is reproducible from a real run (state which repo/command) or clearly marked illustrative | FR-066 |
| 6 | No marketing adjectives; no claim the engine judges quality | FR-066 |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|-------|--------|-----|
| 1 | Guide + README + SCORING_FLOW | AC1–3 sections present | automated (heading/link test) |
| 2 | Identifiers in guide | all exist in `src/` | automated |
| 3 | Reviewer read-through | a new reader can answer the four questions from the guide alone | Supervisor review |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t071_evaluation_docs.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T071.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T071.md`. BEFORE = verbatim prior README/SCORING_FLOW section headings.

---

## Approach

**Pattern reference**: `docs/SCORING_FLOW.md` and `docs/SCORING_RULES.md` — tone, precision, citation style.

Write from the merged code, not from memory: read `core/score.py`, `core/improve.py`, `core/judge.py` constants, `core/batches.py`, and the T070 report.

---

## Edge Case Checklist

- [ ] `docs/` is gitignored: add new files with `git add -f`
- [ ] Do not duplicate SCORING_RULES tables — link instead

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `docs/EVALUATION_GUIDE.md` | new |
| `README.md` | "Reading a report" section |
| `docs/SCORING_FLOW.md` | interpretation guidance |
| `tests/test_t071_evaluation_docs.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `src/**` | docs-only task |

---

## Test Plan

Doc-structure and identifier-existence tests; Supervisor read-through.

---

## Completion Checklist

- [ ] Implementation done
- [ ] `Skill({ skill: "code-review" })`
- [ ] Tests written AND pass — pasted in `tasks/TASK_REVIEW_T071.md`
- [ ] Supervisor notified
