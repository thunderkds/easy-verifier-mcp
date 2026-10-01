# TASK_REVIEW — T[NNN]: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t058_real_repo_auth_gate.py` (15 tests, written in T058; red before the fix: 6 failed): session-middleware cookie statements (`express.session(`, `session(`, `cookieSession(`); Passport markers; `passport.session()` is not a cookie statement; a bryony-shaped regression (auth code in a non-auth path behind >200 path-ranked decoys → gate opens, rule unmet); `peek_source` refuses `.env`, a symlink to `.env`, an escaping symlink and `../outside.js`, and records nothing; the pre-screen cap warning fires or not; `MAX_SECURITY_SOURCES` still binds — pass |
| Verification command run | ☑ pass | Supervisor 2026-09-30, worktree HEAD 3051020: `pytest -q` → `1615 passed, 2 skipped in 113.78s`; `ruff check src tests` → `All checks passed!` — pass |
| Negative cases hold | ☑ pass | kitchd and ai-training: the cookie rule still abstains through the gate ("no authentication or session code … found in 11 / 5 source-file excerpt(s)"), never 0; ai-training verified to have no auth/session/cookie code; kitchd has NestJS JWT auth (not a registry token, reported as a follow-up) but no cookie-setting code, so its score cannot change; peek refusals tested — pass |
| verify | ☑ pass | Supervisor independent CLI `score --scope project </dev/null` on 3 real repos: bryony security 59→50 (cookie_flags_missing_observed 3, earned 0/15: index.js:93, scraper/master.js:141, web/index.js:89, no secure/httponly/samesite; gate at dashboard/index.js:163-164, token.js:25), overall 77→75; kitchd 68 and ai-training 54 unchanged; bryony run time 9.2s→11.2s — feature confirmed working on a real repo, pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor review of `3a381b6..3051020`: context.py `_load` shared by `read_source`/`peek_source` (identical refusals; peek also ignores operator-approved secret reads, which is stricter), the models.py protocol, security `_prescreen` and ordering, js-ts.toml tokens. `RepoContext` is the only DimensionContext implementation. P0–P2: none. P3: `security.py` imports the private `metrics._is_source_file` and `roles._matcher`. Security: 4a is enforced in one place (`_load`), peeked text is never quoted, tokens are escaped — no findings — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1615 passed / 2 skipped (T056 merge: 1600) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | pure backend bugfix, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | pure backend bugfix, no UI component |
| **UI: Responsiveness at target viewports** | ☐ N/A | pure backend bugfix, no UI component |
| Repro loop | ☑ pass | see BEFORE: bryony `score` → cookie rule unavailable, gate closed in 12 excerpts; index.js ranked 788 of 1532 behind the 200-read cap — pass |
| Regression test | ☑ pass | `tests/test_t058_real_repo_auth_gate.py` (bryony-shaped regression, previously xfail(strict), now passing) — pass |
| Smoke suite | ☑ pass | 3-repo real run: only bryony security moved (−9, expected), no other rating moved by more than 5 — pass |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer 2026-09-30T07:32:26Z-07:33:08Z, worktree HEAD `3a381b6` (no fix commit exists), `PYTHONPATH=src <main>/.venv/bin/python -c 'from easy_verifier.adapters.cli import main; main()' score --repo <repo> --scope project </dev/null`:

```
2026-09-30T07:32:26Z
== bryony exit=0 07:32:35Z          (/home/hungnguyenhuu/workspace/project/bryony/bryony)
architecture             50  (30/60)
blast-radius             None  (0/0)
code-quality             100  (20/20)
requirement-fidelity     None  (0/0)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (75/75)
overall 77 (contributor_count 4)
COOKIE UNAVAILABLE: no authentication or session code (a registry auth_markers token) was found in 12 source-file excerpt(s) of registry languages with cookie tokens, so no cookie flag is ju...
== kitchd exit=0 07:32:38Z          (/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd)
architecture             100  (60/60)
blast-radius             None  (0/0)
code-quality             67  (30/45)
requirement-fidelity     15  (15/100)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (30/30)
overall 68 (contributor_count 5)
COOKIE UNAVAILABLE: no authentication or session code ... was found in 11 source-file excerpt(s) ...
== ai-training exit=0 07:32:40Z     (/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training)
architecture             70  (70/100)
blast-radius             None  (0/0)
code-quality             40  (10/25)
requirement-fidelity     0  (0/15)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (30/30)
overall 54 (contributor_count 5)
COOKIE UNAVAILABLE: no authentication or session code ... was found in 5 source-file excerpt(s) ...

2026-09-30T07:33:08Z  security --repo <bryony> --scope project </dev/null
files_read 225 excerpts 40   truncated False omitted_count 0
index.js read? False quoted? False      (backend/server/dashboard/index.js)
```

**AFTER**: the Phase 1 repro loop, re-run by the Supervisor on 2026-09-30 at worktree HEAD `3051020`:

```text
bryony 11.20s
 overall 75 {'architecture': 50, 'blast-radius': None, 'code-quality': 100, 'requirement-fidelity': None, 'security': 50, 'solution-fit': None, 'test-strategy': 100}
  cookie: 3 0 / 15
kitchd 3.19s
 overall 68 {'architecture': 100, 'blast-radius': None, 'code-quality': 67, 'requirement-fidelity': 15, 'security': 59, 'solution-fit': None, 'test-strategy': 100}
  cookie unavailable: ["cookie_flags_missing_observed", "no authentication or session code (a registry auth_markers token) was found in 11 source-file excerpt(s) ...
ai-training 1.72s
 overall 54 {'architecture': 70, 'blast-radius': None, 'code-quality': 40, 'requirement-fidelity': 0, 'security': 59, 'solution-fit': None, 'test-strategy': 100}
  cookie unavailable: ["cookie_flags_missing_observed", "no authentication or session code (a registry auth_markers token) was found in 5 source-file excerpt(s) ...
```

bryony cookie derivation (agent run 07:52:46Z, same values): "3 of 3 cookie-setting statement(s) leave a flag unset: backend/server/dashboard/index.js:93 (no secure, httponly, samesite), backend/server/scraper/master.js:141 (…), backend/server/web/index.js:89 (…); authentication or session code was read at backend/server/dashboard/index.js:163, :164, backend/server/dashboard/token.js:25".

**DELTA**: on a real Express/Passport app the #8 cookie rule now computes. It reads the session setup the path-ranked sweep never reached and judges session-middleware cookie config, so bryony's unflagged session cookies are reported at file:line (security 59→50), while repos without auth code still abstain.

**WITNESS**: Supervisor (main session), 2026-09-30, independent of the implementing agent's run.
