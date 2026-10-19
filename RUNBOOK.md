# RUNBOOK — easy-verifier-mcp
**Last updated**: 2026-10-19

> Operational runbook: how to release, verify, and recover. Written by the `ship` skill; the
> Supervisor plans, **the operator executes** — no agent pushes, merges to `main`, or deploys.

---

## Service Identity

- **Name**: easy-verifier-mcp (offline, rule-based repository verifier — MCP server + CLI)
- **Repo**: `github.com/thunderkds/easy-verifier-mcp` (remote name `github`)
- **Deployment target**: Local Docker, reached by the operator's agent harness. Primary: one shared
  streamable-HTTP container (`scorer`, loopback `127.0.0.1:8766`, DDR-0013). Alternative: per-session
  stdio container. Never internet-exposed (NFR-012). Mirrors `PROJECT_SPEC.md`.
- **Release = fast-forward `main` to a verified `develop` commit, plus a git tag.** `main` is also
  the production branch for the landing site (Vercel, `PROJECT_SPEC_SITE.md`) once T116 lands and the
  operator connects Vercel.
- **Tech**: Python 3.12, `mcp` 1.30, Docker
- **Owner / on-call**: thunderkds (sole operator)

---

## Release 1 plan — `develop` → `main` (first release)

**Planned 2026-10-19. Status: GO for `v0.1.0` — operator executes.**

### Scope

- `main` = `0242067 Initial commit`. `develop` = 869 commits ahead; `main` is an ancestor, so the
  release is a pure **fast-forward** — no merge commit, no conflicts.
- 106 task IDs appear in the range (T001–T114). On `PROJECT_KANBAN.md`: 118 Done, T025 Cancelled,
  none In Progress. Site board (`PROJECT_KANBAN_SITE.md`): T115 (page) and T116 (Vercel config)
  **Done and merged into develop** (f1b9989, 96c14bd), so this release also carries `site/`,
  `vercel.json` and `.vercelignore`.
- `github/develop` is behind local `develop` by the 2026-10-19 commits (the T025 cancellation, the
  T115/T116 planning and merges, and this runbook). The release rule (`docs/RELEASE_GUIDE.md`) requires the candidate to be
  the published `github/develop` head.
- `pyproject.toml` version: `0.1.0`. Docker Hub already carries `temvar/easy-verifier-mcp:0.1.0` /
  `latest`, built 2026-10-05 from `fae8969` (an older develop commit). See Decision A.

### Pre-release checks (operator)

1. **Repair the venv.** `.venv` was built for Python 3.12 and its `python`/`python3` links point to
   `/usr/bin/python3`, which is now 3.14, so `.venv/bin/python -m pytest` reports
   `No module named pytest`. Rebuild it:
   ```bash
   /usr/bin/python3.12 -m venv --clear .venv   # aborts at ensurepip here (no python3.12-venv); links are fixed anyway
   uv pip install --python .venv/bin/python -e '.[dev]'
   .venv/bin/python -c "import pytest, mcp, easy_verifier; print('venv ok')"
   ```
   Pass: prints `venv ok`. **Done by the Supervisor 2026-10-19** (mcp 1.30.0, pytest 9.1.1).
2. **Clean tree on the candidate.** Commit or stash `memory/MEMORY.md` (tracked, modified locally),
   then:
   ```bash
   git switch develop && git status --short   # pass: empty output
   ```
3. **Publish the candidate to `github/develop`:**
   ```bash
   git push github develop
   git fetch github && test "$(git rev-parse develop)" = "$(git rev-parse github/develop)" && echo candidate-published
   ```
4. **Full suite:**
   ```bash
   .venv/bin/python -m pytest -q
   ```
   Pass: `0 failed, 0 errors`. **Supervisor run 2026-10-19 on `d7098eb`, repaired venv:
   `3214 passed, 2 skipped in 770.31s`.** (The earlier workaround run's `test_t014` and
   3 × `test_t101_shared_container` failures were environmental and now pass; the `test_t100`
   regression was fixed in `90c2b11`.)
