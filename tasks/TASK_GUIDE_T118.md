# TASK_GUIDE — T118: Pull-and-run image `temvar/easy-verifier-mcp:0.1.0` from current code
**Date**: 2026-10-19
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: common-infrastructure
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (Deployment target, NFR-012) and `memory/MEMORY.md`
2. Read this file completely
3. Read `.claude/agents/common-infrastructure.md`
4. Read `docs/DOCKER_MCP_GUIDE.md`, `compose.yaml`, `Dockerfile`, `docs/RELEASE_GUIDE.md`
5. Read the cancelled T025 work for reuse: `git show feat/T025-image-publish:scripts/publish_image.sh` and `git show feat/T025-image-publish:tests/test_t025_image_publish.py` (its docs diff is stale — written before the shared-container rewrite; do not reuse the docs)
6. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-19, on the landing page: *"for the guide to install, it looks complicated, let focus on the simple way is pull the docker images and run first, the others comes later"*. Asked how, given no image of the current code exists: *"let build it for now and use the 0.1.0 also"*.

**Restated intent**:
> Make `temvar/easy-verifier-mcp:0.1.0` (and `:latest`) an image of the **current** code that a newcomer can pull and run as the shared scoring server with two commands (pull, run) plus one `claude mcp add` line — no clone, no compose. Document that path first in `docs/DOCKER_MCP_GUIDE.md` and `README.md`, prove it works against the locally built image, and leave a guarded publish script for the operator. The agent builds locally; it never pushes to Docker Hub.

