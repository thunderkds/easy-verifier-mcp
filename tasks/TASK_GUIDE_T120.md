# TASK_GUIDE — T120: Score JSON sidecar next to each HTML evidence report
**Date**: 2026-10-21
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read the memory slice in your spawn prompt (`<!-- memory-slice -->`). Read `memory/MEMORY.md` in full only if your work reaches a file, hook, skill or decision the slice does not cover
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in your role guide
6. **C2/C3 or multi-file tasks only**: read `memory/codebase-map.md` — skip for this C1 task unless the change spreads beyond `core/report.py`

---

## Requirement (Pillar 1 — Adapt the requirement)

Cross-repo request from easy-personal-mcp (its XR-1; consumer task HUN-42, PRD FR-011 there): easy-personal
shows a person's verifier scores over time per project, read-only, from files on disk. Today easy-verifier
leaves only `evidence-report-<scope>-<UTC>.html`, so a reader would have to parse HTML. The owner chose
(2026-10-21) that easy-verifier writes a machine-readable score file next to each HTML report.

**Restated intent** (Supervisor's interpretation, in this project's domain language):
> Every successful `write_report` also writes `evidence-report-<scope>-<UTC>.json` in the same reports
> directory, holding the rendered score summary (the same numbers the HTML shows), with a schema version.

**Out of scope** (what this task explicitly does NOT do):
- Changing the HTML report, scoring, findings validation or any dimension
- Writing anywhere other than the directory the HTML goes to (`<repo>/reports/` or `$EASY_VERIFIER_REPORTS_DIR/<repo>/`)
- Back-filling JSON for existing HTML reports
- Any finding text, evidence excerpt or agent-authored prose in the JSON

**Requirement Refs** (add to this repo's `PRD.md` as a new FR when the gate is signed):
- FR-087: "Each evidence report must have a sibling JSON score summary with the same base name, `schema_version`, scope, UTC timestamp, overall score and per-dimension ratings; no finding text."

### Requirement Fidelity Gate (sign off BEFORE implementation) — signed 2026-10-21, owner said "start and merge to develop for all tasks"

- [x] Restated intent confirmed to match the user's request (by this repo's Supervisor / the owner)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] The new FR is added to `PRD.md` and covered by the Acceptance Criteria

> An agent must NOT start implementing until this gate is checked.

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `write_report` (`src/easy_verifier/core/report.py`), reached from `adapters/cli.py` and `adapters/mcp_server.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | After `write_report` succeeds, a `.json` file with the HTML's base name exists in the same directory | sibling file |
| 2 | JSON holds `schema_version`, `scope`, `generated_at` (UTC), overall score (or its abstain state) and per-dimension rating/abstain, matching the HTML's rendered values | same numbers |
| 3 | JSON contains no finding text, evidence excerpts, agent input or file contents (test with a planted canary in findings and agent input) | no prose |
| 4 | Validation failure writes neither file; a JSON write failure removes the HTML too (no half pair) | atomic pair |
| 5 | With `EASY_VERIFIER_REPORTS_DIR` set, the JSON goes to `$EASY_VERIFIER_REPORTS_DIR/<repo>/` like the HTML | same directory rule |
| 6 | Output is deterministic for the same input (sorted keys) | determinism |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | A fixture repo + valid findings | HTML + JSON pair; JSON overall equals HTML overall | automated test |
| 2 | Canary string in a finding and in agent input | Canary absent from the JSON | automated test |
| 3 | Unevidenced finding | `ValidationError`, no files | automated test |

### Verification Command (exact, runnable)

```bash
uv run pytest tests -k "report and json" -q
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T120.md`. No UI: the three UI Evidence rows are ☐ N/A.

---

## Demonstration

> See `tasks/TASK_REVIEW_T120.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/report.py` `_write_new_file` / `_filename` (naming, directory rules) and `core/score.py` `serialize` (sorted, ASCII JSON)

**Vital slice**: sibling JSON written in `write_report` from the same `CoverageSummary` the HTML renders
**Cut list**: no back-fill of old reports; no JSON schema file published beyond a `schema_version` integer and a docstring describing the keys

Derive the JSON from the same summary object the HTML header uses, so the two cannot disagree. Write HTML and
JSON as a pair; on failure of the second write, remove the first.

---

## Edge Case Checklist

- [ ] Abstained overall score → JSON states abstain, never 0
- [ ] Filename collision with an existing JSON → same no-overwrite rule as the HTML
- [ ] Reports dir guard (`_guard_reports_dir`) applies to the JSON too
- [ ] Non-ASCII repo names in `EASY_VERIFIER_REPORTS_DIR/<repo>/`

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/report.py` | Write the JSON sibling; pair-atomic write |
| `tests/...` | Tests above |
| `src/easy_verifier/core/context.py`, `core/scope.py`, `core/roles.py` | `_is_report_artifact` predicate used in all three walks (authorised by Supervisor 2026-10-21: prevent sidecar re-ingestion) |
| `PRD.md` | New FR (after gate sign-off) |
| `README.md` | One line under reports: the JSON sibling and its keys |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/dimensions/**` | Scoring unchanged |
| HTML rendering functions | Out of scope |

---

## Test Plan

Unit tests on `write_report` with a fixture repo: pair written, values equal, canary absent, failure leaves no half pair, env-dir rule.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T120.md`
- [ ] `Skill({ skill: "verify" })` run
- [ ] Supervisor notified: task ready for Stage 4 review
