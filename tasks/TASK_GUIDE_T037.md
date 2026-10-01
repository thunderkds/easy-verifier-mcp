# TASK_GUIDE — T037: MCP reference gate: framework detection + needs_input for missing fields only
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
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
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)
8. Read `docs/ddr/0006-any-language-roles-and-agent-hard-gates.md` and merged `core/gate.py`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): "Hey, you are working on NodeJS, we need all the source of truth relate to NodeJS before working on verify"; "do not overwhelm the research, it will waste the token"; "if can not search, ask the users … Like the grill skill". Decided G8 (frameworks on demand), G9 (≤20 fields), B2 (≤2 lookups, clear https link).

**Restated intent**:
> Over MCP, before rating, `score` names exactly the registry fields the rules need but the detected languages/frameworks lack, capped at 20, with instructions for a bounded lookup or a grill-style question to the user.

**Out of scope**:
- Storing answers (T036)
- Review gate (T038)
- Any CLI prompting (CLI never asks, FR-040)

**Requirement Refs**:
- FR-044: engine-detected languages + frameworks
- FR-045: reference gate, ≤20 fields, language before framework
- FR-046: ≤2 lookups, else ask user one question at a time
- FR-040: engine never calls a model

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T036 — `registry_entries` intake and local layer

**Entry point**: `needs_input`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Framework detection from manifest dependencies (e.g. `react`, `django`, `spring-boot`) is deterministic and listed in `score` output | engine detects |
| 2 | `needs_input.reference` lists only `{language|framework, field, why (which rule consumes it)}` for missing fields; ≤20; language fields first; nothing when complete | missing fields only |
| 3 | Each request carries fixed instructions: ≤2 lookups per field, official docs first, cite a clear https link, otherwise ask the user one question at a time with a recommended answer and submit as `user-supplied` | bounded research |
| 4 | Remaining gaps beyond 20 are scored with generic patterns and labelled | no silent gaps |
| 5 | CLI output never contains `needs_input.reference` (parity test excludes it like other gates) | FR-040 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture Node repo with `express` and no curated express entry | `needs_input.reference` lists express fields only | automated test |
| 2 | repo fully covered by curated entries | no reference gate | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T037.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T037.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/gate.py` `detect_pick_gates` — MCP-only question built in the shared core, excluded from CLI payload

Compute `required_fields = fields consumed by active rules`; `missing = required − (curated ∪ local)` per detected language/framework; order and cap. Framework→language mapping lives in registry data.

---

## Edge Case Checklist

- [ ] Framework detected in a nested workspace package only
- [ ] Same field missing for two frameworks → two entries, counted toward the cap
- [ ] Gate payload size (measure bytes on real repos, per T028 learning)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/gate.py` | reference gate |
| `src/easy_verifier/core/registry.py` | framework detection + required-field calc |
| `src/easy_verifier/core/score.py` | merge into MCP payload |
| `src/easy_verifier/adapters/mcp_server.py` | tool description update |
| `docs/` | MCP guide: reference gate flow |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| CLI adapter output | FR-040 |

---

## Test Plan

Gate unit tests (cap, order, empty); MCP payload tests; parity exclusion test; live Docker MCP run on one Node repo.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T037.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
