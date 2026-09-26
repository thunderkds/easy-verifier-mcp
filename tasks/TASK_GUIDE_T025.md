# TASK_GUIDE — T025: Publish the container image to Docker Hub (pull-and-run distribution)
**Date**: 2026-09-24
**Complexity Level**: C1
**Risk Level**: Medium — publishes a public, hard-to-retract artifact; a wrong or mutable tag reaches every user who pulls it
**Priority**: P2
**Assigned agent**: common-infrastructure
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/common-infrastructure.md`
5. Note the **Complexity Level** above and apply the matching process (brainstorm / decompose / verify depth / model) from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2/C3 or multi-file tasks only**: read `memory/codebase-map.md` for directory layout, entry points, and blast-radius hotspots — skip if the task is C0/C1 and touches a single known file

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-24): "investigate the way if we can build the image and push to docker hub, for the
shortest way, we just pull down the image and run as container, is it good" → Supervisor
recommended it; user: "yes, let go".

Decisions taken with the user (2026-09-24):
- **Tags**: `0.1.0` + `latest`. Docs pin `0.1.0`; `latest` is a convenience alias only.
- **Pipeline**: a local script (`scripts/publish_image.sh`) doing a multi-arch `docker buildx`
  build + push. **No GitHub Actions workflow.**
- **Namespace**: **OPEN — user will supply later.** Written below as `<NS>`. The agent must not
  guess it; every `<NS>` is replaced with the user-confirmed value before spawn (see Blocked).

**Restated intent** (Supervisor's interpretation, in the project's domain language):
> A user can register easy-verifier as an MCP server with nothing but Docker: `docker pull
> <NS>/easy-verifier-mcp:0.1.0`, then the existing hardened `docker run -i …` from
> `docs/DOCKER_MCP_GUIDE.md` — no clone, no local build. The published image is the same hardened,
> network-less, stdio-only image T016/T023 verified, for both `linux/amd64` and `linux/arm64`.

**Out of scope** (what this task explicitly does NOT do):
- CI/CD (GitHub Actions or any hosted pipeline) — user chose the local script.
- Any change to `Dockerfile` runtime behaviour, hardening flags, or the MCP tool surface.
- Image signing / SBOM / provenance attestations.
- Publishing any version other than `0.1.0`.

**Requirement Refs** (FR/NFR/US IDs from `PRD.md` this task satisfies):
- Distribution of the existing MCP-stdio Docker boundary (T016 / T024). No new FR — this is a
  delivery-channel change; the Supervisor confirms at the Fidelity Gate whether a PRD line should be added.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] `<NS>` replaced everywhere in this guide with the user-confirmed Docker Hub namespace
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] Requirement Refs resolved (PRD line added, or "no new FR" confirmed)

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T024 — `docs/DOCKER_MCP_GUIDE.md` and `tests/test_t024_mcp_guides.py` must be committed (they are uncommitted on `docs/T024-docker-mcp-client-guide` as of 2026-09-24)

**Entry point**: `scripts/publish_image.sh`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `compose.yaml`'s `image:` is `<NS>/easy-verifier-mcp:0.1.0`, and its tag equals `pyproject.toml`'s `version` | pull-and-run, pinned `0.1.0` |
| 2 | Every image reference in `docs/DOCKER_MCP_GUIDE.md` and `README.md` is exactly the `compose.yaml` image; no bare `easy-verifier-mcp:0.1.0` remains | pull-and-run (docs must name the published image) |
| 3 | The guide's step 1 is `docker pull <NS>/easy-verifier-mcp:0.1.0`; building from source stays documented as the alternative | "we just pull down the image and run" |
| 4 | `scripts/publish_image.sh` builds `linux/amd64,linux/arm64` with `docker buildx` and tags `:<version>` and `:latest` | tags + local-script decision |
| 5 | Without `--push` the script builds both platforms but publishes nothing; only `--push` publishes | publishing is outward-facing → explicit opt-in |
| 6 | The script refuses (non-zero, no push) when: the working tree is dirty; the version tag already exists on Docker Hub; the `compose.yaml` image disagrees with the script's image/version | a published version tag is immutable and matches the documented source |
| 7 | After publishing, the pulled image passes `scripts/verify_container.sh` unchanged (11 tools, non-root, read-only root, `network=none`, caps dropped) | "same hardened image" |
| 8 | The Docker Hub manifest lists both `linux/amd64` and `linux/arm64` | multi-arch for Apple Silicon users |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

> The Supervisor signs off on the oracle (test file + commands below) before the agent implements.
> **Steps 3–5 of the Verification Command publish to Docker Hub and are run by the Supervisor only,
> after an explicit user "go" in-session — never by the implementing agent.**

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | repo at task HEAD | compose image == all doc image refs; compose tag == pyproject version | automated test (`tests/test_t025_image_publish.py`) |
| 2 | `scripts/publish_image.sh` source | `bash -n` clean; names both platforms, both tags; push only behind `--push`; dirty-tree, existing-tag, and compose-mismatch guards present | automated test |
| 3 | sabotage: bare `easy-verifier-mcp:0.1.0` in the guide; compose tag ≠ pyproject version; `--push` made unconditional | each sabotage fails the new tests | manual probe, output pasted in review |
| 4 | dirty working tree | `scripts/publish_image.sh` exits non-zero before any build | manual run |
| 5 | clean tree, no `--push` | both platforms build; `docker buildx imagetools inspect <NS>/easy-verifier-mcp:0.1.0` still reports not found | manual run |
| 6 | after the Supervisor's `--push` | manifest shows amd64 + arm64; pulled image passes `verify_container.sh`; second `--push` refuses (tag exists) | Supervisor run |

### Verification Command (exact, runnable)

```bash
# 1. static oracle + regression (agent and Supervisor)
.venv/bin/python -m pytest tests/test_t025_image_publish.py tests/test_t024_mcp_guides.py tests/test_t016_container_config.py -q
.venv/bin/python -m pytest -q && .venv/bin/ruff check .

