# TASK_GUIDE — T014: mcp_server.py — FastMCP adapter, stdio default
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Medium
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

Expose the engine to an agent harness over MCP, locally, without opening anything to the network.

**Restated intent**:
> A FastMCP server exposes all seven dimensions, discovery, the combined pack and `write_report` as
> MCP tools. It speaks **stdio** by default and by requirement, across the container boundary. An
> HTTP/SSE transport exists only as an opt-in flag and binds `127.0.0.1` exclusively. The adapter
> holds no evaluation, context-loading or rendering logic of its own.

**Out of scope**:
- Any engine logic — this is a transport shell (FR-021).
- Docker packaging (T016).
- Authentication (out of scope by design: the server is local and single-user; see `PRD.md` Out of Scope).

**Requirement Refs**:
- FR-019: MCP adapter serving all dimensions, discovery and `write_report`, registrable in Claude Code and the harness; connected locally via Docker, never the internet
- FR-019a: stdio is the default and required transport, spoken across the container boundary
- FR-019b: HTTP/SSE is opt-in and must bind `127.0.0.1` only, never `0.0.0.0`, including in a container
- FR-021: adapters delegate to one shared core with no logic of their own
- FR-013a: discovery available in both adapters
- NFR-006: `easy-ui-mcp` operational style
- NFR-008: Python + `mcp` SDK (FastMCP)
- NFR-012: local-only; no outbound request; no externally-reachable listening socket

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T011 — `list_dimensions()` is one of the exposed tools; T013 — `write_report()` is another, and the tool surface is not complete without it.

**Entry point**: `mcp_server`

**SDK compatibility decision (2026-09-02)**: The approved guide names FastMCP and legacy SSE.
Current `mcp` v2 replaces FastMCP with `MCPServer`; the official SDK advises v1 applications to
constrain the dependency below v2 until migrated. T014 therefore uses `mcp>=1.29,<2`, tested against
locally available v1.29.0, so maintained v1 patch releases remain eligible without admitting the
breaking v2 API.

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Exposes as MCP tools: each of the 7 dimensions, `list_dimensions`, the combined pack, and `write_report` | FR-019, FR-013a |
| 2 | Default transport is stdio, with no port, no bind address and no server lifecycle to manage | FR-019a |
| 3 | HTTP/SSE is available **only** behind an explicit opt-in flag/env var, off by default | FR-019b |
| 4 | When HTTP/SSE is enabled, the bind address is hard-wired to `127.0.0.1` — a test asserts `0.0.0.0`, `::`, and any routable address are impossible to configure, including via env var | FR-019b, NFR-012 |
| 5 | Contains no file reading, no excerpt building, no coverage arithmetic and no rendering — asserted structurally | FR-021 |
| 6 | Tool schemas are derived from the same descriptors as `list_dimensions()`, not hand-written per tool | FR-013a, DRY |
| 7 | The server itself makes no outbound network request | NFR-012 |
| 8 | Tool errors are returned as structured MCP errors, not raised as unhandled exceptions that kill the server | Robustness |
| 9 | Output for a given input matches the CLI's for the same repo, scope and dimension | FR-022 |
| 10 | Nothing is logged to **stdout** — stdio transport owns stdout, so all logging goes to stderr | FR-019a |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Server started with no arguments | stdio transport; no socket bound (verified by inspecting open sockets for the process) | automated test |
| 2 | An MCP `tools/list` request | 10 tools: 7 dimensions + discovery + combined + write_report | automated test |
| 3 | `security` tool called with this repo | Same pack the CLI produces for the same arguments | automated test |
| 4 | HTTP/SSE enabled with `BIND=0.0.0.0` in the environment | Refused or forced to `127.0.0.1` — never binds a routable address | automated test |
| 5 | A tool called with an invalid repo path | Structured MCP error; server still alive and serving | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t014_mcp_server.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T014.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T014.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/adapters/cli.py` (T001 onward) — the sibling adapter. Whatever the CLI does *not* do, this must not do either; the two should be near-mirror images over the same core calls.

Generate the seven dimension tools from the descriptors in a loop (AC #6). Seven hand-written tool
functions is seven places for the CLI and MCP surfaces to drift apart, and FR-022 parity is tested
in T017 — make drift structurally hard now rather than debugging it then.

AC #4 is the security-relevant one. The requirement is not "default to loopback", it is that a
routable bind must be *impossible*. Hard-wire the host rather than defaulting it, so no env var,
flag or config file can widen it. This matters most inside a container, where `127.0.0.1` and
`0.0.0.0` behave very differently with respect to published ports.

AC #10 is the classic stdio-MCP bug: one stray `print()` or a logging handler defaulting to stdout
corrupts the protocol stream, and the failure looks like a mysterious client-side parse error rather
than a logging mistake. Configure logging to stderr explicitly at startup.

---

## Edge Case Checklist

- [ ] A `print()` or stdout log anywhere in the imported code path corrupts stdio → assert stdout is protocol-only
- [ ] Client disconnects mid-tool-call → server exits cleanly, no orphaned work
- [ ] A tool call with a repo path outside any mounted volume (container case) → clear error
- [ ] Relative repo path → resolved against a documented base, not silently against the server's cwd
- [ ] Long-running dimension on a huge repo → bounded by the budget; no protocol timeout mystery
- [ ] Two concurrent tool calls → no shared mutable state between them
- [ ] `write_report` called with a target repo the server cannot write to → structured error naming the path
- [ ] Very large pack returned over stdio → within the budget by construction, but confirm the transport handles it
- [ ] HTTP/SSE mode enabled inside a container with a published port → still loopback-bound, and therefore deliberately not reachable from the host; document that this is intended, not a bug
- [ ] MCP SDK version differences in tool registration API → pin the dependency

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/adapters/mcp_server.py` | New — FastMCP server, tool registration loop, transport selection |
| `pyproject.toml` | Add the `mcp` dependency pin and a console entry point |
| `tests/test_t014_mcp_server.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/**` | Fixed contracts — the adapter calls them and adds nothing |
| `src/easy_verifier/dimensions/**` | Owned by T001/T007–T010 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t014_mcp_server.py` — drive the server in-process through the MCP SDK's test harness
where available, otherwise over a real stdio pipe. The bind-address test (AC #4) should be a
structural assertion over the module plus a runtime attempt with a hostile env var, since this is a
security property and a runtime-only test would miss a future config path that reintroduces it.
Structural test for AC #5 mirroring the CLI thinness test from T001.

---

## Completion Checklist

- [x] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required; network surface)
- [x] Lint passes
- [x] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T014.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — server registered and called from a real MCP client
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [x] Supervisor notified: task ready for Stage 4 review
