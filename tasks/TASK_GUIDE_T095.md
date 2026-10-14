# TASK_GUIDE — T095: Redaction masks URL path segments whose pieces are upper-case letters then digits (`WCAG22`)
**Date**: 2026-10-13
**Complexity Level**: C1
**Risk Level**: Medium (redaction is a security control, NFR-010)
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

## Bug Fix Task Guide — T095

### Mental Model (confirmed by user)
- **Observed:** `redact("See https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html for details")` returns `'See https://www.w3.org/…****:458fc23ebb1e.html for details'`. A plain W3C link in this repo's README is fingerprinted as a secret, so the citation cannot resolve. The KANBAN follow-up from T089 recorded this.
- **Expected:** ordinary URL path text survives. That means word pieces plus a piece made of an upper-case letter run followed by a digit run (`WCAG22`, `HTTP2`, `ES2015`, `UTF8`, `ISO27001`). These things must still be fingerprinted exactly as they are now:
  - random mixed-case tokens such as `xQzRtWvB…`;
  - interleaved letters and digits such as `A1B2C3D4…`;
  - hash-named artefacts;
  - URL userinfo and query secrets.
- **Likely divergence point:** `src/easy_verifier/core/redact.py` `_LETTER_DIGIT_PIECE = r"[a-z]{1,6}[0-9]{1,8}"`, added by T091, admits lower-case letters only. So `WCAG22` fails `_NAME_PIECE`, and the T053 URL/file-suffix exemption (`is_version_labelled_name`) does not apply. The token `WAI/WCAG22/Understanding/non-text-content` then clears the 4.0-bit bar.
- **Recent context:** T029, T051, T053 and T091 are the same class of problem: entropy redaction applied to names.
- **User approval:** "yes" (2026-10-13) to continue with the follow-ups as listed. Scoring side effect: false `redaction_hits_observed` hits can only go down.

### Intake
- **Trigger:** `PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('See https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html for details'))"`
- **Severity:** P2 (wrong citation, no crash)
- **Affected area:** `core/redact.py`, entropy exemptions only. The named detectors are untouched.

### Complexity & Risk
- **Complexity:** C1
- **Risk:** Medium. Accepted residue, stated in the docstring as T091 does: a secret shaped only as upper-case letter run + digit run pieces, joined by `_`, `-` or `/` and written inside a URL path or before a `.ext`, is no longer caught by this rule (for example `ABC123-DEF456.txt`). Credentials are not issued in this shape.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | The trigger line survives unchanged |
| 2 | `WCAG22`, `HTTP2`, `ES2015`, `UTF8` and `ISO27001` pieces are all exempt inside a URL path and before `.ext` |
| 3 | Still fingerprinted: `A1B2C3D4E5F6G7H8J9K0L1M2` (interleaved), a 40-char base64url token, `main-3F9A2B1C.js` (digits before letters inside a piece), `https://user:Summer2024XqZ@host/…` (userinfo), `?token=…` in a query, and a Slack-webhook-shaped path segment |
| 4 | All existing T029/T051/T053/T091 redaction tests pass with expectations unedited |
| 5 | This repo's tracked-path test (`test_t029…::test_every_tracked_path_of_this_repo_survives_redaction`) and line-fidelity test pass, and a new test runs `redact()` over this repo's README with no `high_entropy_string` hit on that URL |
| 6 | Real repos (node-monorepo, fullstack-ts, nest-api, this repo): security `redaction_hits_observed` before → after is pasted. It may only go down. Each hit that disappeared is listed and checked by hand as a path or name, not a secret |

### Diagnosis Gates (Pillar 1 — must pass before any fix)
- [ ] Phase 1 feedback loop built and running (the trigger above)
- [ ] Bug reproduces deterministically on the loop
- [ ] 3–5 ranked falsifiable hypotheses listed (consistent with confirmed mental model)
- [ ] Correct hypothesis identified via Phase 4 instrumentation

### Attempts Log (filled live during diagnosis — required if >1 hypothesis tested)
| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

### Fix Gates (Pillar 2)
- [ ] Regression test written before the fix (it fails on develop `b5f23b6`)
- [ ] Fix applied; regression test passes
- [ ] Phase 1 loop no longer reproduces the bug
- [ ] Fix matches "Expected" (AC 2–5)
- [ ] Real repos: AC 6 pasted

### Cleanup Checklist (Pillar 3)
- [ ] All [DEBUG-...] instrumentation removed (grep verified)
- [ ] Throwaway prototypes deleted
- [ ] Correct hypothesis stated in commit message
- [x] Post-mortem: T091 widened the piece shape for one case (lower-case) without testing its case twin; widen shapes symmetrically and test both cases.

### Files Must NOT Touch
`core/roles.py` (T094 runs in parallel), `core/documents.py` (T096 runs in parallel), and the named detectors in `redact.py`.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

Real repos: paths are as in `tasks/TASK_GUIDE_T094.md` "Real repos". Run them in the background with `</dev/null`.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T095.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T095.md`.

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.
