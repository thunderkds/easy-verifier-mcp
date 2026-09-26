# TASK_GUIDE — T028: MCP evaluate gate — gate evaluations, capped blend, rating provenance
**Date**: 2026-09-26
**Complexity Level**: C3
**Risk Level**: High
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0006-any-language-roles-and-agent-hard-gates.md` (partially supersedes DDR-0003) and `docs/ddr/0003-abstain-from-rating-below-coverage-floor.md`
8. Read the merged T026 and T027 code (`core/roles.py`, `core/gate.py`)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-26): "ask agent llm for hard gate to detect and evaluate" and "agent as contribute to
make the score more correctly"; chose the **capped blend** `w = 0.5 × confidence`. This task is the
**evaluate** half.

**Restated intent**:
> Over MCP only, when a dimension's rules abstain or any rule input sits within ±10% of its
> threshold, `score` asks the calling agent for a cited, confidence-bearing evaluation of that
> dimension. A valid answer blends into the rating by the capped formula (or stands alone, labelled
> agent-rated, where the rules abstained). Every blended or agent-rated number is shown with its
> parts, and the overall discloses how each dimension was rated.

**Out of scope**:
- Changing any rating rule, threshold, or coverage floor.
- Blending findings-based assessments (FR-029a still forbids that).
- Any model call; any CLI prompting.

**Requirement Refs**:
- FR-036: evaluate gate triggers (abstain or ±10%), one round, max two rounds total
- FR-037: gate evaluation shape + validation (score, confidence, ≥1 resolving evidence_ref, only for gated dimensions)
- FR-038: capped blend, agent-rated, parts always shown, overall disclosure
- FR-039 (rating half): rating provenance `rules` / `blended (w)` / `agent-rated`
- FR-029a (amended), FR-022 (amended), FR-040, DDR-0006, DDR-0003 (partially superseded)
- US-012, US-014

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, Stage 0.5 2026-09-26)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (hard gate, gate evaluation, capped blend, agent-rated)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria

---

## Dependencies & Reachability

**Depends on**: T026 — agent-input parsing and roles; T027 — `core/gate.py` and `needs_input` payload

**Entry point**: `gate_evaluations`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | A dimension is at an evaluate gate iff its rules abstain **or** any rule input's metric value lies within ±10% of its declared threshold (band as declared data; threshold 0 → never borderline (Supervisor decision 2026-09-26, Stage 4)). Tested at band edges (9.9%, 10%, 10.1%). | FR-036 |
| 2 | MCP `score` emits `needs_input.gate_evaluations` for each gated dimension: dimension, gate reason (`abstained` / `borderline: <metric>`), and the evidence refs available to cite. Not emitted when the call already carries `gate_evaluations`; never emitted by the CLI. If picks are also pending, picks are asked first and gates computed after picks are applied (max two rounds). | FR-036, FR-040 |
| 3 | A gate evaluation `{score, confidence, evidence_refs[, rationale]}` is rejected, naming the field, when: score ∉ [0,100] or non-numeric; confidence ∉ [0,1]; no evidence_ref; an evidence_ref not in that dimension's pack (FR-015a); the dimension is not currently gated. `rationale` is accepted but never written to the report (FR-039). | FR-037 |
| 4 | Blend: `w = 0.5 × c`; `final = R·(1−w) + A·w` rounded half-up via `Decimal` and clamped 0–100. Worked cases asserted: R=68, A=88, c=0.6 → w=0.30 → 74; R=50, A=51, c=1 → 50.5 → **51** (not banker's 50); c=0 → final=R. | FR-038, Edge 7 |
| 5 | Rules abstained + valid evaluation → `final = A`, labelled `agent-rated`; the abstention record (floor, achieved coverage, misses) is still present beside it. | FR-038, DDR-0006 |
| 6 | Every blended/agent-rated value in `score` output and the HTML report shows its parts (e.g. `74 = rules 68 + agent 88 (w 0.30)`); no code path renders the blended number alone. | FR-038 |
| 7 | Overall rating averages rule-rated, blended and agent-rated dimensions and its disclosure states the count of each plus abstentions with reasons. | FR-038, FR-028b |
| 8 | Outside a gate, no agent input changes any number — asserted by feeding an evaluation for an ungated dimension (rejected) and by property test that ratings with/without agent input are equal for ungated dimensions. | FR-038, FR-036 |
| 9 | Findings-based assessments remain side by side and are never blended (FR-029a regression test stays green). | FR-029a |
| 10 | CLI `--agent-input` replays `picks` + `gate_evaluations`; MCP and CLI results byte-equal after DDR-0005 normalization. | FR-022, FR-034 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Fixture where `security` abstains; evaluation A=70, c=0.8, valid ref | security `70`, `agent-rated`, abstention detail retained | automated test |
| 2 | R=68 borderline; A=88, c=0.6 | `74 = rules 68 + agent 88 (w 0.30)` in JSON and HTML | automated test |
| 3 | Evaluation for ungated `architecture` | validation error naming dimension | automated test |
| 4 | Evaluation citing unknown ref | validation error naming the ref | automated test |
| 5 | Live MCP stdio session vs Docker image on `ai-training`: call 1 → gates; call 2 with evaluations | blended/agent-rated values + disclosure | `verify` run, transcript pasted |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled in `tasks/TASK_REVIEW_T028.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T028.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/judge.py` — declared-data rules, abstention records,
overall disclosure string; extend, don't restructure. `src/easy_verifier/core/findings.py` —
evidence-ref resolution (FR-015a) and all-errors-at-once validation; reuse its resolver.

Add to `core/gate.py`: `detect_evaluate_gates(ratings, rules)`, `validate_gate_evaluations(doc,
packs, gates)`, `blend(R, A, c) -> Decimal-rounded int`. `judge.py` gains the three rating states
(rule-rated / blended / agent-rated) in its output and disclosure; `report.py` renders the parts.
Band `±10%` lives as declared data next to the rating rules (a value change, not a code change —
FR-028).

---

## Edge Case Checklist

- [ ] Banker's rounding avoided (`Decimal`, ROUND_HALF_UP)
- [ ] Threshold 0 band collapses to equality — tested
- [ ] NaN/inf/bool/string score or confidence rejected
- [ ] Evaluation for a dimension that became ungated after picks → rejected with reason
- [ ] `rationale` text never reaches the report
- [ ] Overall never averages an abstained dimension without an evaluation
- [ ] DDR-0005 normalization list unchanged

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/gate.py` | evaluate-gate detection, validation, blend |
| `src/easy_verifier/core/judge.py` | rating states + disclosure; declared band |
| `src/easy_verifier/core/score.py` | apply gate evaluations |
| `src/easy_verifier/core/report.py` | render parts + rating provenance |
| `src/easy_verifier/adapters/mcp_server.py` | `needs_input.gate_evaluations`; tool description |
| `src/easy_verifier/core/roles.py` | lift T026's "gate_evaluations not yet supported" rejection |
| `tests/…` | per AC |
| `README.md`, MCP guides | evaluate flow, blend formula |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/assessment.py` | findings assessments stay unblended (FR-029a) |
| `src/easy_verifier/core/metrics.py` | metrics unchanged; the gate reads them, never alters them |
| `core/redact.py`, `core/budget.py`, `Dockerfile`, `compose.yaml` | reuse only / hardening stays |

---

## Test Plan

Unit: gate detection at band edges, validation matrix, blend arithmetic table, disclosure strings.
Integration: MCP two/three-call flows (picks → gates → final), CLI replay parity, report rendering.
Live: Docker image via MCP stdio on `ai-training`.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk — caller input changes numbers)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T028.md` (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated
- [ ] Supervisor notified: task ready for Stage 4 review
