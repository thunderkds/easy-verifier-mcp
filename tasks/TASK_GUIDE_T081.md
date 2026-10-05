# TASK_GUIDE — T081: Guide for checking a feature or bugfix (changes scope)
**Date**: 2026-10-05
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Supervisor (docs-only)
**Agent guide**: `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-05): "did you add it to the document guide, like 'hey, if you want to run verify the
change, let use the flag or command, ...'" → "yes, add it".

Supervisor finding (develop `fae8969`): `--scope changes` is named only in passing
(`SCORING_FLOW.md:73`, `EVALUATION_GUIDE.md:83`, `AREA_COVERAGE.md:45`). Neither README nor
`DOCKER_MCP_GUIDE.md` tells a user how to rate a branch or a bugfix. Three facts a user needs and
cannot learn today:
1. A bare commit/branch name in `--ref` is that one commit against its parent
   (`scope._normalize_range`), not the whole branch. A whole branch needs `main...HEAD`.
2. `score` reads optional findings JSON from stdin when stdin is not a TTY
   (`cli._read_findings`); an agent/script shell that leaves stdin open waits forever. Observed in
   this session: a `score --scope changes` run hung until a 300 s timeout; the same run with stdin
   closed took 11 s.
3. A change score is partial: on a real one-file bryony bugfix with no test
   (`09be767d0~1...09be767d0`) `score` gave 97 (architecture 90, code-quality 100, blast-radius 100;
   test-strategy, security, requirement-fidelity abstained `below_coverage_floor`).

**Restated intent**:
> A user reading README or the Docker guide can rate a feature/bugfix branch with one copied command
> (CLI) or one sentence (MCP), knows the range semantics, and is told plainly that today's change
> score does not penalise a missing regression test.

**Out of scope**: any `src/` change (change-risk rules, repo-wide context roles in changes scope,
symbol-level reach, stdin behaviour) — that is the change-risk vision, to be planned separately.

**Requirement Refs**: FR-008 (changes scope from local git), FR-066 (evaluation docs).

### Requirement Fidelity Gate

- [x] Restated intent matches the request
- [x] Each fact cites the code or the run it comes from
- [x] Every AC traces to the Requirement
- [x] Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `README.md` § Scopes

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | README has "Checking a feature or bugfix" with the CLI command `score --repo . --scope changes --ref main...HEAD < /dev/null`, the worktree alternative and the MCP arguments | FR-066 |
| 2 | README states a bare commit/branch name is one commit, and three dots rate the whole branch only — and a test pins both behaviours on a real git repo | FR-008, FR-066 |
| 3 | README explains the stdin wait and states the change score is partial (missing test not penalised), with the dated bryony example | FR-066 |
| 4 | `DOCKER_MCP_GUIDE.md` § 5 tells MCP users the sentence to ask and the `scope`/`ref` the tool takes, and points to the README limits | FR-066 |
| 5 | Existing README doc-truth test (T018) still passes; full suite passes | FR-066 |

### Verification Command

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_t081_change_check_guide.py tests/test_t018_readme.py -q
```

## Files to Change

| File | Change |
|---|---|
| `README.md` | new `### Checking a feature or bugfix` under § Scopes (`console` fence: not executed by T018) |
| `docs/DOCKER_MCP_GUIDE.md` | new `## 5. Check a feature or bugfix` (tracked file under gitignored `docs/`) |
| `tests/test_t081_change_check_guide.py` | new |

---

## Evidence

| Gate | Result | Evidence |
|---|---|---|
| New test(s) cover acceptance criteria | ☑ pass | `tests/test_t081_change_check_guide.py` (5 tests: AC 1/3/4 doc pins, AC 2 range semantics on a real tmp git repo — `main...HEAD` → `("one.py", "two.py")`, bare `feature` → `("two.py",)`). Against the pre-change docs (`git stash` of README + guide): `3 failed, 2 passed in 1.55s`; after: `5 passed in 0.24s`. With T018: `11 passed, 1 skipped in 39.30s` |
| Full suite passes | ☑ pass | `2006 passed, 2 skipped in 296.91s`; `ruff check` → All checks passed; `ruff format --check` → 1 file already formatted. A first run gave `1 failed, 2005 passed` while `tasks/TASK_GUIDE_T081.md` was being written mid-run; all 33 doc/scope/CLI test files passed in isolation and the rerun passed — cause not confirmed, recorded as an unreproduced flake |
| Real-repo command works | ☑ pass | bryony (`project/bryony/bryony`), develop `fae8969`: `score --repo . --scope changes --ref 09be767d0~1...09be767d0 < /dev/null` → overall 97, contributors architecture 90 / code-quality 100 / blast-radius 100; abstained solution-fit `no_static_rule`, requirement-fidelity / security / test-strategy `below_coverage_floor` |
| code-review | ☑ pass | Supervisor self-review (C1 docs-only): every claim traced to code or a run — range semantics to `scope._normalize_range` and the AC 2 tests, stdin to `cli._read_findings`, the 97 example to the bryony run above; `console` fence so T018 never executes the command. No P0–P2 findings. Noted, not fixed (out of scope): FR-066 names EVALUATION_GUIDE as the single place to read a score — the partial-score caveat should move there when change-risk rules are planned |
| UI visual regression | ☐ N/A | docs-only, no UI |
| UI design-system compliance | ☐ N/A | docs-only, no UI |
| UI responsiveness | ☐ N/A | docs-only, no UI |
