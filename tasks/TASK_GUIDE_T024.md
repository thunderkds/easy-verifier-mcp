# TASK_GUIDE — T024: MCP client setup guides (Docker + direct) referenced from README
**Date**: 2026-09-24
**Complexity Level**: C0
**Risk Level**: Low
**Priority**: P2
**Assigned agent**: Supervisor (docs-only; no `src/` change)
**Agent guide**: `.claude/agents/general-agent-template.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/general-agent-template.md`
5. Note the **Complexity Level** above (C0 — no brainstorm, single-pass verify)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-24): "guide me, how can I run the docker container as MCP" → "I don't see the guide
like that in this repos, add one and README will refer to it for easier?" → "Yes [trim README],
so the same with docker, the way to run directly should be as a guide and refer from README"

**Restated intent**:
> A user can register easy-verifier with an MCP client (Claude Code, JSON-configured clients)
> either as the hardened container (same hardening as `compose.yaml`) or directly on the host, by
> copying one documented command. Setup detail lives in two guides under `docs/`; README keeps only
> a short summary of each surface and links to them.

**Out of scope**:
- Any change to `Dockerfile`, `compose.yaml`, `src/`, or `scripts/`.
- Publishing the image to a registry.
- HTTP/SSE transport setup (deliberately unpublished — README §Docker).

**Requirement Refs**: none new — documents the existing T016 container surface.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] No new Requirement Refs

---

## Dependencies & Reachability

**Depends on**: T016 — image `easy-verifier-mcp:0.1.0` and `compose.yaml` hardening
**Entry point**: `docs/DOCKER_MCP_GUIDE.md` (linked from README §Docker)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `docs/DOCKER_MCP_GUIDE.md` documents a raw `docker run`, a `claude mcp add`, and a JSON client config | "guide me how to run the container as MCP" |
| 2 | Every documented `docker run` carries all `compose.yaml` hardening (read-only root, no network, drop ALL caps, no-new-privileges, noexec tmpfs, `:ro` target, writable reports) | same security boundary as Compose |
| 3 | No documented invocation allocates a TTY (breaks stdio) | the command must actually work |
| 4 | README links to both guides, and its MCP/Docker sections keep only a summary (no duplicated setup steps) | "README will refer to it" / trim follow-up |
| 6 | `docs/LOCAL_MCP_GUIDE.md` documents host-direct registration using the real `easy-verifier-mcp` entry point and real `--http` flag | "the way to run directly should be as a guide" |
| 5 | The documented command completes a real MCP handshake against the built image | the command must actually work |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | Guide + compose.yaml | ACs 1–4 hold | `tests/test_t024_mcp_guides.py` |
| 2 | Guide with one hardening flag / `:ro` / `-i` removed, or README link removed | test fails | sabotage probe |
| 3 | Built image, documented `docker run` | `initialize` + `tools/list` → 11 tools | live stdio probe |

### Verification Command

```bash
PYTHONPATH=src python -m pytest tests/test_t024_mcp_guides.py -q
```

---

## Approach

**Pattern reference**: `tests/test_t018_readme.py` — doc-truth test pinning documented commands;
`tests/test_t016_container_config.py` — static container-config assertions.

Write the guide as `console`/`json` fences (not `bash`) so no test executes Docker. The test parses
every direct `docker run` (console blocks + JSON `args`) and asserts each carries the token
sequences mapped from `compose.yaml` keys, so a compose hardening change without a guide update
fails CI.

---

## Edge Case Checklist

- [x] `-t`/`-it` in any invocation (stdio breaks) — pinned by test
- [x] Compose variant uses `--no-tty` (valid spelling per `docker compose run --help`)
- [x] `claude mcp add --scope` must precede `--` — stated explicitly
- [x] Relative/`~` paths not expanded by clients — stated explicitly
- [x] reports/ ownership (UID 10001) and SELinux `:z` — troubleshooting table

---

## Files to Change

| File | Change |
|------|--------|
| `docs/DOCKER_MCP_GUIDE.md` | new guide (also receives the manual Compose session moved out of README) |
| `docs/LOCAL_MCP_GUIDE.md` | new guide for host-direct MCP |
| `README.md` | trim §MCP and §Docker to summaries + links |
| `tests/test_t024_mcp_guides.py` | new doc-truth test |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `Dockerfile`, `compose.yaml`, `src/`, `scripts/` | docs-only task; container surface is T016's, already release-gated by T023 |

---

## Completion Checklist

- [x] Implementation done
- [x] Self-review
- [ ] Security review — N/A (Low risk, docs only)
- [x] Lint passes
- [x] Tests written AND pass — see `tasks/TASK_REVIEW_T024.md`
- [x] Live verify at the container MCP-stdio surface
