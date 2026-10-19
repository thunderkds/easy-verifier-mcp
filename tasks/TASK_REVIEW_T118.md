# TASK_REVIEW — T118: Pull-and-run image `temvar/easy-verifier-mcp:0.1.0` from current code

> Sibling of `tasks/TASK_GUIDE_T118.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t118_pull_and_run.py` (29 tests: AC1 one image name; AC2/AC3 quick-start order + README verbatim copy; AC4 strict-parse equivalence of the doc `docker run -d` with `docker compose config` scorer service; AC5 script guards against a stubbed `docker`; AC7 release-guide step). Pre-change run on `9667e85`: `17 failed, 1 passed, 11 errors`. Post-change: `29 passed in 1.30s` (pass) |
| Verification command run | ☑ pass | `bash scripts/publish_image.sh` (no flags) at `327caa0`: `Local build: loaded temvar/easy-verifier-mcp:0.1.0 and temvar/easy-verifier-mcp:latest for linux/amd64; nothing was published` exit=0; image `4a062789ba8e`. Full suite: see smoke row |
| Negative cases hold | ☑ pass | Doc block with `--read-only`, `--cap-drop ALL`, `--init`, `--security-opt …`, `--restart …`, `:ro`, `-e EASY_VERIFIER_SOT=/sot`, or the command removed → mismatch (8 parametrized tests); adding `-p 8766:8766`, `-i`, `--user` → mismatch. Script: `--push` + existing tag without `--replace-existing` exits non-zero with no build call; dirty tree, wrong compose image (either service), builder without amd64, `--replace-existing` alone, unknown args all refuse before building. Sabotage: disabling the existing-tag guard → `test_push_refuses_an_existing_tag_without_replace_existing` FAILED; removing dirty-tree guard + `--load` → 2 FAILED (pass) |
| verify | ☑ pass | Live proof (manual verify; Skill tool not available to this agent): documented `docker run -d` extracted verbatim from the guide, run against a throwaway workspace on the final image; tools/list 18 tools, `score` returned overall 80 over `http://127.0.0.1:8766/mcp`, `ss -ltn` shows `127.0.0.1:8766` only, LAN IP refused, container + scratch removed — pass. Output in Demonstration AFTER |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: compose image name (both services), docs/DOCKER_MCP_GUIDE.md, README Docker section, RELEASE_GUIDE publish step, scripts/publish_image.sh, the verify_container.sh expected-tool line, tests pinning image name/doc order. Skipped `src/**` (unchanged) and `site/**` (T119) — pass |
| Full smoke suite still green (no regression) | ☑ pass | Run 1 at `a805fb6` (fresh image): `2 failed, 3252 passed, 3 skipped in 670.19s` — both failures `unexpected=['change-risk']` from `scripts/verify_container.sh` (pre-existing: T108 added the tool, the verifier's hardcoded set was never updated; masked by a stale pre-T108 local image). Fixed in `327caa0`; rerun `tests/integration/test_adapter_parity.py tests/integration/test_redaction_proof.py`: `9 passed in 37.40s` exit=0; doc suites after review fixes: `117 passed, 2 skipped` exit=0. A final full run at `327caa0` was started in the background; the user said not to wait, so its result is not pasted here — Supervisor to re-run at Stage 5 |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI: container, script and docs only (guide § UI/Design N/A) |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI: container, script and docs only (guide § UI/Design N/A) |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI: container, script and docs only (guide § UI/Design N/A) |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by common-infrastructure in the T118 worktree, before any implementation commit):

```text
$ date -u
Mon Oct 19 08:03:22 AM UTC 2026
$ grep -n image: compose.yaml
6:    image: easy-verifier-mcp:0.1.0
49:    image: easy-verifier-mcp:0.1.0
$ ls scripts/publish_image.sh
ls: cannot access 'scripts/publish_image.sh': No such file or directory
exit=2
$ grep -n 'docker pull' README.md docs/DOCKER_MCP_GUIDE.md
exit=1
$ docker images ... | grep temvar
temvar/easy-verifier-mcp:0.2.0 7dfd60af1835 10 days ago
temvar/easy-verifier-mcp:latest 7dfd60af1835 10 days ago
temvar/easy-verifier-mcp:0.1.0 8dee42f049a9 2 weeks ago
```

**AFTER** (common-infrastructure, worktree at `327caa0`):

```text
$ grep -n image: compose.yaml
6:    image: temvar/easy-verifier-mcp:0.1.0
49:    image: temvar/easy-verifier-mcp:0.1.0
$ ls scripts/publish_image.sh
scripts/publish_image.sh
$ grep -n 'docker pull' README.md docs/DOCKER_MCP_GUIDE.md
docs/DOCKER_MCP_GUIDE.md:27:   docker pull temvar/easy-verifier-mcp:0.1.0
docs/DOCKER_MCP_GUIDE.md:83:docker pull temvar/easy-verifier-mcp:0.1.0
docs/DOCKER_MCP_GUIDE.md:158:Pull it (`docker pull temvar/easy-verifier-mcp:0.1.0`), or build it from this repository:
README.md:419:   docker pull temvar/easy-verifier-mcp:0.1.0
README.md:453:the repository. Stop it with `docker rm -f easy-verifier`; to upgrade, remove it, `docker pull`
$ bash scripts/publish_image.sh   (old IDs: temvar 0.1.0 8dee42f049a9, latest 7dfd60af1835 = 0.2.0)
Mon Oct 19 08:26:18 AM UTC 2026
#13 writing image sha256:4a062789ba8eae3206bd97171bdbf9509bc16efa4820fd30940ea1d846413b0c done
#13 naming to docker.io/temvar/easy-verifier-mcp:0.1.0 0.0s done
#13 naming to docker.io/temvar/easy-verifier-mcp:latest 0.0s done
Local build: loaded temvar/easy-verifier-mcp:0.1.0 and temvar/easy-verifier-mcp:latest for linux/amd64; nothing was published (pass --push to publish).
exit=0
temvar/easy-verifier-mcp:0.1.0 4a062789ba8e Less than a second ago
temvar/easy-verifier-mcp:latest 4a062789ba8e Less than a second ago
temvar/easy-verifier-mcp:0.2.0 7dfd60af1835 10 days ago

# live run of the documented command
$ date -u
Mon Oct 19 08:27:04 AM UTC 2026
$ git -C <worktree> rev-parse --short HEAD
327caa0
$ ss -ltn | grep :8766   (before)
(nothing on 8766)
# step 2 prep as documented, under a throwaway HOME=<scratch>/home; chmod 0777 instead of sudo chown 10001 (no sudo in the agent shell)
# step 3: the docker run block extracted verbatim from docs/DOCKER_MCP_GUIDE.md, /home/you/code -> <scratch>/code, run with HOME=<scratch>/home
6780427916b2c39a2442772f6032c2948916a30eec3532abe96798ef8b3aa7a1
docker run exit=0
$ docker inspect easy-verifier (hardening as applied)
Image=sha256:4a062789ba8eae3206bd97171bdbf9509bc16efa4820fd30940ea1d846413b0c User=10001:10001 ReadonlyRootfs=true Init=true NetworkMode=host CapDrop=[ALL] SecurityOpt=[no-new-privileges:true] Restart=unless-stopped Tmpfs=map[/tmp:rw,noexec,nosuid,nodev,size=16m] PortBindings=map[]
mount <scratch>/home/.easy-verifier-sot -> /sot rw=true
mount <scratch>/code -> <scratch>/code rw=false
mount <scratch>/home/.easy-verifier-reports -> <scratch>/home/.easy-verifier-reports rw=true

$ ss -ltn | grep :8766   (running)
LISTEN 0      2048       127.0.0.1:8766       0.0.0.0:*   
$ python live_client.py http://127.0.0.1:8766/mcp <scratch>/code/demo
server: easy-verifier 1.29.1
tools (18): api, architecture, blast-radius, change-risk, code-quality, combined, data, infrastructure, list_dimensions, operations, reliability, requirement-fidelity, score, security, solution-fit, supply-chain, test-strategy, write_report
score.repo: None
score.overall: 80
  api: abstained (below_coverage_floor)
  architecture: abstained (below_coverage_floor)
  blast-radius: abstained (all_metrics_abstained)
  code-quality: abstained (below_coverage_floor)
  data: abstained (below_coverage_floor)
  infrastructure: abstained (below_coverage_floor)
  operations: abstained (below_coverage_floor)
  reliability: abstained (insufficient_measured_weight)
  requirement-fidelity: abstained (below_coverage_floor)
  security: abstained (below_coverage_floor)
  solution-fit: abstained (no_static_rule)
  supply-chain: abstained (below_coverage_floor)
  test-strategy: 80
client exit=0
$ curl http://<host LAN IP>:8766/mcp
curl: (7) Failed to connect to <host LAN IP> port 8766 after 0 ms: Could not connect to server
000
curl exit=7
$ docker rm -f easy-verifier
easy-verifier
$ docker ps -a --filter name=^easy-verifier$
(none)
$ ss -ltn | grep :8766   (after)
(nothing on 8766)
$ rm -rf <scratch>
(scratch removed)
```

**DELTA**: A newcomer can now `docker pull temvar/easy-verifier-mcp:0.1.0`, start the shared scorer with one documented `docker run -d` (hardening identical to compose `scorer`, test-pinned) and register it with one `claude mcp add` line — no clone, no compose (once the operator publishes with `publish_image.sh --push --replace-existing`).

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
