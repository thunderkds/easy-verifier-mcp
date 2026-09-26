# TASK_REVIEW — T026: Any-language source roles, `.easy-verifier.toml`, agent-input picks replay

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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t026_source_roles.py` (61 tests: AC1–10, AC12, plus Stage 4 P1 regressions `test_a_backtracking_config_glob_is_rejected_quickly_at_the_cli`, `test_config_glob_wildcards_are_bounded` ×4, `test_config_matcher_agrees_with_the_builtin_translation`); `tests/integration/test_adapter_parity.py::test_score_with_the_same_picks_matches_across_adapters` (AC11). Supervisor run 2026-09-26: `658 passed, 2 skipped in 27.19s` — pass |
| Verification command run | ☑ pass | `PYTHONPATH=src ../easy-verifier-mcp/.venv/bin/python -m pytest -q` → `658 passed, 2 skipped`; `ruff check src tests` → `All checks passed!`; agent: `docker compose build` exit 0, `scripts/verify_container.sh` → `PASS: uid=10001, tools=11, root=read-only, reports=writable, network=none, ports=none, caps=none` (pre-P1-fix; fix touches config matching only) — pass |
| Negative cases hold | ☑ pass | Supervisor adversarial probe: hostile config glob `**a**a**…**b` + 60-char filename — BEFORE fix: killed by `timeout 60` at 100% CPU (Stage 4 P1); AFTER `8e699b8`: exit 2 in 0.09s, `roles.spec-doc[0] … '**' must be a whole path segment`; allowed globs `**/*a*a*a*a`, `**/**/*a*a*a*b` finish in 0.12s. Picks/TOML validation matrices in test file (abs path, `..`, symlink escape, missing, unknown role, secret-bearing, unknown key, floor attempt) — pass |
| verify | ☑ pass | Rebuilt image `easy-verifier-mcp:t026`, `score` via Docker (read-only mount, `--network none`) on real repos vs v0.1.0 baseline 2026-09-26: kitchd 5→**7/7** rated (code-quality 41, security 50 newly rated; blast-radius 50→64), bryony 2→**5/7**, ai-training 3→**6/7**. Remaining abstentions are requirement-fidelity/solution-fit where no requirements docs exist — the T027 detect-gate target. Feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed 18 changed src files (`git diff b031e2d..HEAD -- src`) + callers of `score_repository`/`combined_pack`/`load_repo_config`/`validate_agent_input`; confirmed every `role_files` consumer reads via `context.read_source` (containment + DDR-0002). Built-in `security-review` skill could not run (no `origin/HEAD`); manual security pass done instead — 1 P1 (config-glob ReDoS) found and fixed, 0 other findings ≥75 confidence — pass |
| Full smoke suite still green (no regression) | ☑ pass | 658 passed, 2 skipped (baseline 596 passed, 2 skipped); existing-test changes are role-key lookups, each commented; architecture snapshot 0.6→1.0 (3/5 files → 3/3 roles, excerpts byte-identical) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend/CLI/MCP task — no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend/CLI/MCP task — no UI component |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend/CLI/MCP task — no UI component |

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