5. **Release gate (stdio boundary + container):**
   ```bash
   bash scripts/verify_release_gate.sh
   ```
   Pass: final line `RESULT integration=0 container=0 release=0`, every KPI `PASS` (`NOT VERIFIED`
   is a failure). **Supervisor run 2026-10-19 on `d7098eb`: exit 0, `RESULT integration=0
   container=0 release=0`; integration 20 passed / 1 skipped; container 2 passed;
   `PASS: uid=10001, tools=12, root=read-only, reports=writable, network=none, ports=none,
   caps=none`; all 6 KPIs PASS.**
6. **Shared-container checks** — the "Supplemental checks" section of `docs/RELEASE_GUIDE.md`.

### Release steps (operator)

```bash
CANDIDATE=$(git rev-parse github/develop)
git push github "$CANDIDATE":refs/heads/main          # fast-forward only; refused if not a FF
git tag -a v<VERSION> "$CANDIDATE" -m "easy-verifier-mcp v<VERSION> — first release to main"
git push github v<VERSION>
```

Then publish the image (T118; replaces the 2026-10-05 Hub `0.1.0`, user decision 2026-10-19 —
needs `docker login` as `temvar` and a clean tree on the tagged commit):

```bash
bash scripts/publish_image.sh --push --replace-existing
docker buildx imagetools inspect temvar/easy-verifier-mcp:0.1.0   # new digest
```

`<VERSION>` is set by Decision A. The `pre_bash_block_unsafe_merge` hook blocks `git push` while
any `PROJECT_KANBAN.md` task is In Progress / Ready for Review. Today none is (T115 lives on the
site board).

### Post-release health check

```bash
git fetch github --tags
test "$(git rev-parse github/main)" = "$CANDIDATE" && echo main-ok
git rev-parse "v<VERSION>^{commit}"                   # equals $CANDIDATE
docker compose build scorer && EASY_VERIFIER_WORKSPACE="$(dirname "$PWD")" docker compose up -d scorer
claude mcp list | grep easy-verifier                 # registered against http://127.0.0.1:8766/mcp
```
Pass: `main-ok`, the tag resolves to the candidate, the `scorer` container is up, and one `score`
call on a small repo through the MCP client returns ratings. `docs/DOCKER_MCP_GUIDE.md` has the
probe.

### Rollback

- **Triggers**: the post-release health check fails; the container does not start from `main`; a
  wrong commit landed on `main`.
- **Reverse steps:**
  1. `main` had no consumers before this release (initial commit only, no Vercel yet). To restore
     it, reset `main` to the initial commit:
     `git push --force-with-lease=main:$CANDIDATE github 0242067:refs/heads/main`. This is a
     history rewrite, so the operator must explicitly approve it. Prefer step 2 when possible.
  2. Fix-forward: commit the fix on `develop`, re-run the pre-release checks, and fast-forward
     `main` again.
  3. Delete a wrong tag: `git push github :refs/tags/v<VERSION> && git tag -d v<VERSION>`.
  4. Container: `docker compose down scorer`, check out the previous good commit, rebuild.
- **Verify rollback**: `git rev-parse github/main` equals the intended commit, and the container
  health check above passes.

### Release notes (draft)

**Features**
- MCP server (stdio + shared streamable-HTTP container) and CLI over the same operations, with
  payload parity (T014, T015, T101–T103).
- 13 rated dimensions plus `change-risk`, scored from declared rules over measured metrics. A
  dimension abstains below its coverage floor, so there is no number without evidence (T010–T022,
  T050–T062, Wave 13).
- 32 cited evaluation areas, a reference registry with source tags, and optional `finance` /
  `healthcare` / `frontend-a11y` packs (Waves 10–11, 16).
