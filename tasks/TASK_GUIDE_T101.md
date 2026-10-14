# TASK_GUIDE — T101: One shared scoring container that every repo points at (streamable HTTP, easy-ui-mcp style)
**Date**: 2026-10-14
**Complexity Level**: C2
**Risk Level**: High (changes the container's network posture and opens a local port; security-review mandatory)
**Priority**: P1
**Assigned agent**: common-infrastructure
**Agent guide**: `.claude/agents/common-infrastructure.md`
**Depends on**: none

## Feature Task Guide — T101

### Restated Intent (user, 2026-10-14)
"for the way to run the docker mcp each start the claude, I don't like this way too much, could we
support the way that it only 1 container for scoring, any repos needed will point into that to
score". Transport: "like the way to the easy-ui-mcp". That project runs
`docker compose up -d` once (`restart: unless-stopped`, `network_mode: host`), and each repo registers
`claude mcp add --transport http easy-ui-mcp http://localhost:8765/mcp`.

### Locked decisions (DDR-0013, local file `docs/ddr/0013-one-shared-http-container.md`; PRD FR-019b amended)
1. **Transport.** `easy-verifier-mcp --transport streamable-http` serves FastMCP streamable HTTP at
   `/mcp`, with the port from `EASY_VERIFIER_PORT` (default **8766**). Keep stdio as the default, and keep
   `--http` (legacy SSE) working unchanged.
2. **Bind.** Always `127.0.0.1`, and callers cannot configure the host (keep `LOOPBACK_HOST`). The
   shared compose service uses `network_mode: host`, so the container's loopback is the host's.
3. **Repos.** `EASY_VERIFIER_WORKSPACE` (an absolute host path, required for the shared service) is
   bind-mounted **read-only at the identical path**. Tool `repo` arguments are absolute host paths, so
   no path translation is needed and output paths are host paths (FR-021c). The Dockerfile git config
   must allow these repos (`safe.directory = *`); today it allows only `/workspace`.
4. **Reports.** New env `EASY_VERIFIER_REPORTS_DIR`. When it is set, `write_report` writes to
   `$EASY_VERIFIER_REPORTS_DIR/<repo directory name>/` instead of `<repo>/reports/`. When it is unset,
   behaviour is byte-identical to today. The shared service mounts
   `${EASY_VERIFIER_REPORTS:-$HOME/.easy-verifier-reports}` read-write at the same host path and sets
   the variable. The existing first-write advisory and the file-guard logic apply to the new directory.
5. **Concurrency.** One process serves many sessions. Serialise every tool call with one process-wide
   `threading.Lock` in the MCP adapter. Do not attempt to make the core thread-safe.
6. **Hardening kept.** Read-only rootfs, `cap_drop: ALL`, `no-new-privileges`, UID 10001, noexec
   tmpfs `/tmp`, init, `restart: unless-stopped`, and the SOT registry mount as today.
   `network_mode: none` is dropped **only for the new shared service**. The existing per-session
   `verifier` service and the `docker run -i` instructions stay as the alternative.
7. **No auth.** It is local-only (NFR-012). The docs state the exposure plainly: any local process
   can read, read-only, repos under the workspace root.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | `easy-verifier-mcp --transport streamable-http` binds 127.0.0.1:`$EASY_VERIFIER_PORT` (default 8766). A test asserts that the host can never be anything else, and that `--http` and stdio are unchanged |
| 2 | An MCP client over streamable HTTP (`mcp.client.streamable_http`) lists all tools and runs `score` on two **different** repos in one server process, and both results match the stdio adapter after the existing parity normalisation |
| 3 | `EASY_VERIFIER_REPORTS_DIR` set → the report lands in `<dir>/<repo name>/`, the repo is untouched, and the returned path is that file. Unset → byte-identical to today (existing report tests pass unedited) |
| 4 | Two concurrent `score` calls from two sessions both complete correctly (the lock serialises them; a test proves no interleaving) |
| 5 | `compose.yaml` has a new service (e.g. `scorer`) with `network_mode: host`, the read-only same-path workspace mount, the reports and SOT mounts, `restart: unless-stopped`, the hardening above, and command `--transport streamable-http`. The existing `verifier` service is unchanged |
| 6 | **Real container run** (run the network check first: a quick PyPI reachability probe, and if it fails, stop and report rather than retrying a long build). `docker compose build && EASY_VERIFIER_WORKSPACE=<real-repos parent> docker compose up -d scorer`. Then, from the host, an HTTP MCP client scores two real repos (aliases `k8s-ops` and `fullstack-ts`; paths in `.local/real-repos.md`) through the one container. Paste the overall values (k8s-ops 100, fullstack-ts 56 expected), `docker ps` showing exactly one scorer container, and a `write_report` path under the reports dir. Paste `grep -c /workspace` = 0 on the payloads |
| 7 | Rebuilding the image also turns the 2 stale container tests green (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`), or explains exactly why not. Full suite and `ruff check src tests` pass |
| 8 | `docs/DOCKER_MCP_GUIDE.md` and `README.md` lead with the shared-container way: (1) set the env and `docker compose up -d scorer` once; (2) `claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp` from any repo; (3) pass the absolute repo path. They also cover how to stop and upgrade, and state the exposure. The per-session stdio way is kept as an alternative section. The doc-truth tests (README commands pinned) are updated and pass |

### Files to Change (prediction, not contract)
`src/easy_verifier/adapters/mcp_server.py`, `src/easy_verifier/core/report.py` (reports dir only), `compose.yaml`, `Dockerfile`, `scripts/verify_container.sh` (if it should cover the shared service), `docs/DOCKER_MCP_GUIDE.md`, `README.md`, and new tests `tests/test_t101_shared_container.py`.

### Files Must NOT Touch
Scoring and evidence logic (`core/` apart from the report output directory, and `dimensions/`). No tracked file may contain a real repo name or path: use aliases. The guard test `tests/test_t100_no_personal_identifiers.py` enforces it.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Real repos
Aliases `k8s-ops`, `fullstack-ts`. Absolute paths are in the main checkout's `.local/real-repos.md` (local, git-ignored; read it from the main checkout, because worktrees do not have it). Agent worktrees have no `.venv`, so use the main checkout's interpreter with `PYTHONPATH=src`. Run long scans in the background with `</dev/null`. Stop the scorer container when done (`docker compose down scorer`) unless told otherwise.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T101.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T101.md`.

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.
