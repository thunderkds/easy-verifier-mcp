# TASK_GUIDE — T034: Security sink patterns per language (CWE-95/78/89) as registry data + metric
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
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

---

## Requirement (Pillar 1 — Adapt the requirement)

Approved rule table (B5): security — dangerous-sink hits (eval/exec CWE-95, shell CWE-78, SQL string concat CWE-89; per-language patterns) = 0. Patterns are ours, each citing its CWE/ASVS link (B3).

**Restated intent**:
> The security dimension counts dangerous-sink hits per language from cited registry patterns, so the security rating reflects code sinks, not only secrets.

**Out of scope**:
- Taint analysis / data-flow
- Rules/weights (T035)

**Requirement Refs**:
- FR-043 (security half)
- NFR-003: security available in every mode and scope
- FR-027a: a sink hit is evidence-local

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T031 — metrics read registry

**Entry point**: `sink_hits_observed`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Registry field `security_sinks` per language: list of `{cwe, pattern, citation_url}` for CWE-95, CWE-78, CWE-89 (e.g. Python `eval(`, `subprocess(..., shell=True)`, f-string/`%` into `execute(`; JS `eval(`, `child_process.exec(`, template string into `query(`) | per-language cited patterns |
| 2 | Metric `sink_hits_observed` (evidence-local) with per-hit citation (path:line, CWE id) | metric |
| 3 | Comments/strings stripped via T033 tokenizer before matching | fewer false positives |
| 4 | A safe parameterised query fixture yields 0 hits; the unsafe twin yields 1 | boundary |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Python `cursor.execute(f"... {user}")` | 1 hit, CWE-89 | automated test |
| 2 | Python `cursor.execute("... %s", (user,))` | 0 hits | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T034.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T034.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/security.py` existing evidence collection + `core/context.py` SECRET_BEARING_PATTERNS

Patterns are conservative (prefer misses over noise); each cites the CWE page and an ASVS V5 requirement. Report hits as excerpts so the agent can judge at the evaluate gate.

---

## Edge Case Checklist

- [ ] Test files containing sinks deliberately (security tests) — count but tag as test path
- [ ] Minified/vendored JS — excluded by existing ignore rules

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/curated/*.toml` | security_sinks |
| `src/easy_verifier/core/metrics.py` | sink metric |
| `src/easy_verifier/dimensions/security.py` | surface sink excerpts if not already in pack |
| `tests/` | safe/unsafe fixture pairs |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/redact.py | T029 owns it |

---

## Test Plan

Safe/unsafe fixture pairs per language for each CWE.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T034.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
