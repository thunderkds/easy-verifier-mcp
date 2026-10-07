# TASK_GUIDE — T083: `score --scope changes` crashes when the diff has no API spec / route source file
**Date**: 2026-10-07
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

## Bug Fix Task Guide — T083

### Mental Model (confirmed by user)
- Observed: `score --scope changes` on a diff whose only change is a non-code file (e.g. a `.tfvars`) raises `MetricCitationError: metric 'breaking_api_changes_observed' (api) reports a value but cites no evidence`, so the whole score fails.
- Expected: when no API specification or route source file in the diff was read, `breaking_api_changes_observed` **abstains** with a reason ("no API specification or route source file in this diff was read") and the score completes; the api dimension rates on its other rules or abstains honestly. When removed endpoints/fields are found but their file was not read, the metric also abstains rather than reporting an uncited value.
- Likely divergence point: `src/easy_verifier/dimensions/api.py:_breaking_metric` (line ~382) returns `_metric(name, len(gone), cited, ...)` with `cited` empty; the citation invariant in `core/metrics.py` (~3540) raises.
- Recent context: introduced by T044 (merged e54712c, 2026-10-07); reproduced by the T042 agent on base c1b6d73. User confirmed this model 2026-10-07.

### Intake
- Trigger: target git repo whose working diff (changes scope) touches only a `.tfvars` (or any non-spec, non-source) file → `easy-verifier score --repo <r> --scope changes`.
- Severity: P1 — every changes-scope score on a non-code diff crashes.
- Affected area: `src/easy_verifier/dimensions/api.py` (`_breaking_metric`), tests.

### Complexity & Risk
- Complexity: C1
- Risk: Medium

### Diagnosis Gates (Pillar 1 — must pass before any fix)
- [ ] Phase 1 feedback loop built and running
- [ ] Bug reproduces deterministically on the loop
- [ ] 3–5 ranked falsifiable hypotheses listed (consistent with confirmed mental model)
- [ ] Correct hypothesis identified via Phase 4 instrumentation

### Attempts Log (filled live during diagnosis — required if >1 hypothesis tested)
| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

### Fix Gates (Pillar 2)
- [ ] Regression test written before the fix (or no-seam documented)
- [ ] Fix applied; regression test passes
- [ ] Phase 1 loop no longer reproduces the bug
- [ ] Fix matches the "correct behaviour" definition from the mental model

### Cleanup Checklist (Pillar 3)
- [ ] All [DEBUG-...] instrumentation removed (grep verified)
- [ ] Throwaway prototypes deleted
- [ ] Correct hypothesis stated in commit message
- [ ] Post-mortem: what would have prevented this?

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T083.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T083.md`.
