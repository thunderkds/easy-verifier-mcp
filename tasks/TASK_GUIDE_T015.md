# TASK_GUIDE — T015: cli.py — full CLI adapter surface
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Skim `memory/codebase-map.md` for layout

---

## Requirement (Pillar 1 — Adapt the requirement)

Finish the CLI so Case B — an engineer with an ordinary repo and an agent CLI, no container, no
server — has the complete surface the MCP adapter has.

**Restated intent**:
> `cli.py` grows from the T001 tracer-bullet stub into the full adapter: all seven dimensions,
> discovery, combined pack, and `write_report` (`--findings <path>`, or stdin JSON when the flag is
> omitted). It runs from a plain checkout with no container and no server process, and produces
> output identical to the MCP adapter's for the same inputs.

**Out of scope**:
- Any engine logic (FR-021).
- Interactive prompting — the caller is an agent, not a human at a terminal.

**Requirement Refs**:
- FR-020: CLI adapter running the same dimensions against a repo given by path, no server process
- FR-021: delegate to one shared core; no logic of its own
- FR-021b: runnable with no container and no server, from a plain checkout
- FR-022: identical evidence packs and report output vs. the MCP adapter for the same inputs
- FR-013a: discovery available in both adapters
- FR-014: `write_report` exposed
- `PRD.md` Q5: `--findings <path>`, or stdin JSON when the flag is omitted; both call the identical core path

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T011 — discovery; T013 — `write_report()`. (Earlier tasks each added their own flags to the stub; this task completes and unifies the surface.)

**Entry point**: `easy-verifier` (console script)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Subcommands exist for all 7 dimensions, `list-dimensions`, `combined`, and `write-report` — the same operation set the MCP adapter exposes | FR-020, FR-013a, FR-014 |
| 2 | `--repo <path>` is accepted everywhere a target is needed; `--scope`, `--task`, `--range`, `--budget-bytes` are supported where meaningful | FR-006, FR-011a |
| 3 | `write-report` accepts `--findings <path>` **or** stdin JSON when the flag is omitted, and both take the identical core path | `PRD.md` Q5, FR-022 |
| 4 | Runs from a plain checkout with no container, no server, no config file | FR-021b, NFR-005 |
| 5 | Contains no file reading of target-repo content, no excerpt building, no coverage arithmetic, no rendering — asserted structurally | FR-021 |
| 6 | Output is machine-readable JSON by default (the caller is an agent), and is byte-identical to the MCP adapter's for the same inputs modulo the T017 normalization | FR-022 |
| 7 | Exit codes are meaningful: 0 success, non-zero distinct codes for validation failure vs. operational error | Usability |
| 8 | Errors go to stderr; only the result payload goes to stdout, so the output can be piped | Usability |
| 9 | `--help` lists every dimension with its purpose, sourced from `list_dimensions()` rather than hardcoded | FR-013a |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `easy-verifier list-dimensions` | 7 dimensions with purposes and `sources_sought` | automated test |
| 2 | `easy-verifier security --repo . --scope project` | Valid JSON pack on stdout, exit 0 | automated test |
| 3 | Valid findings JSON piped on stdin to `write-report` | Report written; path reported; exit 0 | automated test |
| 4 | The same findings via `--findings f.json` | Byte-identical result to the stdin path | automated test |
| 5 | Findings missing a confidence value | Validation error on stderr, no report written, distinct non-zero exit code | automated test |
| 6 | Fresh clone, `pip install -e .`, no Docker running | Every subcommand works | manual + automated |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t015_cli.py -q && \
  easy-verifier list-dimensions && \
  easy-verifier architecture --repo . --scope project >/dev/null && echo "exit=$?"
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T015.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T015.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/adapters/mcp_server.py` (T014) — the sibling adapter; mirror its structure and its tool-generation-from-descriptors approach.

Generate the seven dimension subcommands from the descriptors in a loop, for the same reason T014
generates its tools that way: hand-writing them twice guarantees the two adapters drift, and FR-022
parity is a hard requirement tested in T017.

Use `argparse` from the standard library. This is a small, stable command surface and an agent is
the primary caller, so a third-party CLI framework buys nothing here.

The stdin-vs-`--findings` equivalence (AC #3/#4) should be enforced by structure: read the bytes
from whichever source, then call one function. Two parse paths is how they diverge.

---

## Edge Case Checklist

- [ ] `--repo` omitted → defaults to cwd, or errors; decide, document, keep consistent with the MCP adapter
- [ ] `--repo` pointing at a nonexistent path, a file, or a path without read permission
- [ ] Relative vs. absolute repo paths → same result
- [ ] stdin is a TTY (no piped input) and `--findings` omitted → clear error rather than hanging forever waiting on stdin
- [ ] Both `--findings` and piped stdin supplied → defined precedence, stated in `--help`
- [ ] Malformed JSON on stdin → parse error naming the position, non-zero exit
- [ ] Empty stdin
- [ ] Output piped into a tool that closes early (`| head`) → `BrokenPipeError` handled, not a traceback
- [ ] Non-UTF-8 locale environment
- [ ] Very large JSON output → streamed or written efficiently, not built as one giant string if avoidable
- [ ] `--scope task` without `--task` → clear error naming the missing argument
- [ ] Unknown dimension name → error listing the valid ones from `list_dimensions()`

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/adapters/cli.py` | Complete the surface: subcommand generation, `write-report`, exit codes, stderr/stdout discipline |
| `pyproject.toml` | `easy-verifier` console script entry point |
| `tests/test_t015_cli.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/**`, `dimensions/**` | Fixed contracts — the adapter calls them and adds nothing |
| `src/easy_verifier/adapters/mcp_server.py` | Owned by T014 — if parity requires a change there, raise it with the Supervisor |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t015_cli.py` — invoke through `subprocess` (real argv, real exit codes, real stdio
separation) rather than by calling `main()` in-process, since AC #7 and #8 are precisely about
process-level behaviour. Include the stdin/`--findings` equivalence test as a byte comparison. Add
the structural thinness test for AC #5, mirroring T001's.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T015.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — full surface exercised from a plain checkout with no Docker
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