**Out of scope**:
- Pushing to Docker Hub (operator; it **replaces** the existing `temvar/easy-verifier-mcp:0.1.0` built 2026-10-05 from `fae8969` — user decision 2026-10-19)
- arm64 / multi-arch (amd64 only, as T025's amendment)
- Changing `pyproject.toml` version (stays `0.1.0`)
- The landing page (`site/**`, T119)
- Any `src/` behaviour change

**Requirement Refs**: `PROJECT_SPEC.md` Deployment target (shared streamable-HTTP container, loopback 127.0.0.1:8766, DDR-0013), NFR-012 (never internet-exposed); T025 (cancelled) for the publish-script pattern.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-10-19)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] Requirement Refs exist and are covered

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `scripts/publish_image.sh`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `compose.yaml` services build/tag the image as `temvar/easy-verifier-mcp:0.1.0` (one image name everywhere: compose, docs, scripts, tests) | one image of current code |
| 2 | `docs/DOCKER_MCP_GUIDE.md` opens the shared-container section with **"Quick start: pull and run"**: `docker pull temvar/easy-verifier-mcp:0.1.0`, one `docker run -d ...` that is the exact equivalent of the compose `scorer` service (same hardening: `--init --read-only --cap-drop ALL --security-opt no-new-privileges:true --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m`, `--network host`, `--restart unless-stopped`, workspace bind read-only at the same path, reports dir, `/sot`, env `EASY_VERIFIER_REPORTS_DIR`/`EASY_VERIFIER_SOT`, command `--transport streamable-http`), the reports/sot `mkdir` + `chown 10001` prep, and the `claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp` line. Build-from-clone (compose) follows as "Build from source"; stdio stays the alternative | pull and run first, others later |
| 3 | `README.md`'s container section leads with the same pull + run + register commands (verbatim copies of the guide's), then points to the guide for build-from-source and stdio | README first impression |
| 4 | A test asserts the documented `docker run` flags equal the compose `scorer` service's hardening (read_only, init, cap_drop ALL, no-new-privileges, tmpfs options, network host, restart policy, the three mounts and their ro-ness, env names, command) — parse compose.yaml and the guide's code block. Negative: removing `--read-only` or `--cap-drop ALL` from the doc block fails the test | equivalence is pinned |
| 5 | `scripts/publish_image.sh` (from T025, adapted): builds `linux/amd64` with tags `:<pyproject version>` and `:latest`; refuses a dirty tree; refuses if compose image ≠ `temvar/easy-verifier-mcp:<version>`; without flags = local build only (`docker buildx build --load`, nothing pushed); `--push` publishes; because `0.1.0` already exists on Docker Hub, `--push` refuses an existing tag unless `--replace-existing` is also given (the user's 2026-10-19 decision is the documented reason). Tests pin the guards with a stubbed `docker` (no network) | guarded publish, operator executes |
| 6 | Live proof (Docker available on this host): build locally with the script (no push), run the documented `docker run` against a throwaway workspace containing a small repo, list tools and call `score` on it over `http://127.0.0.1:<port>/mcp` (use a free port via `EASY_VERIFIER_PORT` if 8766 is taken), confirm `ss -ltn` shows loopback only, then stop and remove the container. Paste output | it really works |
| 7 | `docs/RELEASE_GUIDE.md` gains the image publish step (operator): `bash scripts/publish_image.sh --push --replace-existing` after the release tag, plus a post-publish check `docker buildx imagetools inspect temvar/easy-verifier-mcp:0.1.0` showing a new digest | operator steps |
| 8 | Full suite passes in `.venv` (existing tests pinning `easy-verifier-mcp:0.1.0` are updated to the new name — list each one changed) | no regression |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How it's checked |
|---|-------|--------|------------------|
| 1 | Repo after the change | new tests + full suite pass | automated |
| 2 | Doc block with `--read-only` removed | equivalence test fails | automated |
| 3 | `publish_image.sh --push` with a stub reporting the tag exists, no `--replace-existing` | exits non-zero, nothing pushed | automated (stub) |
| 4 | Fresh container from the documented `docker run` | `score` returns ratings over HTTP, loopback-only | live, pasted |

### Verification Command

```bash
cd "$(git rev-parse --show-toplevel)"
<main-checkout>/.venv/bin/python -m pytest -q   # PYTHONPATH=src when run from a worktree
bash scripts/publish_image.sh                    # local build only
```

---

## UI / Design Acceptance Criteria

N/A — container, script and docs; no rendered UI. All three UI Evidence rows ☐ N/A.

---

## Approach

**Pattern reference**: T025's `scripts/publish_image.sh` + `tests/test_t025_image_publish.py` (stubbed-docker guard tests); `tests/test_t101_shared_container.py` (driving the HTTP server); `scripts/verify_container.sh` (hardening probes).

Test first (equivalence + script guards), then compose rename, docs, script, live proof.

---

## Edge Case Checklist

- [ ] `--network host` + loopback bind: the server binds 127.0.0.1 itself (DDR-0013) — the doc must not add `-p`
- [ ] `EASY_VERIFIER_REPORTS_DIR` must equal the reports bind target (same-path mount)
- [ ] Docs placeholder paths use `/home/you/code` (the exempt placeholder) — no real host paths in tracked files (test_t100)
- [ ] `docker buildx build` without `--push` must `--load` so the image is runnable locally
- [ ] A container named `easy-verifier` already running → the doc shows `docker rm -f easy-verifier` for restarts
- [ ] Do not delete or retag the user's other local images

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `compose.yaml` | image name |
| `docs/DOCKER_MCP_GUIDE.md` | Quick start: pull and run first |
| `README.md` | container section leads with pull + run |
| `docs/RELEASE_GUIDE.md` | publish step |
| `scripts/publish_image.sh` | new (from T025) |
| `tests/test_t118_pull_and_run.py` | new |
| tests pinning the old image name | updated |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/**` | no behaviour change |
| `site/**` | T119 |
| `pyproject.toml` | version stays 0.1.0 |
| `PROJECT_KANBAN*.md`, `memory/**` | Supervisor-only |

---

## Test Plan

`tests/test_t118_pull_and_run.py` (AC 4, 5), updated name pins (AC 1, 8), live run (AC 6), full suite.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Risk Medium)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T118.md` Evidence (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — live container proof (AC 6)
- [ ] Supervisor notified: task ready for Stage 4 review
