# TASK_GUIDE — T091: Redaction masks ordinary paths whose name pieces mix letters then digits
**Date**: 2026-10-13
**Complexity Level**: C1
**Risk Level**: Medium (redaction is a security control, NFR-010)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

## Bug Fix Task Guide — T091

### Mental Model (confirmed by user)
- Observed: `redact("tests/test_t087_third_party_exclusion.py")` returns `test…****:009fc5eee991.py`. `tests/test_t029*::test_every_tracked_path_of_this_repo_survives_redaction` fails on develop since the T087 merge (`1eaa761`).
- Expected: an ordinary path whose pieces are a letter run followed by a digit run (`t087`, `v2`, `utf8`, `py3`) survives the long-token entropy rule. Random mixed-case tokens (`xQzRtWvB`), keys with interleaved letters and digits, and hash-named artefacts (`main-3f9a2b1c.js`) are still fingerprinted exactly as now.
- Likely divergence point: `src/easy_verifier/core/redact.py` `_NAME_PIECE` (about line 195) only admits letters-only or digits-only pieces, so `t087` disqualifies the T029 file-name exemption. The 37-character token then clears the 4.0-bit bar. The shorter `test_t086_toml_migration_dirs` scores under 4.0, so it survives by luck.
- Recent context: T029 (file-name exemption), T051 (`_UNDERSCORE_IDENTIFIER`), T053 (digit-run pieces). This is the same class: entropy redaction on names.
- User (2026-10-13), plain-language summary agreed: "it does not affect scoring progress, just the tasks working". Scoring side effect: false `redaction_hits_observed` hits on paths only go down.

### Intake
- Trigger: `PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('tests/test_t087_third_party_exclusion.py'))"`
- Severity: P1 (develop red)
- Affected area: `core/redact.py` (entropy exemptions only; named detectors untouched)

### Complexity & Risk
- Complexity: C1
- Risk: Medium. Accepted residue, same as T029's: a secret shaped only as lowercase-letter-run + digit-run pieces before a `.ext` (`abc123_def456.txt`) is no longer caught by this rule. State it in the docstring as T029 does.

### Diagnosis Gates (Pillar 1 — must pass before any fix)
- [x] Phase 1 feedback loop built and running (the trigger above, plus the t029 test)
- [x] Bug reproduces deterministically on the loop
- [x] 3–5 ranked falsifiable hypotheses listed (consistent with confirmed mental model)
- [x] Correct hypothesis identified via Phase 4 instrumentation

### Attempts Log (filled live during diagnosis — required if >1 hypothesis tested)
| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

### Fix Gates (Pillar 2)
- [x] Regression test written before the fix (fails on develop `94618c1`)
- [x] Fix applied; regression test passes
- [x] Phase 1 loop no longer reproduces the bug
- [x] Fix matches "Expected": the existing T029/T051/T053 secret-still-fingerprints tests pass unchanged, and new negatives show `main-3f9a2b1c.js`, `xQzRtWvB…`, a 40-char base64url and `a1b2c3d4…` interleaved tokens still fingerprint (both extremes)
- [x] Real repos: the security dimension's `redaction_hits_observed` on bryony and kitchd, before → after, pasted. It may only go down. List any hit that disappeared and confirm by hand that it was a path or name, not a secret

### Cleanup Checklist (Pillar 3)
- [x] All [DEBUG-...] instrumentation removed (grep verified)
- [x] Throwaway prototypes deleted
- [x] Correct hypothesis stated in commit message
- [x] Post-mortem: what would have prevented this?

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T091.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T091.md`.
