# TASK_GUIDE — T047: Pack mechanism (detect pick / config) + healthcare pack (#9 PHI, #28 BAA/residency)
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
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
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0008-thirteen-dimensions-rule-groups-and-optional-packs.md` and `BRAINSTORMING_LOG_evaluation-areas.md` (32-area mapping table)
8. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

Decided E1 (2026-09-28): healthcare/finance/frontend-a11y are optional packs, active only when detected or configured — never guessed.

**Restated intent**:
> A pack switches on only via a detect-gate pick or `.easy-verifier.toml`; the healthcare pack adds PHI test-data/log checks and BAA/residency documentation rules.

**Out of scope**:
- Finance and frontend packs (T048, T049)
- Legal compliance judgment — documentation presence only

**Requirement Refs**:
- FR-053: optional packs, never guessed
- FR-052: documentation rules for BAA/residency
- FR-035 detect gate, FR-033 config (add-only; packs are an allowed addition)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T039 — rule groups/doc rule; T037 — gate plumbing

**Entry point**: `packs`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `.easy-verifier.toml` `packs = ["healthcare"]` or an MCP detect pick activates a pack; nothing else does | never guessed |
| 2 | Healthcare pack rules: PHI-shaped data (SSN/MRN/DOB patterns) in fixtures/logs = 0 (HIPAA §164.514 de-identification cited); retention policy, BAA, data classification/residency = documentation rules | #9, #28 |
| 3 | Inactive pack contributes nothing and costs no evidence budget | cost scales |
| 4 | Pack results appear under their area labels and in overall disclosure | visible |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | repo with fixture containing SSN-shaped value + pack active | #9 rule unmet, cited | automated test |
| 2 | same repo, pack inactive | no healthcare output | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T047.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T047.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/roles.py` `.easy-verifier.toml` handling (add-only config)

A pack = registry data (patterns + rules with area labels) + activation flag. PHI values must be redacted in output like secrets (fingerprint), never echoed.

---

## Edge Case Checklist

- [ ] Synthetic test data clearly marked fake (e.g. 000-00-0000) — allowlist per HIPAA guidance
- [ ] Pack requested but unknown → warning, ignored

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/roles.py` | `packs` config key |
| `src/easy_verifier/core/registry.py` | pack loading |
| `src/easy_verifier/registry/packs/healthcare.toml` | new |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| core dimensions' default rules | packs only add |

---

## Test Plan

Activation tests (config, pick, none); PHI fixture tests with redaction check.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T047.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
