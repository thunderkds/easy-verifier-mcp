# TASK_GUIDE — T097: Redaction masks paths whose name pieces have more than 6 letters before digits (`rancher2`)
**Date**: 2026-10-13
**Complexity Level**: C1
**Risk Level**: Medium (redaction is a security control, NFR-010)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

## Bug Fix Task Guide — T097

### Mental Model (confirmed by user)
- **Observed:** on k8s-ops, 50 of 371 tracked paths under `rancher2/`, `rancher/` and `elk/` are fingerprinted by `redact()`. For example, `rancher2/cb-ppl/gateway-prod-ingress.yml` becomes `ranc…****:bdeabc3ea4ad.yml`. Those citations in the T094 infrastructure card cannot resolve. This was found while reviewing T094.
- **Expected:** an ordinary path piece made of a letter run of any word length (up to 30, like `_WORD_PIECE`) followed by a digit run survives the entropy rules: `rancher2`, `backup2`, `python3`, `postgres16`, `elasticsearch7`, `KUBERNETES1`. Everything T091 and T095 still fingerprint is still fingerprinted:
  - random mixed-case tokens;
  - interleaved letters and digits;
  - digits-before-letters artefacts (`main-3f9a2b1c.js`);
  - a realistic Slack webhook;
  - `AKIA…` keys;
  - URL userinfo and query secrets.
- **Likely divergence point:** `src/easy_verifier/core/redact.py` `_LETTER_DIGIT_PIECE = r"(?:[a-z]{1,6}|[A-Z]{1,6})[0-9]{1,8}"`. The 6-letter cap (T091, then mirrored in T095) rejects `rancher2`, so the whole path loses the `_WORD_JOINED_NAME` file-suffix exemption and clears the entropy bar.
- **Recent context:** T029, T051, T053, T091 and T095 are the same class of problem. The learning from T095: widen a piece shape symmetrically, for both letter cases.
- **User confirmation:** "yes, fix it as T097" (2026-10-13), after being told it loosens masking slightly. False `redaction_hits_observed` hits can only go down.

### Intake
- **Trigger:** `PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('rancher2/cb-ppl/gateway-prod-ingress.yml'))"`. Also count the tracked paths that fail to survive: `git -C <real-repos>/k8s-ops ls-files`, where `redact(p) != p` gives 50 on develop `a245fb7`.
- **Severity:** P1 (citations unresolvable on a real repo)
- **Affected area:** `core/redact.py`, entropy exemptions only. The named detectors are untouched.

### Complexity & Risk
- **Complexity:** C1
- **Risk:** Medium. Accepted residue, written into the docstring as T091 and T095 did: a secret shaped only as single-case letter runs of up to 30 letters, each followed by a digit run, joined by `_`, `-` or `/` inside a URL path or before `.ext`, is no longer caught by this rule. Generated credentials are mixed-case alphanumerics, so this is not their shape.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | The trigger path survives unchanged |
| 2 | `rancher2`, `postgres16`, `elasticsearch7` and `KUBERNETES1` pieces are exempt before `.ext` and inside a URL path; a 31-letter run before digits is not exempt (bound test) |
| 3 | Still fingerprinted: every T091/T095 negative, plus `aB3xK9mQzR7tWvY2pL8nC4dF`-style segments, `AKIA…`, a realistic Slack webhook `…/T024BE7LD/B01ABCD2EFG/<mixed-case token>`, userinfo, and a `?token=` query |
| 4 | All existing T029/T051/T053/T091/T095 tests pass with expectations unedited |
| 5 | k8s-ops: every tracked path survives `redact()`, or each one that doesn't is listed with the reason it legitimately should not |
| 6 | Real repos (k8s-ops, node-monorepo, fullstack-ts, nest-api, python-ml, this repo): security `redaction_hits_observed` and every rating before → after are pasted. Hits may only go down, and each vanished hit is checked by hand as a path or name. Any rating change is reported with its cause |

### Diagnosis Gates (Pillar 1 — must pass before any fix)
- [ ] Phase 1 feedback loop built and running (the trigger above)
- [ ] Bug reproduces deterministically on the loop
- [ ] 3–5 ranked falsifiable hypotheses listed (consistent with confirmed mental model)
- [ ] Correct hypothesis identified via Phase 4 instrumentation

### Attempts Log (filled live during diagnosis — required if >1 hypothesis tested)
| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

### Fix Gates (Pillar 2)
- [ ] Regression test written before the fix (fails on develop `a245fb7`)
- [ ] Fix applied; regression test passes
- [ ] Phase 1 loop no longer reproduces the bug
- [ ] Fix matches "Expected" (AC 2–5)
- [ ] Real repos: AC 6 pasted

### Cleanup Checklist (Pillar 3)
- [ ] All [DEBUG-...] instrumentation removed (grep verified)
- [ ] Throwaway prototypes deleted
- [ ] Correct hypothesis stated in commit message
- [ ] Post-mortem: what would have prevented this?

### Files Must NOT Touch
The named detectors in `redact.py`, and everything outside `core/redact.py` and the new test file `tests/test_t097_long_letter_digit_pieces.py`.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

All read-only:
- k8s-ops `<real-repos>/k8s-ops`
- node-monorepo `<real-repos>/node-monorepo`
- fullstack-ts `<real-repos>/fullstack-ts`
- nest-api `<real-repos>/nest-api`
- python-ml `<real-repos>/python-ml`

Run them in the background with `</dev/null`.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T097.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T097.md`.

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.
