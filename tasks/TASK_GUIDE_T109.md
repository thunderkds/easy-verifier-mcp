# TASK_GUIDE — T109: `change_kind` gate — the calling agent confirms or overrides the detected change kind
**Date**: 2026-10-16
**Complexity Level**: C2
**Risk Level**: Medium (untrusted agent input changes a rating; replay parity must hold)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary: **Change kind**, **Agent input**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` FR-081, FR-022, FR-034; `docs/ddr/0014-change-risk-dimension.md`; DDR-0006 (`docs/ddr/`)
7. Read `src/easy_verifier/core/gate.py` (detect/evaluate/review gates and how each validates agent
   input), `core/score.py` (`parse_agent_input`), `adapters/mcp_server.py` (`needs_input` assembly
   around line 216), `adapters/cli.py` (`--agent-input`), and T108's `dimensions/change_risk.py`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16: "you will need to ask about the kind of thing to score, or you may depend on the
changes file to detect and confirm with supervisor from llm about that".

**Restated intent**:
> When `change-risk` is rated, the MCP `score` response asks the calling agent to confirm or override
> the detected kind: `needs_input.change_kind = {proposal, signals, allowed: [bugfix, feature,
> refactor, chore], instructions}`. The agent's answer returns on the next call as
> `agent_input.change_kind = {value, reason}`; it is validated (enum, `reason` a non-empty string ≤ 500
> chars), and when valid it replaces the detected kind and the payload says `source: "confirmed"` (with
> the agent's reason). An invalid answer is rejected with a structured reason and the detected kind is
> kept (`source: "detected"`). The CLI never asks but accepts the same answer through `--agent-input`,
> and the same repo + scope + agent input give a byte-equal payload through both adapters (FR-022).
> The engine makes no model call (NFR-001).

**Out of scope**: test ↔ symbol pair confirmation (S2); new rules (T110); asking when `change-risk`
abstains for scope (no question at `project`/`task` scope).

**Requirement Refs**: FR-081, FR-022, FR-034, NFR-001, US-022.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md`
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T108
**Entry point**: MCP `score` tool (`needs_input.change_kind` out, `agent_input.change_kind` in) and CLI `score --agent-input`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | MCP `score` at `changes`/`worktree` scope includes `needs_input.change_kind` (proposal, signals, allowed values, fixed instructions telling the agent to read the diff and answer with value + reason) unless a valid `agent_input.change_kind` was supplied; the CLI payload never contains it (FR-021/FR-034) |
| 2 | `agent_input.change_kind` is parsed by the existing agent-input parser; valid → kind replaced, `change_kind.source = "confirmed"`, `change_kind.reason` = the agent's reason (redacted like other agent text); the rating follows the confirmed kind |
| 3 | Invalid answers — value outside the enum, missing/empty/over-long reason, wrong type, extra keys — are rejected with a structured reason in the payload (same shape as other rejected agent input) and the detected kind is kept with `source: "detected"`; never a crash |
| 4 | Parity: for the same repo, scope and agent input, CLI (`--agent-input`) and MCP payloads are byte-equal after DDR-0005 normalization, with and without a `change_kind` answer |
| 5 | Override changes the score: on a synthetic repo whose detected kind is `feature` (abstains until T110 — or rated if T110 merged first), confirming `bugfix` applies `bugfix_without_regression_test`; the test asserts the rule result flips |
| 6 | Real repo: node-monorepo `--ref 09be767d0` via CLI with `--agent-input '{"change_kind": {"value": "bugfix", "reason": "..."}}'` → `source: "confirmed"`, rule fails; same through the MCP stdio surface (`.claude/skills/verify/SKILL.md`) |
| 7 | Tests in `tests/test_t109_change_kind_gate.py` cover AC1–AC5 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- MCP asks; agent answer applied; invalid answers rejected loudly; CLI = MCP.
- New tests pass; full suite and ruff green.

### Verification Command (exact, runnable)

Py3.12 venv as in T107.

```bash
<py312> -m pytest -q tests/test_t109_change_kind_gate.py
<py312> -m pytest -q          # background
<py312> -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T109.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T109.md`. BEFORE = MCP `score(scope="changes")` response without
> `needs_input.change_kind`, and `--agent-input '{"change_kind": …}'` ignored or rejected as unknown.

---

## UI / Design Acceptance Criteria

> N/A — no UI change beyond T108's block showing `source`. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: the review gate in `core/gate.py` (`review_requests` → `needs_input.review`,
answers in `agent_input.reviews`) — same request/answer/validate/replay shape.

1. Capture BEFORE. 2. Parser + validation, test-first. 3. `needs_input.change_kind` in the MCP adapter
only. 4. Parity test. 5. Real-repo CLI + MCP check.

---

## Edge Case Checklist

- [ ] Answer supplied at `project` scope → ignored with a stated reason (no change-risk rating there), not an error
- [ ] Answer equal to the detected kind → `source: "confirmed"` (the agent confirmed it), rating unchanged
- [ ] Reason text containing a secret-shaped string is redacted before it reaches the payload/report
- [ ] Unicode / very long reason → bounded, rejected over 500 chars
- [ ] Agent input with `change_kind` plus other keys (picks, reviews) → each validated independently

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/gate.py` | `change_kind_request` + validation |
| `src/easy_verifier/core/score.py` | parse/apply `agent_input.change_kind` |
| `src/easy_verifier/adapters/mcp_server.py` | `needs_input.change_kind` |
| `src/easy_verifier/dimensions/change_risk.py` | accept the confirmed kind |
| `tests/test_t109_change_kind_gate.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/adapters/cli.py` beyond what `--agent-input` already does | CLI never asks (FR-034) |
| other dimensions | out of scope |

---

## Test Plan

Unit tests for validation; adapter-level tests for MCP `needs_input`; a parity test running both
adapters on one synthetic repo with and without the answer.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T109-change-kind-gate`
- [ ] AC6 real-repo output pasted into `tasks/TASK_REVIEW_T109.md`
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
