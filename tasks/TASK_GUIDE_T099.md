# TASK_GUIDE — T099: Redaction masks extensionless lower-case word paths (`bin/build-push-kibana-docker-image`)
**Date**: 2026-10-14
**Complexity Level**: C1
**Risk Level**: Medium (redaction is a security control, NFR-010)
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`
**Depends on**: none

## Bug Fix Task Guide — T099

### Mental Model (Supervisor, follow-up from T097)
- **Observed:** `redact('bin/build-push-kibana-docker-image')` returns `bin/…****:e169e83f548e`.
  This is the 1 scraping-devops tracked path still changed by redaction after T097, so citations to
  it cannot resolve.
- **Expected:** a slash-bearing token whose every piece is a **lower-case** word shape survives the
  long-token entropy rule even without a file suffix. Each piece is `[a-z]{1,30}`, a digit run
  `[0-9]{1,8}`, or a lower-case letter-digit piece (T097), and pieces are joined by `/`, `-` or `_`.
  Examples: `bin/build-push-kibana-docker-image`, `scripts/deploy-all-the-things`,
  `rancher2/cb/worker-get-job`. These stay fingerprinted:
  - a bare no-`/` identifier in prose (T029 rule kept: over-redaction outside path shapes);
  - mixed-case or upper-case pieces with no suffix;
  - random mixed-case tokens after `bin/`;
  - `AKIA…`;
  - a realistic Slack webhook;
  - URL userinfo and `?token=` queries;
  - everything T029, T051, T053, T091, T095 and T097 still catch.
- **Likely divergence point:** `core/redact.py` `_entropy_spans`. `_ENTROPY_CANDIDATE` takes the whole
  34-character token. `_PATHISH` needs a leading `/`/`~` or a `/word/` in the middle, so a single
  relative slash fails it. `is_version_labelled_name` needs a suffix or a URL anchor, so the token is
  scored on entropy (≥ 4.0) and masked.
- **Accepted residue** (the docstring must state it, as T091/T095/T097 did): a secret made only of
  lower-case letter words joined by `-`/`_` and containing a `/` is no longer caught by the
  long-token rule. Generated credentials are mixed-case alphanumerics, so this is not their shape.
  The per-segment rule (`_KEY_MATERIAL_CANDIDATE`) is unchanged.

### Intake
- **Trigger:** `PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('bin/build-push-kibana-docker-image'))"`
  Also count: on develop `9bfa721`, `git -C <scraping-devops> ls-files` gives 1 path where `redact(p) != p`.
- **Severity:** P2
- **Affected area:** `core/redact.py`, the long-token entropy exemption only. The named detectors are untouched.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | The trigger path survives unchanged |
| 2 | The lower-case slash-bearing word paths listed above survive. A no-`/` lower-case identifier ≥ 32 chars is judged as before; a mixed-case extensionless path like `bin/Build-PushKibana-DockerImage-Tool` is judged as before |
| 3 | Still fingerprinted: `bin/aB3xK9mQzR7tWvY2pL8nC4dF`-style tokens, `AKIA…`, a realistic Slack webhook, userinfo, `?token=`, and every T091/T095/T097 negative |
| 4 | All existing redaction tests pass with expectations unedited |
| 5 | scraping-devops: every tracked path survives `redact()` (0 changed), pasted |
| 6 | Real repos (scraping-devops, bryony, kitchd, coffee-shop-api, ai-training, this repo): security `redaction_hits_observed` and every rating before → after are pasted. Hits may only go down, and each vanished hit is checked by hand as a path |

### Diagnosis Gates (Pillar 1 — must pass before any fix)
- [ ] Phase 1 feedback loop built and running (the trigger above)
- [ ] Bug reproduces deterministically on the loop
- [ ] 3–5 ranked falsifiable hypotheses listed
- [ ] Correct hypothesis identified via instrumentation

### Attempts Log
| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

### Fix Gates (Pillar 2)
- [ ] Regression test written before the fix (fails on develop `9bfa721`)
- [ ] Fix applied; regression test passes
- [ ] Fix matches "Expected" (AC 2–5)
- [ ] Real repos: AC 6 pasted

### Cleanup Checklist (Pillar 3)
- [ ] All [DEBUG-...] instrumentation removed (grep verified)
- [ ] Correct hypothesis stated in commit message
- [ ] Post-mortem: what would have prevented this?

### Files Must NOT Touch
The named detectors in `redact.py`, and everything outside `core/redact.py` and the new test file `tests/test_t099_extensionless_word_paths.py`.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Real repos

All read-only:
- scraping-devops `/home/hungnguyenhuu/workspace/project/bryony/scraping-devops`
- bryony `/home/hungnguyenhuu/workspace/project/bryony/bryony`
- kitchd `/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd`
- coffee-shop-api `/home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api`
- ai-training `/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training`

Run them in the background with `</dev/null`. Agent worktrees have no `.venv`, so use the main checkout's interpreter with `PYTHONPATH=src`.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T099.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T099.md`.

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.