- An improvement plan ordered by declared, recomputed gain (Wave 12). A readable HTML report and an
  evaluation guide (Wave 14).
- Any-language discovery with agent hard gates for picks, and `.easy-verifier.toml` conventions
  (Wave 9, Wave 15, T078).
- Architecture recognised by behaviour and content, not names (Wave 17). Request paths per route
  (T090).
- Change-risk scoring for bugfix/feature changes, with test ↔ symbol pairs (Waves 23–24). Whole-
  codebase scan and project-scope blast radius from the import graph (Wave 25, T113, T114).

**Fixes**
- Test-file sinks are reported but not scored (T092). The layer rule counts backend units only
  (T093). Document roles are filled by content (T089). Assorted redaction and entropy false
  positives were fixed (T029, T095, T097).

**Internal**
- Container hardening (read-only rootfs, non-root UID, no network on stdio) (T016–T018). Release
  gate script (T023). Privacy scrub of tracked files (T100).
- Known limitation: the evaluation area "Transactions, concurrency, idempotency" has no rule yet.

### GO gate

| Check | Status |
|---|---|
| Stage 5 evidence green for every in-scope task | ⚠️ 106/118 Done tasks matched the current Evidence-row format. 11 older tasks (T014–T023, T094, T097) record passing tests in an older format. **T096**'s "New test(s)" row lists the tests, but its checkbox was never ticked. |
| Full suite green in a working interpreter | ✅ 3254 passed, 3 skipped (2026-10-19, T118 at `327caa0`; `src/`, `Dockerfile`, `pyproject.toml` unchanged since; T119 site tests 118 passed on `1c06465`) |
| Release gate `RESULT ... release=0` | ✅ `RESULT integration=0 container=0 release=0` re-run 2026-10-19 on the **fresh** image `temvar/easy-verifier-mcp:0.1.0` (`4a062789ba8e`, built from `327caa0`). The earlier pass ran on a stale 2026-10-14 image and hid the missing `change-risk` tool (fixed in T118). The PASS line's `tools=12` is a hard-coded string; the check compares the exact 18-tool set. |
| Rollback plan with triggers + exact reverse steps | ✅ above |
| Post-release health check with a concrete pass condition | ✅ above |
| Release command known | ✅ fast-forward push + tag |
| Version decided | ✅ `v0.1.0` (operator, 2026-10-19 — Decision A) |

**Verdict: GO (2026-10-19) for `v0.1.0` at the published `develop` head.** Suite and release gate
are green in the repaired venv; the version is decided. Remaining steps are operator-only: clean
tree (pre-release check 2), publish `develop` (check 3), then the release steps with
`VERSION=0.1.0`, then connect Vercel. If `develop` moves past `d41ea3a` with code changes before
the release, re-run checks 4–5 first. T096's unticked evidence checkbox is bookkeeping, not a
blocker.

- **Decision A — resolved (operator, 2026-10-19): `v0.1.0`.** Matches `pyproject.toml`; no bump
  task. Operator's reason: there has been no prior release, so nothing consumes a conflicting
  `0.1.0`. Accepted side effect: the older Docker Hub `temvar/easy-verifier-mcp:0.1.0` image (from
  `fae8969`) shares the number with this git tag but is different code; it is not referenced
  anywhere in the docs or the site (T025 cancelled).
- **Decision B — resolved by events (2026-10-19):** T115 and T116 are merged, so the first `main`
  will serve the landing page as soon as the operator connects Vercel (`docs/RELEASE_GUIDE.md`,
  "Landing site"). After connecting, run that section's live checks: 200 for `/`, 404 for
  `/memory/MEMORY.md`.

This plan is a recommendation; the operator executes every step.

---

## Release Log

| Version | Date | Scope | Deployer | Outcome |
|---------|------|-------|----------|---------|
| v0.1.0 (Release 1) | planned 2026-10-19 | develop → main FF, T001–T119 + image publish | thunderkds | GO — awaiting operator execution |
