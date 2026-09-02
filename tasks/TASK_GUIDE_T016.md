# TASK_GUIDE — T016: Dockerfile + compose, least-privilege container
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Common-Infrastructure-Agent
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/common-infrastructure.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Skim `memory/codebase-map.md` for layout

---

## Requirement (Pillar 1 — Adapt the requirement)

Package the MCP server so the harness can run it locally via Docker, with the least privilege that
still does the job.

**Restated intent**:
> A Dockerfile and compose configuration ship the MCP adapter as a `docker run -i` stdio server.
> Configuration comes from environment variables only, with no host-absolute paths baked in. The
> target repository mounts as a volume, read-only except for its `reports/` directory. The container
> runs as a non-root user, needs no elevated capabilities, and publishes no port.

**Out of scope**:
- Publishing an image to any registry (local-only, NFR-012).
- Orchestration beyond a single local container.
- The CLI adapter, which must keep working with no container at all (FR-021b).

**Requirement Refs**:
- FR-021a: Dockerfile + compose in v1; env-var configuration only; no host-absolute paths; target repo mountable as a volume; stdio by default so no port need be published
- FR-019a: stdio across the container boundary (`docker run -i`)
- FR-019b: if HTTP/SSE is enabled, loopback-bound even inside the container
- FR-021c: container paths must not leak into reports
- NFR-013: non-root user; target repo read-only except `reports/`; no elevated capabilities
- NFR-012: local-only; no outbound network
- NFR-006: `easy-ui-mcp` operational style

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T014 — the MCP server is what the container runs; there is nothing to package before it exists.

**Entry point**: `Dockerfile`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `docker run -i` speaks MCP over stdio and serves a real tool call against a mounted repo | FR-019a, FR-021a |
| 2 | The image runs as a **non-root** user — asserted by inspecting the running container's UID | NFR-013 |
| 3 | The compose config mounts the target repo **read-only**, with a separate writable mount or path for `reports/` only | NFR-013, NFR-007 |
| 4 | A write attempt anywhere in the target outside `reports/` fails at the filesystem level, not merely by application convention | NFR-013, NFR-007 |
| 5 | No capabilities are added; `cap_drop: ALL` (or equivalent) with only what is genuinely required added back | NFR-013 |
| 6 | No port is published in the default configuration | FR-021a, NFR-012 |
| 7 | All configuration arrives via environment variables; no host-absolute path appears in the Dockerfile or compose file | FR-021a |
| 8 | Reports written from inside the container contain no `/workspace`-style container paths | FR-021c |
| 9 | The container makes no outbound network request at runtime — build-time dependency installation is the only network use, and it happens at build only | NFR-012 |
| 10 | `git` is present in the image (T003's scope resolution needs it) and the mounted repo's git metadata is readable | FR-008 |
| 11 | Image build is reproducible enough to pin: base image and Python dependencies are version-pinned | Reproducibility |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `docker build` then `docker run -i` with this repo mounted, sending an MCP `tools/list` | 10 tools listed | automated/scripted test |
| 2 | `docker exec ... id -u` | Non-zero UID | scripted test |
| 3 | `docker exec ... touch /workspace/NOPE` | Permission denied | scripted test |
| 4 | `docker exec ... touch /workspace/reports/ok` | Succeeds | scripted test |
| 5 | A report generated inside the container | No `/workspace` string in the HTML | scripted test |
| 6 | `docker inspect` on the running container | No published ports; no added capabilities | scripted test |

### Verification Command (exact, runnable)

```bash
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T016.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T016.md`.

---

## Approach

**Pattern reference**: `None — no comparable prior art in this repo`. `NFR-006` names `easy-ui-mcp` as the style reference, but per `PRD.md` Open Question #2 it was **never fetched or verified** — approximate it from `REQUIREMENT.md` §4 and do not claim conformance the project cannot check.

Use a slim official Python base, pinned by digest or at minimum by exact tag. Install the package,
create an unprivileged user, drop to it, and set the entrypoint to the MCP server in stdio mode.

The mount arrangement in AC #3/#4 is the interesting part. The cleanest shape is the target repo
mounted read-only at a fixed container path, with `reports/` supplied as a second writable bind
mount over the corresponding subpath. That gives kernel-enforced write protection rather than
trusting the application — which matters because the application in question reads arbitrary source
trees looking for credentials, and NFR-013 exists precisely to bound what a bug in it can do.

AC #8 is the one most likely to be discovered late: it only manifests inside the container, and T013
implemented the normalization without being able to test it here. Verify it for real in this task.

Write the verification as a checked-in script (`scripts/verify_container.sh`) rather than as manual
steps, so T017 and every future change can re-run it.

---

## Edge Case Checklist

- [ ] Host UID/GID mismatch with the container user → `reports/` writes fail with a confusing permission error; handle or document explicitly (this is the single most common Docker bind-mount papercut)
- [ ] Target repo's `reports/` does not exist on the host before the run → the read-only mount makes creating it impossible from inside; the compose docs must say to create it first, or the mount arrangement must accommodate it
- [ ] SELinux/AppArmor hosts needing `:z`/`:Z` mount flags
- [ ] Repo containing symlinks pointing outside the mount → broken inside the container; behaviour should be an honest miss, not a crash
- [ ] `.git` present but owned by a different UID → git's `safe.directory` protection refuses to operate; handle explicitly
- [ ] Very large repo → mount performance, especially on macOS/Windows Docker Desktop
- [ ] stdin closed by the client → container exits cleanly, no zombie
- [ ] Build with no network available → fails at build (acceptable); runtime must never need the network
- [ ] Image layer caching hiding a stale package version → pin versions (AC #11)
- [ ] HTTP/SSE opt-in enabled inside the container → binds loopback, therefore unreachable from the host even with `-p`; document as intended (FR-019b)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `Dockerfile` | New — pinned slim Python base, non-root user, stdio entrypoint, `git` installed |
| `compose.yaml` | New — read-only repo mount, writable `reports/` mount, `cap_drop: ALL`, no ports, env-var config |
| `.dockerignore` | New — exclude `.git`, tests, caches from the build context |
| `scripts/verify_container.sh` | New — the AC #1–#6 checks as a runnable script |
| `README.md` | New or updated — how to run both Case A (container) and Case B (plain checkout) |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/**` | Packaging only; if the server needs a change to run in-container, raise it with the Supervisor as a T014 follow-up |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`scripts/verify_container.sh` covering AC #1–#6 with real `docker build` / `docker run` /
`docker inspect` — container properties cannot be honestly verified from a Python unit test.
Mark the script skippable in CI where Docker is unavailable, but it must run and be pasted as
evidence before this task is Done. The write-protection checks (AC #3/#4) are the load-bearing
ones: an application-level guarantee is not what NFR-013 asks for.

---

## Completion Checklist

- [x] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required; container privilege surface)
- [ ] Lint passes (Dockerfile lint / shellcheck where available)
- [ ] Tests written AND pass — `verify_container.sh` output pasted into `tasks/TASK_REVIEW_T016.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — harness connected to the containerised server for real
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
