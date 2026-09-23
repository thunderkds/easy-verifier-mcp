# TASK_GUIDE — T023: final v1 release verification
**Date**: 2026-09-23
**Complexity Level**: C2
**Risk Level**: High
**Priority**: P0
**Assigned agent**: QA-Automation-Agent
**Agent guide**: `.claude/agents/qa.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, especially FR-019a, FR-021a, FR-021c, FR-022, NFR-010, NFR-012, and NFR-013.
2. Read `memory/MEMORY.md`.
3. Read this file completely.
4. Read `.claude/agents/qa.md` and `memory/codebase-map.md`.
5. Read `tasks/TASK_GUIDE_T017.md` and `tasks/TASK_REVIEW_T017.md`.
6. Confirm T017's implementation is committed and published before starting. Do not verify a dirty or unpublished release candidate.

## Requirement (Pillar 1 — Adapt the requirement)

**Original request:** perform the final verification before release after the independent T017 gate is ready.

**Restated intent**:
> On a clean, published release candidate, run the complete v1 verification gate at its real boundaries and bring the repository-facing documentation into agreement with the verified result. Release is ready only when host integration, CLI/MCP parity, redaction, self-containment, MCP stdio, Docker hardening, container path scrubbing, regression tests, documentation truth, and KPI output all pass. Any unavailable proof remains visibly `NOT VERIFIED` and fails the gate.

**Out of scope**:
- Fixing production or test defects discovered by verification; route them to a new scoped task.
- Adding release features, changing parity normalization, or weakening a failed assertion.
- Treating skipped, historical, local-only, or unpushed evidence as release proof.
- Claiming Docker, stdio, or release readiness in documentation when the corresponding gate is unavailable.

**Requirement Refs**:
- FR-019a / FR-021a: MCP stdio and Docker packaging
- FR-021c: no container-internal paths in reports or score output
- FR-022: byte-equal adapter parity after DDR-0005's closed normalization
- NFR-010: raw secrets never reach packs, reports, logs, or errors
- NFR-012 / NFR-013: local-only, least-privilege container operation
- PRD Success Metrics / KPIs: all release rows must report `PASS`
- Repository documentation contract: README and release runbook must describe the exact runnable gate and its fail-closed meaning

### Requirement Fidelity Gate

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-09-23)
- [x] Domain terms align with the glossary: release gate, evidence, parity, redaction, `NOT VERIFIED`
- [x] Every Acceptance Criterion below traces to the Requirement above
- [x] Requirement refs exist in `PRD.md` and are covered by the criteria

## Dependencies & Reachability

**Depends on**: T017 — independent integration and release gate must be committed and published; T016 — live container verifier and Docker packaging.

**Entry point**: `scripts/verify_release_gate.sh`

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|---|---|
| 1 | The release candidate is clean, the intended commit is published on `github/develop`, and the verifier runs against that exact commit. | Release integrity; FR-022 |
| 2 | `bash scripts/verify_release_gate.sh` exits 0 in a Docker-capable environment. | All refs; KPI gate |
| 3 | Host integration passes without hiding required proof; all seven dimensions, combined/score/discovery parity, standalone warning, findings rejection, redaction, and self-containment pass. | FR-022, NFR-010, KPI |
| 4 | MCP stdio is driven through a real process boundary and the container tests execute, rather than skip; Docker hardening, `/workspace` path scrubbing, and report writing pass. | FR-019a, FR-021a, FR-021c, NFR-012, NFR-013 |
| 5 | Every KPI row reports `PASS`; no row reports `NOT VERIFIED`, and the wrapper fails nonzero if Docker, stdio, or another required proof is unavailable. | PRD KPIs; fail-closed constraint |
| 6 | Compatible full regression, Ruff, formatting, shell syntax, Compose configuration, and `git diff --check` pass on the release candidate. | Quality/release integrity |
| 7 | The final evidence records exact commands, exit codes, commit/ref identity, environment limitations, and any remaining blocker; no claim relies on historical output. | Traceability and auditability |
| 8 | `README.md` and `docs/RELEASE_GUIDE.md` document the same release command, prerequisites, PASS criteria, and `NOT VERIFIED` failure semantics; no stale claim says the release is ready. | Documentation truth |

## Evaluation & Acceptance

### Success Criteria

| # | Given (input/state) | Expect (output/behavior) | How checked |
|---|---|---|---|
| 1 | Clean published `develop` with T017 present | Release wrapper exits 0 and prints all KPI rows as `PASS` | exact release command |
| 2 | Docker daemon unavailable or MCP stdio cannot start | Wrapper exits nonzero and names the missing proof; no release-ready claim | controlled environment probe |
| 3 | Same release candidate at host and container boundaries | Parity holds under only DDR-0005's three normalizations; substantive differences fail | T017 integration/container tests |
| 4 | Runtime-generated fake secrets in a target repository | No raw secret appears in packs, reports, logs, stderr, or errors | T017 redaction proof |
| 5 | Full project test/lint/format checks | All checks pass with exit code 0 | compatible full-suite command |
| 6 | README and release guide are checked against the actual wrapper and current release verdict | Commands and status semantics are accurate and reproducible | documentation truth test plus Markdown review |

### Verification Command (exact, runnable)

```bash
bash scripts/verify_release_gate.sh
```

Supplemental evidence commands, run against the same commit:

```bash
PYTHONPATH=src <compatible-python> -m pytest -q --tb=short
ruff check src tests
ruff format --check src tests
bash -n scripts/verify_release_gate.sh
docker compose config --quiet
git diff --check
python -m pytest tests/test_t018_readme.py -q
```

## Evidence

Evidence belongs in `tasks/TASK_REVIEW_T023.md`. A Docker or stdio skip is not a pass; it must be shown as `NOT VERIFIED` and leaves T023 open.

## Approach

**Pattern reference**: `scripts/verify_release_gate.sh` and `tasks/TASK_REVIEW_T017.md` — reuse the existing fail-closed wrapper and independent QA evidence; do not create a second normalization or release oracle.

Run the gate from a clean, published candidate, capture output and exit status directly, then perform the supplemental checks against the same commit. If any required surface fails, stop at the failing boundary and report the owning follow-up task instead of editing the implementation during release verification.

## Edge Case Checklist

- [ ] Docker CLI exists but the daemon socket is inaccessible — must fail, not skip-success.
- [ ] MCP stdio emits no response or exits before all response IDs arrive — must name the missing response.
- [ ] A container report contains `/workspace` or another absolute container path — fail FR-021c.
- [ ] A fourth adapter difference appears outside DDR-0005 — report a spec defect; do not normalize it.
- [ ] Remote ref differs from the verified local commit — do not call the candidate published.
- [ ] A full suite uses a different interpreter or stale editable install — record the interpreter and source path.

## Files to Change (Predicted)

| File | Change |
|---|---|
| `tasks/TASK_GUIDE_T023.md` | This release-verification contract |
| `tasks/TASK_REVIEW_T023.md` | Final commands, outputs, commit identity, and release verdict |
| `README.md` | Document the final release gate, prerequisites, and fail-closed status semantics |
| `docs/RELEASE_GUIDE.md` | Add the repository release runbook / guidebook for the exact verification workflow |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `src/easy_verifier/**` | Verification task; production changes require a separate scoped task |
| `tests/integration/**` | T017 owns the independent oracle; changes require a separate QA remediation task |
| `Dockerfile`, `compose.yaml`, `scripts/verify_container.sh` | T016 artifacts are verified, not changed here |
| `PROJECT_SPEC.md`, `PRD.md`, `memory/**` | No requirement or memory changes during final verification |

## Test Plan

Run the exact release wrapper and supplemental commands against one clean published commit, update README and the release guide from the observed result, capture raw output, and record unavailable proof as a blocker. Documentation updates must be truthful for both PASS and `NOT VERIFIED` outcomes; do not mark T023 Done until every required gate passes in one reproducible run.

## Completion Checklist

- [ ] T017 is committed and published; candidate identity recorded
- [ ] Release wrapper exits 0 with all KPI rows `PASS`
- [ ] MCP stdio and Docker proof executed, not skipped
- [ ] Full regression, Ruff, formatting, shell, Compose, and diff checks pass
- [ ] Stage 4 bounded code/security review recorded
- [ ] `tasks/TASK_REVIEW_T023.md` contains exact evidence and verdict
- [ ] T023 marked Done only after the release verdict is PASS
