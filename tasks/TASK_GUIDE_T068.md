# TASK_GUIDE — T068: Large repos — read code-tier sources in priority batches, continue or stop, resumable
**Date**: 2026-10-03
**Complexity Level**: C3
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C3 process from `.claude/agents/general-agent-template.md` (brainstorm + decompose before code)
6. Read `memory/codebase-map.md`, `docs/ddr/0010-evidence-floor-and-priority-batches.md` (main checkout only), `tasks/TASK_GUIDE_T067.md`, and the T031/T050 entries in `memory/decisions.md` (the all-or-none cap this task reverses)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-03): "with the large files, we should split the source by the purpose of file with the
project, or maybe the file is changed too much first, and work on priority, with each priority we can
ask users if they want to going on, or just stop for saving token, and the context is enough now, we
can save the process." Supervisor defaults accepted ("yes"): purpose class then churn; batch 200; MCP
asks continue/stop; CLI `--batches N` / `--all` (default 1); stateless resume.

**Restated intent**:
> On a repository with more source files than the cap, code-quality, architecture and test-strategy
> read the most important, most-changed files first in batches of 200, report honestly how much was
> read, and let the user continue batch by batch or stop to save tokens — without the agent ever
> carrying a number.

**Out of scope**:
- The measured-weight floor and gate change (T067).
- Rule weights/thresholds; non-code tiers (docs/config selection).
- Persisting state on disk outside `reports/`.

**Requirement Refs**:
- FR-060: purpose → churn → path ordering, batches of the cap, sample disclosure.
- FR-061: MCP `needs_input.continue_batches`; CLI `--batches N` / `--all`, default 1.
- FR-062: stateless continuation, engine recomputes batches 1…N, replay byte-equal.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (Supervisor, user "yes" 2026-10-03)
- [x] Domain terms align (tier, cap, batch, churn, sample)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

> C3: before coding, write a short design note (in `tasks/TASK_REVIEW_T068.md` under a `## Design`
> heading) covering purpose classification data, ordering key, metric merge across batches, and the
> exact `needs_input` / agent-input shapes. If any part conflicts with DDR-0010, STOP and report.

---

## Dependencies & Reachability

**Depends on**: T067 — measured-weight floor (a sample counts as measured; the floor decides what is rated)
**Entry point**: `continue_batches`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|----------------------|-----------|
| 1 | Above the cap, code tiers (`_code_extract.function_excerpts`, `import_excerpts`, test-strategy source reads) read batch 1 instead of nothing | FR-060 |
| 2 | Order = purpose class (application/server → other application → scripts/tooling → generated/vendored; class patterns declared as static data with a cited or project-default basis) → git churn desc → path; deterministic | FR-060 |
| 3 | Whole-set metrics over batches are computed over all files of batches 1…N (counts merged, max over all), and their derivation states "sample: batches N of M, X of Y files" | FR-060 |
| 4 | MCP `score` with remaining batches returns `needs_input.continue_batches {batches_done, batches_total, files_read, files_in_scope, question}`; calling again with `agent_input.batches = N+1` (or `"all"`) continues | FR-061 |
| 5 | CLI `--batches N` / `--all`; default 1; output discloses remaining batches and the flag to continue | FR-061 |
| 6 | The agent input never carries a count or metric; the engine recomputes batches 1…N; same input → byte-equal payload (DDR-0005); `batches` out of range → validation error | FR-062 |
| 7 | Repos at or under the cap behave exactly as before (no new keys except disclosure, parity unchanged) | regression |
| 8 | bryony: batch 1 reads 200 of 1,178 files; code-quality function metrics now computed (sample) — with T067 the dimension is rated or abstains honestly; continuing to batch 2 changes the sample size shown | user report |
| 9 | Token bound: each continued call's pack carries only excerpts within the existing byte budget (NFR-009 unchanged) | FR-060 |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|-------|--------|-----|
| 1 | Fixture repo, 450 synthetic source files across app/, scripts/, vendor/ with git history | batch 1 = 200 app files, most-churned first; 3 batches total | automated |
| 2 | Same fixture `batches=3` vs `all` | identical payload | automated |
| 3 | Metric over batches 1–2 | equals the metric computed directly over those 400 files | automated (oracle) |
| 4 | MCP first call | `needs_input.continue_batches` present with correct counts | automated |
| 5 | `batches=0`, `batches=99`, `batches="x"` | validation error | automated |
| 6 | Repo with 50 sources | payload identical to develop | automated (snapshot) |
| 7 | bryony CLI `--batches 1` then `--batches 2` | sample size 200 → 400; ratings disclosed as sample | verify, pasted |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t068_priority_batches.py -q
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T068.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T068.md`.

---

## UI / Design Acceptance Criteria

Report shows the sample disclosure ("batches 1 of 6, 200 of 1,178 files") beside affected dimensions; reuse existing styles.

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|---|---|---|
| Score panel sample disclosure | headless Chromium + LLM vision | disclosure visible on each sampled dimension |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|---|---|---|
| Colors / typography | CSS audit | existing classes only |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|---|---|---|
| 400px (iframe) / 1280px | screenshot | no horizontal page scroll |

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/_code_extract.py` (tier reading, warnings), `src/easy_verifier/core/git.py` (churn), `src/easy_verifier/core/gate.py` + `roles.validate_agent_input` (needs_input / agent_input round trip, stateless).

Replace the all-or-none branch with: classify → order → slice batches 1…N → read. Keep metric computation reading what the pack quotes; if merging requires counts beyond the excerpt budget, compute metric inputs from the full batch read and quote within budget — state this in the Design note.

---

## Edge Case Checklist

- [ ] No git history (tarball) → churn 0 for all, order falls back to purpose → path, disclosed
- [ ] Secret-bearing files still refused by `read_source`
- [ ] Generated/vendored detection never drops files silently — they are last, not excluded
- [ ] `batches` beyond total → error, not clamp
- [ ] Byte budget truncation inside a batch still reported (FR-027a)
- [ ] Parity CLI vs MCP (needs_input excluded per existing rule)
- [ ] Repos ≤ cap unchanged

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `src/easy_verifier/dimensions/_code_extract.py` | batches instead of all-or-none |
| `src/easy_verifier/dimensions/test_strategy.py` | same for `MAX_TEST_SOURCES` |
| new `src/easy_verifier/core/batches.py` (or similar) | purpose classes, ordering, cursor |
| `src/easy_verifier/core/score.py`, `roles.py`, adapters | `batches` input, `continue_batches` needs_input, CLI flags |
| `src/easy_verifier/core/report.py` | sample disclosure |
| `tests/test_t068_priority_batches.py` | new |
| `docs/SCORING_FLOW.md` | describe batches |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `judge.py` rules/weights/floors | user-signed |
| `core/redact.py` | unchanged |
| T067's floor logic | owned by T067 |

---

## Test Plan

Fixture repo with git history for ordering/merge oracles; parity; Stage 5 on bryony (batches 1, 2) and a second real repo.

---

## Completion Checklist

- [ ] Design note written before code
- [ ] Implementation done
- [ ] `Skill({ skill: "code-review" })`
- [ ] `Skill({ skill: "security-review" })` (Medium)
- [ ] Lint passes
- [ ] Tests written AND pass — pasted in `tasks/TASK_REVIEW_T068.md`
- [ ] `Skill({ skill: "verify" })` on bryony + second repo
- [ ] Supervisor notified
