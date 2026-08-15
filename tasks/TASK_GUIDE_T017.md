# TASK_GUIDE — T017: verification suite — two-mode integration, FR-022 parity, NFR-010 redaction proof
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: **High**
**Priority**: P0
**Assigned agent**: QA-Automation-Agent
**Agent guide**: `.claude/agents/qa.md`

---

## ⛔ HITL Gate — do not start until this is answered

**Open item #15.** FR-022 says both adapters produce **"identical"** evidence packs and report
output; the `PRD.md` KPI table says **"byte-equal"**. These cannot both hold as written: a run on
the host and a run in the container differ in timestamps and in absolute paths by construction, and
report filenames embed a UTC timestamp with sub-second resolution (FR-018b) precisely so they never
collide.

The Supervisor must record the user's decision before this task is spawned:

| Option | Consequence |
|---|---|
| **A — Byte-equal after a defined normalization** (recommended) | Define a normalization applied before comparison: repo-relative paths, timestamps replaced by a fixed token, report filename excluded. Then assert byte-equality on the normalized form. Keeps the KPI's strength, and the normalization list is itself the honest statement of what legitimately differs. |
| **B — Weaken the word** | Change FR-022 and the KPI to "semantically identical: same excerpts, same order, same coverage, same miss lists", and compare structurally field by field. Simpler, but a weaker guarantee, and the comparison logic then embeds judgments about which differences matter. |

> Recommendation: **A**. It is the stronger guarantee, and the normalization list doubles as
> documentation of every host/container difference. Whichever is chosen, `PRD.md` FR-022 and the KPI
> row must be updated to agree with each other — that mismatch is the actual defect here.

| Decision | _unanswered_ |
|---|---|

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/qa.md`
5. **C2 / High Risk** — apply the C2 process from the Complexity matrix; expect mandatory `security-review` at Stage 4
6. **C2** — read `memory/codebase-map.md`
7. Read `tasks/TASK_GUIDE_T004.md` — this task's redaction proof is the formal Evidence-Gate artifact for NFR-010

---

## Requirement (Pillar 1 — Adapt the requirement)

Independently verify that the assembled system does what `PRD.md` promises — in both modes, from
both entry points, without leaking a secret.

**Restated intent**:
> A QA-owned suite proves three things end-to-end: (1) both kit-aware and standalone modes produce a
> usable report on a real repo; (2) the MCP and CLI adapters agree, per the parity definition decided
> at the HITL gate above; (3) no raw secret value escapes into any pack, report, log, or error, from
> either adapter, on host or in container. This suite is the project's release gate.

**Out of scope**:
- Fixing defects it finds — those return to the owning task via the `bugfix` skill.
- Re-testing what a task's own unit tests already cover; this is integration-level verification.

**Requirement Refs**:
- FR-022: both adapters produce identical evidence packs and report output for the same inputs
- FR-002/FR-003/FR-004: kit-aware and standalone modes, with the limited-context warning
- NFR-010: no raw secret reaches an agent, report or log — **the proof test**
- FR-018: reports self-contained, zero external requests
- FR-015/FR-015a/NFR-004: no unevidenced finding reaches a report
- FR-021c: no container paths in reports
- `PRD.md` KPI table: all six success metrics

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] HITL gate above answered; `PRD.md` FR-022 and the KPI row updated to agree
- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T015 — the CLI adapter must be complete to be one side of the parity comparison; T016 — the container must exist to test the host/container difference and FR-021c.

**Entry point**: `tests/integration/`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | **Kit-aware integration**: a full run against this repo produces a multi-dimension report with real coverage scores and miss lists | FR-002, `PRD.md` KPI "2 modes" |
| 2 | **Standalone integration**: a full run against a non-kit repo (an installed pip package) produces a usable report containing the limited-context warning | FR-003, FR-004, KPI "warning present: 100%" |
| 3 | **Parity**: for the same repo, scope and dimension, MCP and CLI output match per the HITL decision — including for the combined pack | FR-022, KPI "2 entry points" |
| 4 | **Parity across the container boundary**: a containerised run matches a host run under the same definition, and this is where FR-021c is actually proven | FR-022, FR-021c |
| 5 | **NFR-010 redaction proof**: with a repo seeded with distinct fake secrets, no raw value appears in any pack, any report, any log at DEBUG, or any error message — verified for **both** adapters and **both** host and container | NFR-010 |
| 6 | **Unevidenced findings**: submissions missing evidence or confidence, and submissions with dangling citations, are rejected with no report written — through both adapters | FR-015, FR-015a, KPI "unevidenced findings: 0" |
| 7 | **Self-containment**: every report produced by the suite is scanned for external references; zero found | FR-018, KPI "network fetches: 0" |
| 8 | **Discovery**: 7 dimensions listed by both adapters, with matching content | FR-013a, KPI "7 dimensions" |
| 9 | The suite runs as one command and reports pass/fail per KPI row, so the `PRD.md` KPI table can be filled from its output directly | `PRD.md` KPIs |
| 10 | Each failure names the requirement it violates (FR/NFR ID), not just an assertion diff | Traceability |
| 11 | The suite is **independent**: it does not import a task's own test helpers or reuse its assertions — an implementation bug shared with its unit test must still be caught here | Pillar 3 oracle |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo, all 7 dimensions, both adapters | Reports produced; parity holds; suite green | automated |
| 2 | An installed pip package as target | Standalone report with the warning | automated |
| 3 | Seeded-secret repo, both adapters, host + container, logging at DEBUG | Zero raw values across packs, reports, logs, stderr | automated |
| 4 | 3 malformed finding submissions (no evidence / no confidence / dangling ref) | All 3 rejected; `reports/` unchanged | automated |
| 5 | Every report the suite produced | Zero external references | automated |
| 6 | The whole suite | One command, KPI-shaped pass/fail summary | automated |

### Verification Command (exact, runnable)

```bash
pytest tests/integration -q --tb=short && bash scripts/verify_container.sh && \
  pytest tests/integration/test_kpi_summary.py -q -s
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T017.md`.
> This task's Evidence table is the **release gate** for v1. The NFR-010 proof (AC #5) and the
> parity result (AC #3/#4) must show pasted output. `ship` may not be invoked for the v1 milestone
> until this table is complete.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T017.md`.

