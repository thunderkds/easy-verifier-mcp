# TASK_REVIEW — T026: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T026.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured by backend-developer at worktree HEAD `b031e2d`, before any T026 implementation
commit). Fixture: an Elixir-shaped repo (no ecosystem table) built in the session scratchpad —
`README.md`, `CONTRIBUTING.md`, `docs/specs/{requirements,architecture}.md`, `.formatter.exs`,
`mix.exs`, `mix.lock`, `lib/app/greeter.ex`, `test/{greeter_test,test_helper}.exs`,
`.github/workflows/ci.yml`, `Dockerfile`, one git commit.

```
$ git log --oneline -1 && date -u
b031e2d plan(T026-T028): add task review files from template
Sat Sep 26 03:11:11 PM UTC 2026
$ PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/elixir_demo \
    | python3 -c "...print(dimension, value, reason_code, achieved_coverage)...;print(overall.disclosure)"
architecture None below_coverage_floor 0.2
blast-radius None below_coverage_floor 0.125
code-quality 64
requirement-fidelity None below_coverage_floor 0.0
security None below_coverage_floor 0.18181818181818182
solution-fit None below_coverage_floor 0.0
test-strategy None below_coverage_floor 0.1111111111111111
1 of 7 dimensions contributed; ratings average contributors only, so abstention can raise the overall; abstained: architecture (below_coverage_floor: achieved coverage is below the declared floor), solution-fit (below_coverage_floor: achieved coverage is below the declared floor), requirement-fidelity (below_coverage_floor: achieved coverage is below the declared floor), security (below_coverage_floor: achieved coverage is below the declared floor), test-strategy (below_coverage_floor: achieved coverage is below the declared floor), blast-radius (below_coverage_floor: achieved coverage is below the declared floor)
```

**AFTER** (backend-developer, same fixture, same command; HEAD `9f12a06` plus uncommitted
formatting/comment/test/doc edits, with no logic change since that commit; one extra line printing the
new `provenance` field):

```
$ git log --oneline -1 && date -u
9f12a06 feat(T026): WIP source roles, .easy-verifier.toml, agent-input picks
Sat Sep 26 03:34:51 PM UTC 2026
$ PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/elixir_demo | python3 -c "..."
architecture 82
blast-radius 64
code-quality 82
requirement-fidelity 82
security 64
solution-fit 64
test-strategy 82
7 of 7 dimensions contributed; ratings average contributors only, so abstention can raise the overall; none abstained
['rules', 'rules', 'rules', 'rules', 'rules', 'rules', 'rules']
```

**DELTA**: An Elixir repository with no ecosystem table goes from 1 of 7 dimensions rated (6
abstaining below their coverage floor) to 7 of 7 rated. Its roles are filled by language-agnostic
patterns, and each dimension says where its sources came from.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
