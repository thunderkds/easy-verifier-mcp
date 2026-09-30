# TASK_GUIDE — T058: Bugfix — #8 cookie rule never computes on a real Express/Passport repo (T056 defect)
**Date**: 2026-09-30
**Complexity Level**: C3
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, this guide, and `.claude/agents/backend.md`.
2. Read `memory/MEMORY.md` in full (path, not pasted), plus `memory/decisions.md` entries
   "2026-09-29 — T056 design decisions (user)" and "2026-09-30 — T056 weights and thresholds".
3. Invoke `Skill({ skill: "diagnose" })` as the first action. No fix code before every Diagnosis Gate is checked.

---

## Bug Fix Task Guide — T058

### Mental Model (confirmed by user)

- **Observed**: On the real repo bryony (`/home/hungnguyenhuu/workspace/project/bryony/bryony`, an Express + Passport JS app), `score --scope project` leaves security's `cookie_flags_missing_observed` unavailable. The reason is "no authentication or session code (a registry auth_markers token) was found in 12 source-file excerpt(s)". Security rates 59 over a denominator of 85, and the #8 rule never computes. Two causes were found:
  1. **Excerpt selection.** The security pack reads 225 files but keeps only 40 excerpts. They are ranked by *path* category (`_ranked_candidates` / `_category` / `_has_auth_marker` on the path in `dimensions/security.py`), so frontend `auth/*.hbs` templates, `package.json` files and Dockerfiles fill the budget. `backend/server/dashboard/index.js` is never quoted, although it holds the Passport setup (lines 129-167: `passport.use(`, `passport.initialize()`, `passport.session()`, `_.bind(passport.authenticate, passport)`) and the session middleware.
  2. **Too few tokens.** js-ts `auth_markers` are only `req.session` and `passport.authenticate (`. js-ts `cookie_calls` is only `.cookie (`. bryony never calls `res.cookie(`: its session cookie is configured through middleware, `express.session({ secret: 'bryony', store: …, cookie: { maxAge: … } })` at `backend/server/dashboard/index.js:93-99`, with no secure, httpOnly or sameSite. The metric cannot see the most common way an Express app sets its session cookie.
- **Expected** (testable, user-confirmed 2026-09-30):
  1. The security pack selects files by **content** (registry auth, session and cookie tokens), not only by path. On bryony, `backend/server/dashboard/index.js` is quoted.
  2. The auth gate opens on bryony, citing the Passport/session code (index.js:163-164 or similar).
  3. Session-middleware cookie configuration counts as a cookie-setting statement: `express.session(…)`, `session(…)` from `express-session`, and `cookieSession(…)` from `cookie-session`, with their `cookie: {…}` options. Flags are judged inside that statement.
  4. On bryony, `cookie_flags_missing_observed` is **unmet**, citing `backend/server/dashboard/index.js:93` with no secure, httponly or samesite (T056 rule: an unset flag counts as unset, framework defaults included; the user chose not to exempt the httpOnly default). Security drops from 59 to about 50.
  5. kitchd (`/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd`) and ai-training (`/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training`) are re-run, with before/after per-dimension numbers pasted. A CLI-only repo still has the cookie rule left out (abstains through the gate), never scored 0.
  6. Every new registry token has a fetched and checked citation URL (DDR-0007).
- **Likely divergence point**: `dimensions/security.py` `collect` / `_ranked_candidates` / `_category` (path-only ranking before the evidence budget), and `registry/curated/js-ts.toml` `auth_markers` / `cookie_calls` (plus the same gap in other languages' session-middleware forms, if cheap and citable). `metrics.cookie_sites` / `_statement_end` must handle a multi-line `session({ … cookie: { … } })` statement.
- **Recent context**: T056 (merge `4b94744`, 2026-09-30) added the gate and the metric, verified only on the synthetic fixtures t056a/t056b. Its Done claim was not checked against a real repo; the user flagged this ("security is not implemented"). Do not touch evidence budgets (NFR-009): fix the *ordering and targeting* within the budget. Learnings: 200-line excerpt clipping must not produce findings (`metrics.excerpt_clipped`); use `</dev/null` for CLI `score`; `score` payloads repeat each metric per dimension pack, so filter by dimension.

### Intake

- **Trigger**: `.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project </dev/null`, then read the security rating's `unavailable_metrics` → `cookie_flags_missing_observed` (gate closed). `easy-verifier security --repo <bryony> --scope project` lists the 40 excerpt paths; index.js is absent.
- **Severity**: P1. A shipped feature is non-functional on real repos; there is no crash and no wrong score (it abstains honestly).
- **Affected area**: `src/easy_verifier/dimensions/security.py`, `src/easy_verifier/core/metrics.py` (cookie_sites / auth_lines), `src/easy_verifier/registry/curated/*.toml` (auth_markers, cookie_calls), `tests/`.

### Complexity & Risk

- **Complexity**: C3. It spans pack selection, metrics and the registry across languages.
- **Risk**: Medium. It changes which files the security pack quotes, which can move sink/redaction counts on every repo: report those deltas.

### Diagnosis Gates (Pillar 1 — must pass before any fix)

- [ ] Phase 1 feedback loop built and running (the bryony trigger above, plus a minimal fixture reproducing both causes)
- [ ] Bug reproduces deterministically on the loop
- [ ] 3–5 ranked falsifiable hypotheses listed (consistent with the confirmed mental model)
- [ ] Correct hypothesis identified via Phase 4 instrumentation

### Attempts Log (filled live during diagnosis — required if >1 hypothesis tested)

| # | Hypothesis | Predicted signal | Actual result | Verdict |
|---|---|---|---|---|

**Stuck checkpoint** (if 2 consecutive hypotheses disproven):
- [ ] 3 options presented (next hypothesis / widen scope / abandon+escalate)
- [ ] Chosen option: ___
- [ ] User's explicit go-ahead: ___

### Fix Gates (Pillar 2)

- [ ] Regression test written before the fix (or no-seam documented): a fixture shaped like bryony, with auth code in a file whose path carries no auth marker, many path-ranked decoys filling the budget, and `session({ cookie: { maxAge } })`
- [ ] Fix applied; regression test passes
- [ ] Phase 1 loop no longer reproduces the bug (bryony: gate open, rule unmet at index.js:93)
- [ ] Fix matches every "Expected" item 1–6 in the mental model
- [ ] STOP and report to the Supervisor, without merging, if the real-repo deltas move any other rating by more than 5 points

### Cleanup Checklist (Pillar 3)

- [ ] All [DEBUG-...] instrumentation removed (grep verified)
- [ ] Throwaway prototypes deleted
- [ ] Correct hypothesis stated in the commit message
- [ ] Post-mortem: what would have prevented this? (Expected: a real-repo run in the T056 acceptance criteria.)

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T058.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T058.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

## Files Must NOT Touch

| File | Reason |
|------|--------|
| dimension evidence budgets (`MAX_SECURITY_SOURCES`, pack byte budgets) | NFR-009 decisions |
| `RATING_RULES` weights | user-signed 2026-09-30 |

## Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project </dev/null
```
