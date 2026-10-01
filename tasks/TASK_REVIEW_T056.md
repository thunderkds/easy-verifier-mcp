# TASK_REVIEW — T056: Area rule groups needing new evidence (#8, #17 strict config)

> Sibling of `tasks/TASK_GUIDE_T056.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t056_auth_and_type_config.py` (92 tests, written as part of T056): SC1 `test_a_session_cookie_without_httponly_is_unmet_with_file_and_line`; SC2 `test_no_cookie_code_abstains_with_a_bounded_reason_never_zero`, `test_a_cli_only_repo_abstains_naming_both_absences`; AC2 gate `test_cookie_code_without_auth_code_abstains_naming_what_was_found`; SC3 `test_tsconfig_without_strict_is_unmet_and_cited`; AC5 signed tables sum to 100, `gate.required_fields()` == 16, a closed gate leaves the cookie rule out of the rating (never 0). Supervisor run: `1600 passed, 2 skipped in 94.79s` — pass |
| Verification command run | ☑ pass | Supervisor, 2026-09-30, worktree HEAD 8b647c0: `python -m pytest -q` → `1600 passed, 2 skipped in 94.79s (0:01:34)`; `python -m ruff check src tests` → `All checks passed!` — pass |
| Negative cases hold | ☑ pass | CLI-only repo (t056b): the cookie metric abstains through the auth gate ("no authentication or session code ... found"), never 0; no type-checker config → the strict metric abstains; `resolve_extends` refuses `../../x.json` beyond the root and absolute paths (probed); `strict_optional = true` / `"alwaysStrict": true` do not match the strict tokens (probed); extends never reads a secret-bearing file (`test_extends_never_reads_a_secret_bearing_file`) — pass |
| verify | ☑ pass | Supervisor ran `verify`: CLI `score --scope project </dev/null` on t056a → security 70 (cookie_flags_missing_observed value 1, w 15, earned 0, `src/app/auth.py:10 (no httponly)`, gate opened at auth.py:8), code-quality 76 (strict_type_config_missing value 2, w 10: tsconfig.json unset, pyproject [tool.mypy] unset); t056b → the cookie metric abstains via the auth gate, strict = 1 (mypy.ini:1-2). MCP stdio `score` with the same args: payload identical to the CLI except the MCP-only `needs_input` key (DDR-0006, by design) — feature confirmed working, pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor `code-review` over `375a63b..8b647c0`: metrics.py (cookie_sites, auth_lines, type_config_sections, extends_targets, resolve_extends, the two metrics), code_quality._type_config_excerpts, security collect/_sink_excerpts, registry fields, judge RATING_RULES, 9 curated TOMLs, pinned-test updates (T028 60→55 arithmetic checked: the new strict rule fails in the `_rating_*` fixture). Findings: P0 0, P1 0, P2 0, P3 1 (security.py imports the private `roles._matcher`; optional). Security pass (manual; the built-in `security-review` needs an `origin` remote and this repo uses `github`): read_source confines reads to the repo incl. symlinks, secret files are refused unread, tokens are `re.escape`d (no ReDoS), quoted lines go through the redaction seam — no findings. Skipped: unrelated dimensions — pass |
| Full smoke suite still green (no regression) | ☑ pass | Full suite 1600 passed / 2 skipped (baseline before T056: 1539); the 8 older pins were updated only for the signed weight change and the 14→16 required-field count — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | ☐ N/A | pure backend task, no UI component |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**:

Fixtures (`<scratchpad>/t056a` and `<scratchpad>/t056b`, one git commit each).
`t056a`: `src/app/auth.py` (Flask `session[...]` plus `resp.set_cookie("session_id", ..., secure=True,
samesite="Lax")` — no `httponly`), `tsconfig.json` without `strict`, `pyproject.toml` `[tool.mypy]`
without `strict`, `docs/offboarding.md` present, `README.md`. `t056b`: a CLI-only `src/tool/cli.py`
(no session or cookie code), `mypy.ini` without `strict`, no offboarding doc, `README.md`.
`summarize.py` prints security's and code-quality's rule inputs (with area), unavailable metrics,
documentation results, and any metric whose name mentions cookie/session/auth/strict/offboard/type_config.

