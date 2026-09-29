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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T056x.jsonl`, never the
implementing agent alone]
