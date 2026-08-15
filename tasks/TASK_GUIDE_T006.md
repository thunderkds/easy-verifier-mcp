# TASK_GUIDE — T006: findings.py — finding schema + write_report validation
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Skim `memory/codebase-map.md` for layout

---

## Requirement (Pillar 1 — Adapt the requirement)

Make an unevidenced claim impossible to publish. This module is the only thing standing between a
confident-sounding LLM finding and a report that a developer will trust.

**Restated intent**:
> `validate_findings(findings, packs)` rejects any finding missing an evidence reference **or** a
> confidence value, and rejects any finding whose evidence reference does not resolve to an item
> actually present in the pack it cites. Rejection names the offending finding and the exact missing
> or dangling field. Enforcement lives here, not in caller convention.

**Out of scope**:
- Rendering (T013) — this task validates and returns a structured result; HTML comes later.
- Judging whether a finding is *correct* — only whether it is founded.

**Requirement Refs**:
- FR-014 (partial): `write_report` accepts findings as structured JSON
- FR-015: reject if **either** evidence reference or confidence is missing from **any** finding; error names the finding and the missing field
- FR-015a: reject a finding whose evidence reference does not resolve to an item in the pack it cites
- FR-023: optional suggested-improvement field
- FR-024: suggestions are advisory text only — never applied or patched
- NFR-004: enforcement in validation, not in caller convention

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T001 — `EvidencePack` and `Excerpt` define what a citation must resolve *to*.

**Entry point**: `validate_findings`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `Finding` schema: `dimension`, `title`, `detail`, `evidence_ref`, `confidence`, optional `suggestion` | FR-014, FR-023 |
| 2 | A finding with evidence but **no confidence** is rejected | FR-015 |
| 3 | A finding with confidence but **no evidence** is rejected | FR-015 |
| 4 | A finding with neither is rejected | FR-015 |
| 5 | The validation error names the offending finding (by index and title) and the specific missing field — not a generic "invalid input" | FR-015 |
| 6 | A finding citing an evidence ref absent from the cited pack is rejected as a dangling citation | FR-015a |
| 7 | A finding citing a pack for a dimension that was not run is rejected | FR-015a |
| 8 | **All** findings are validated and **all** errors reported together — validation does not stop at the first failure | FR-015 |
| 9 | If any finding fails, the whole submission is rejected and **no report is written** — no partial write | NFR-004, FR-015 |
| 10 | `confidence` is constrained to a documented domain (e.g. `low`/`medium`/`high` or 0.0–1.0) and an out-of-domain value is rejected — an empty string or `null` is not a confidence value | FR-015 |
| 11 | `suggestion` is carried through as inert text; nothing in this module writes, patches, or executes anything | FR-024 |
| 12 | Findings are accepted tagged by dimension so a single submission can span several | FR-018a |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | 3 valid findings across 2 dimensions with resolvable refs | Accepted; result carries all 3 grouped by dimension | automated test |
| 2 | 4 findings where #2 lacks confidence and #4 has a dangling ref | Rejected; error lists **both** #2 and #4 with their distinct reasons | automated test |
| 3 | 1 finding citing `architecture` when only `security` was run | Rejected, naming the unrun dimension | automated test |
| 4 | `confidence: ""` | Rejected as out-of-domain | automated test |
| 5 | Any rejected submission | No file created anywhere on disk | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t006_findings.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T006.md`.
> This task's Evidence table is the audit artifact for the "Unevidenced findings reaching a report:
> 0" KPI in `PRD.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T006.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/models.py` (T001) — same dataclass conventions; keep `Finding` a plain dataclass unless the MCP SDK's tool-schema generation already requires pydantic, in which case reuse what is already a dependency rather than adding one.

Note the history here: FR-015 was originally ambiguous, and the loose reading ("reject only if
*both* are missing") silently defeated NFR-004 — that gap is why gap-audit item #9 exists. Implement
the strict reading and write the tests for AC #2 and #3 as separate named tests, so the ambiguity
cannot creep back in through a future refactor.

Collect-all-errors (AC #8) matters more than it looks: an agent that gets one error at a time will
fix, resubmit, fix, resubmit, burning context on a round trip per finding.

---

## Edge Case Checklist

- [ ] Empty findings list → is that acceptance or rejection? Decide, document, test. (Recommended: accepted, producing a report that states no findings were made — that is a meaningful result, distinct from a failure.)
- [ ] Duplicate findings (identical content) → accepted but flagged, or deduplicated; do not crash
- [ ] Evidence ref pointing at a **truncated-away** excerpt → dangling, and the error should say so specifically, since this is the confusing case for a caller who saw the item before truncation
- [ ] Evidence ref formatting variants (`path:12`, `path:12-40`, pack item ID) → one canonical form, documented, others rejected clearly
- [ ] `confidence` supplied as a string `"0.9"` when a float is expected, or vice versa
- [ ] Very large findings payload → bounded parse, no unbounded memory
- [ ] Malformed JSON entirely → clear parse error naming the position
- [ ] Unicode / control characters in `title` or `detail` → preserved safely for T013 to escape (do not sanitize here; escaping is the renderer's job and doing it twice mangles content)
- [ ] A finding whose `suggestion` contains something that looks like a patch or a shell command → still inert text; never interpreted (FR-024)
- [ ] Extra unknown fields in the submission → rejected or ignored, decided and documented

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/findings.py` | New — `Finding`, `ValidationError`, `validate_findings()` |
| `src/easy_verifier/core/models.py` | Add a stable evidence-item identifier to `Excerpt` so refs can resolve |
| `tests/test_t006_findings.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/report.py` | Does not exist yet — owned by T013 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t006_findings.py`. One named test per rejection reason (missing confidence, missing
evidence, both missing, dangling ref, unrun dimension, out-of-domain confidence) so a failure names
the violated requirement directly. Plus a multi-error test for AC #8 and a filesystem-assertion test
for AC #9 using `tmp_path` with a directory listing before and after.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T006.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