```text
captured: 2026-09-29T11:11:24Z  worktree HEAD=375a63b (no T056 implementation commit yet)
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t056a --scope project </dev/null > t056a_before.json; python summarize.py t056a_before.json
score exit=0
code-quality: rating value=88 reason=None
   rule functions_over_ccn_10_share [Maintainability, reuse, library judgment, patterns] value=0.0 w=30 passed=True
   rule max_function_ccn [Maintainability, reuse, library judgment, patterns] value=1 w=15 passed=True
   rule lint_config_missing [Type safety & code quality] value=0 w=15 passed=True
   rule format_config_missing [Type safety & code quality] value=1 w=10 passed=False
   rule type_escapes_per_kloc [Type safety & code quality] value=0.0 w=15 passed=True
   unavailable ['todo_without_ticket_share', "no debt marker was found in the comments of 1 source-file excerpt(s), so the share has a zero denominator; that is not a share of 0. debt markers are TODO, FIXME, XXX or HACK as whole words inside comments (the registry's comment delimiters; a marker in a string is not a comment); a marker has a ticket when its comment names a KEY-123 issue key, a #123 reference or a URL; only source-file excerpts of registry languages are read, so this describes the quoted code, not the repository"]
security: rating value=80 reason=None
   rule redaction_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule sink_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule lockfile_missing [Dependencies, vulns, licenses, obsolescence] value=1 w=20 passed=False
metric names computed: 35
  metric name containing 'cookie': []
  metric name containing 'session': []
  metric name containing 'auth': []
  metric name containing 'strict': []
  metric name containing 'offboard': []
  metric name containing 'type_config': []
area 'AuthN/Z, sessions, offboarding' rated inputs: []
area 'AuthN/Z, sessions, offboarding' documentation results: []
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t056b --scope project </dev/null > t056b_before.json; python summarize.py t056b_before.json
score exit=0
code-quality: rating_abstention value=None reason=below_coverage_floor
security: rating_abstention value=None reason=below_coverage_floor
metric names computed: 35
  metric name containing 'cookie': []
  metric name containing 'session': []
  metric name containing 'auth': []
  metric name containing 'strict': []
  metric name containing 'offboard': []
  metric name containing 'type_config': []
area 'AuthN/Z, sessions, offboarding' rated inputs: []
area 'AuthN/Z, sessions, offboarding' documentation results: []
```

No cookie, session, auth, strict-type-config or offboarding metric exists; area #8
"AuthN/Z, sessions, offboarding" carries no rated input and no documentation result on either fixture,
and code-quality has no strict-config rule although both fixtures ship a type-checker config without
`strict`.

**AFTER**:

```text
captured: 2026-09-30T04:38:24Z  worktree HEAD=8b647c0 (Supervisor)
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t056a --scope project </dev/null
score exit=0
code-quality rating 76
   rule functions_over_ccn_10_share value= 0.0 w= 25 earned= 25 passed= True
   rule max_function_ccn value= 1 w= 15 earned= 15 passed= True
   rule lint_config_missing value= 0 w= 10 earned= 10 passed= True
   rule format_config_missing value= 1 w= 10 earned= 0 passed= False
   rule type_escapes_per_kloc value= 0.0 w= 15 earned= 15 passed= True
   rule strict_type_config_missing value= 2 w= 10 earned= 0 passed= False
     (2 of 2 language(s) ... enable no strict mode: js-ts: tsconfig.json:1-5 (unset); python: pyproject.toml:4-5 [tool.mypy] (unset))
security rating 70
   rule redaction_hits_observed value= 0 w= 35 earned= 35 passed= True
   rule sink_hits_observed value= 0 w= 35 earned= 35 passed= True
   rule lockfile_missing value= 1 w= 15 earned= 0 passed= False
   rule cookie_flags_missing_observed value= 1 w= 15 earned= 0 passed= False
     (1 of 1 cookie-setting statement(s) leave a flag unset: src/app/auth.py:10 (no httponly); authentication or session code was read at src/app/auth.py:8)
security documentation: [('AuthN/Z, sessions, offboarding', 'present', 'docs/offboarding.md')]
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t056b --scope project </dev/null
score exit=0
code-quality: rating_abstention below_coverage_floor
security: rating_abstention below_coverage_floor
code-quality strict_type_config_missing: 1 (python: mypy.ini:1-2 [mypy] (unset))
cookie_flags_missing_observed: no value: no authentication or session code (a registry auth_markers token) was found ... a repository without such code (a CLI, a library) is not rated on cookies; no cookie-setting statement was found
security documentation: [('AuthN/Z, sessions, offboarding', 'missing', None)]
```

**DELTA**: security now rates session-cookie flags (area #8) only where auth/session code was read and reports offboarding documentation as present/missing, and code-quality rates strict type-checker config (area #17). On t056a, security moves 80→70 and code-quality 88→76, with cited file:line evidence; a CLI-only repo is never scored on cookies.

**WITNESS**: Supervisor (main session), 2026-09-30T04:38Z, independent of the implementing agent's own run.