---

## Approach

**Pattern reference**: `scripts/verify_container.sh` (T016) for the container-side checks; the per-task unit suites for fixture locations — but deliberately **not** for assertions (AC #11).

Structure the suite as one file per KPI row, so the `PRD.md` KPI table maps to it one-to-one and a
failure points at a metric rather than at an implementation detail.

On AC #11 — this is the reason the QA agent owns this task rather than the implementer. The Karpathy
rule that an implementing agent must not be the sole author of its own acceptance test only has
teeth if the independent suite is genuinely independent: write the assertions from `PRD.md`, not
from the code, and resist reading an implementation to decide what to assert.

The parity comparison (AC #3/#4) should implement the normalization decided at the HITL gate as one
documented, reviewable function. Every entry in it is an admission that something legitimately
differs between adapters, so the list should be short and each entry justified — if it grows to
cover a real behavioural difference, that is a defect in an adapter, not a normalization to add.

Defects found here go back to the owning task via `Skill({ skill: "bugfix" })`; do not fix them in
this task's branch, or the suite stops being independent evidence.

---

## Edge Case Checklist

- [ ] Docker unavailable on the test host → container tests skip cleanly and the skip is **visible in the summary**, never silently counted as a pass
- [ ] A dimension legitimately produces zero excerpts for a fixture → parity must still hold on empty output
- [ ] Non-determinism in ordering surfacing only across adapters → this is a real T005/T011 defect, not something to normalize away
- [ ] Timestamp resolution: two runs in the same second (FR-018b) → filenames differ, contents match after normalization
- [ ] The seeded-secret fixture accidentally committed with a *real* credential → fixtures must be generated or use published example values only; add a check
- [ ] Test pollution: reports written into the verifier repo's own `reports/` during the run → use temp targets, and assert the verifier repo is unchanged after the suite
- [ ] The suite evaluating this repo while this repo contains the fake-secret fixtures → expected hits; assert the fingerprints, not their absence
- [ ] Standalone fixture (an installed pip package) varying across environments → pin which package, or assert on properties rather than exact content
- [ ] Log capture missing output from a subprocess or the container → capture at the process boundary, not only via `caplog`
- [ ] A report written inside the container and read from the host → path translation for the assertion itself

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `tests/integration/test_kit_aware_mode.py` | New — AC #1 |
| `tests/integration/test_standalone_mode.py` | New — AC #2 |
| `tests/integration/test_adapter_parity.py` | New — AC #3, #4, plus the normalization function |
| `tests/integration/test_redaction_proof.py` | New — AC #5, the NFR-010 artifact |
| `tests/integration/test_findings_validation.py` | New — AC #6 |
| `tests/integration/test_report_self_contained.py` | New — AC #7 |
| `tests/integration/test_kpi_summary.py` | New — AC #9 |
| `tests/integration/fixtures/` | New — seeded-secret repo generator |
| `PRD.md` | **Supervisor edits** the FR-022 / KPI wording per the HITL decision — not the agent |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/**` | QA verifies; it does not fix. Defects route back to the owning task via `bugfix` |
| `tests/test_t0*.py` | Per-task unit suites belong to their tasks; independence (AC #11) requires not reusing them |
| `memory/**`, `PROJECT_KANBAN.md`, `PRD.md` | Supervisor-only writes |

---

## Test Plan

The suite *is* the test plan. Two points of discipline:

1. **Assertions come from `PRD.md`**, written before or without reading the implementation (AC #11).
2. **Skips are failures until proven otherwise.** A container test that skips because Docker is
   absent must appear in the KPI summary as "not verified", never as green. This suite is the v1
   release gate, and a gate that passes by skipping is worse than no gate.

The Supervisor signs off on this plan as the oracle before spawn — High Risk.

---

## Completion Checklist

- [ ] HITL gate answered; `PRD.md` FR-022 + KPI row reconciled by the Supervisor
- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (**High risk — mandatory**)
- [ ] `Skill({ skill: "blast-radius" })` run (sensitive data, High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T017.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: v1 release gate result reported
