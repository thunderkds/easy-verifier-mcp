# TASK_GUIDE — T092: Dangerous-sink hits in test files are reported, not scored
**Date**: 2026-10-13
**Complexity Level**: C1
**Risk Level**: Medium (security rating semantics)
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

Supervisor finding (2026-10-13): after T091, coffee-shop-api's security dropped from 59 to 18. The
pack now reads 143 files instead of 66 and finds one CWE-89 hit at `test/reset-test-db.ts:25`, a
test helper building `truncate table ${names}`. `sink_hits_observed` (weight 35, pass when 0)
already tags test-path hits `[test path]` but still counts them.

Question to the user: "Should risky code inside test files lower the security score the same as
risky code in the real app? My suggestion: no — still show it, but don't count it." User
(2026-10-13): **"yes, agree"**.

**Restated intent**:
> `sink_hits_observed` counts only hits in non-test files. Hits in test files are still listed in
> the derivation, cited and tagged `[test path]`, but they do not change the value or the rating.

**Out of scope**:
- `redaction_hits_observed` and other security metrics
- The test/source classification itself (`_is_test_file` is reused as-is)
- Budget sensitivity of the security pack (a separate observation)

**Requirement Refs**:
- FR-043 (declared rating rules); user decision 2026-10-13

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user, 2026-10-13: "yes, agree")
- [x] Domain terms align with `PROJECT_SPEC.md` (metric, rating, test path)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-043 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `_sink_hits_observed` in `src/easy_verifier/core/metrics.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | The value of `sink_hits_observed` = the number of distinct hits in non-test files only | not counted |
| 2 | Test-file hits are still listed in the derivation with path:line, CWE, URL and `[test path]`; the derivation states that "N test-path hit(s) are listed and not counted" | still shown |
| 3 | If every scanned excerpt is a test file, the metric **abstains** with a reason ("only test files were scanned for sinks"), never 0 | abstention is a state, not a value (Constraint 1b) |
| 4 | Citations (`computed_from`) still include the test-hit refs so the reader can open them | still shown |
| 5 | Both extremes pinned: a fixture with one production hit and one test hit gives 1; a sabotage that counts test hits gives 2 and must fail the test | pinned |
| 6 | **Real repo (paste)**: coffee-shop-api security before → after (expected: sink 1 → 0, security 18 → back toward its non-test value); bryony and kitchd security before → after, listing any test-path hits that stop counting, checked by hand | real-repo verified |

---

## Evaluation & Acceptance

### Verification Command

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api --scope project < /dev/null
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T092.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `_sink_hits_observed` already computes `_is_test_file(path, view.tables)`
for its tag. Split the hits into production and test sets, count only the production set, and
describe both. Update the `_SINK_METHOD` wording and the `SCORING_RULES.md` row.

---

## Edge Case Checklist

- [ ] A file that is both test-named and under `src/`: use `_is_test_file` as-is, never re-derive
- [ ] Same line, two CWEs: counted per (path, line, CWE), as today
- [ ] Snapshot tests that pin the derivation text: update and justify

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | count non-test hits only; derivation |
| `docs/SCORING_RULES.md` | sink row |
| `tests/test_t092_test_path_sinks.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` weights in `core/judge.py` | unchanged |

---

## Completion Checklist

- [ ] Implementation done; tests written and pass; real-repo runs pasted (AC 6)
- [ ] Supervisor notified: task ready for Stage 4 review