# 2. dry run: multi-arch build, no publish (agent and Supervisor)
bash scripts/publish_image.sh

# 3–5. SUPERVISOR ONLY, after explicit user go: publish, then verify the published artifact
bash scripts/publish_image.sh --push
docker buildx imagetools inspect <NS>/easy-verifier-mcp:0.1.0      # expect linux/amd64 + linux/arm64
docker image rm <NS>/easy-verifier-mcp:0.1.0 || true
docker compose pull && bash scripts/verify_container.sh
bash scripts/publish_image.sh --push; echo "exit=$?"                # expect non-zero: tag exists
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T025.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T025.md`. BEFORE: `docker pull <NS>/easy-verifier-mcp:0.1.0` → not found.
> AFTER: pull succeeds and the documented `claude mcp add … docker run -i …` lists 11 tools.

---

## Approach

**Pattern reference**: `scripts/verify_container.sh` — `set -euo pipefail`, a `fail()` helper, up-front
tool checks (`command -v docker`), and explicit guard messages. Imitate its style exactly.

1. **`compose.yaml`**: change only `image:` to `<NS>/easy-verifier-mcp:0.1.0`. Keep `build:` so
   `docker compose build` still works from source and `docker compose pull` fetches the published
   image. `verify_container.sh` uses the compose image, so it verifies whichever one is present —
   no script change needed.
2. **`scripts/publish_image.sh`** (new): image repo `<NS>/easy-verifier-mcp` as one variable at the
   top; version read from `pyproject.toml`; assert `compose.yaml`'s image equals `$repo:$version`;
   refuse a dirty tree (`git status --porcelain`); with `--push`, refuse if
   `docker buildx imagetools inspect "$repo:$version"` succeeds; run
   `docker buildx build --platform linux/amd64,linux/arm64 -t "$repo:$version" -t "$repo:latest"`
   adding `--push` only when requested; print the pushed digest. Fail with a clear message if no
   buildx builder supports both platforms (point to `docker buildx create --use` / QEMU binfmt).
3. **Docs**: `docs/DOCKER_MCP_GUIDE.md` step 1 becomes "Get the image" — `docker pull` first,
   `docker compose build` as the from-source alternative; replace every image ref; the
   "Unable to find image" troubleshooting row points to `docker pull`. `README.md` Docker section
   gains the one-line pull. `docs/RELEASE_GUIDE.md` gains a short "Publish the image" section
   naming the script and the Supervisor-only publish rule.
4. **Tests**: new `tests/test_t025_image_publish.py` for Success Criteria 1–2; update the image pin
   in `tests/test_t024_mcp_guides.py` (line 31) to read the compose image rather than a
   hard-coded literal.

---

## Edge Case Checklist

- [ ] Re-pushing `0.1.0` would silently change what pinned users run → existing-tag guard (AC 6)
- [ ] Publishing from a dirty tree ships code no commit describes → dirty-tree guard (AC 6)
- [ ] `pyproject.toml` version bumped but compose/docs not → version-consistency test (AC 1)
- [ ] Default `docker` buildx driver cannot build multi-platform → clear failure, not a single-arch push
- [ ] arm64 build without QEMU binfmt → clear failure message
- [ ] `latest` tag must never appear in docs examples (docs pin `0.1.0`)
- [ ] `.dockerignore` unchanged — published image must not contain `.git`, `memory`, `tasks`, `tests` (already pinned by `test_build_context_excludes_development_and_repository_state`)
- [ ] Docker Hub repo visibility is public — confirm with the user before the first push

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `compose.yaml` | `image:` → `<NS>/easy-verifier-mcp:0.1.0` |
| `scripts/publish_image.sh` | new: guarded multi-arch build/push |
| `docs/DOCKER_MCP_GUIDE.md` | pull-first step 1; image refs; troubleshooting row |
| `README.md` | Docker section: one-line `docker pull` |
| `docs/RELEASE_GUIDE.md` | short publish section |
| `tests/test_t025_image_publish.py` | new oracle |
| `tests/test_t024_mcp_guides.py` | image pin reads compose instead of literal |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `Dockerfile` | runtime image verified by T016/T023; out of scope |
| `src/**` | no product change |
| `scripts/verify_container.sh` | the oracle for AC 7 — must verify the pulled image unchanged |

---

## Test Plan

Static: `tests/test_t025_image_publish.py` + updated T024 test, plus the sabotage probe (Success
Criteria 3). Behavioural: dirty-tree refusal and the no-push dry run (agent). Published artifact:
manifest inspect, pull + `verify_container.sh`, repeat-push refusal (Supervisor, after user go).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T025.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — pulled image driven over MCP stdio
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
