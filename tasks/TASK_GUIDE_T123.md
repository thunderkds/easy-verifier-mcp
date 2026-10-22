# TASK_GUIDE — T123: Report sensitivity notice names where the report was actually written
**Date**: 2026-10-21
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P2
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

---

## Requirement (Pillar 1 — Adapt the requirement)

Field report (2026-10-21, consumer easy-personal-mcp): the report's sensitivity notice said it was "written
inside the evaluated repository". It was written to `~/.easy-verifier-reports/`, because
`EASY_VERIFIER_REPORTS_DIR` was set (DDR-0013, FR-017 amendment). `SENSITIVITY_ADVISORY`
(`core/report.py:85`) is one fixed string from before DDR-0013. The notice exists to warn before sharing, so
wrong location text misleads.

The same report asked for `score` to write the report itself. The owner chose (2026-10-21) to **keep the two
calls separate**, because findings come after reading the score. This task fixes only the notice.

**Restated intent** (Supervisor's interpretation, in this project's domain language):
> The sensitivity notice states the real destination. With `<repo>/reports/` it keeps today's wording. With
> `EASY_VERIFIER_REPORTS_DIR` it says the report is outside the evaluated repository, in the shared reports
> directory, and that it still quotes the repository's source and paths. Both the HTML notice and the
> `advisory` string returned by `write_report` use the same text.

Supervisor 2026-10-21: first-write marker included (same defect)

**Out of scope** (what this task explicitly does NOT do):
- `score` writing a report (owner declined 2026-10-21)
- The first-write-only rule for returning `advisory`
- Any other report content

**Requirement Refs**:
- FR-017 (amended, DDR-0013), NFR-011 (notice names the real exposures)

### Requirement Fidelity Gate (sign off BEFORE implementation) — signed 2026-10-21, owner said "start and merge to develop for all tasks"

- [x] Restated intent confirmed to match the user's request
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement

> An agent must NOT start implementing until this gate is checked.

---

## Dependencies & Reachability

**Depends on**: T120 should merge first, or sequence after it. Both edit `write_report` in `core/report.py`.

**Entry point**: `write_report` → `_render_advisory` (`core/report.py:485`), `_reports_dir` (`:311`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Env unset → notice text unchanged (HTML and returned `advisory`) | default unchanged |
| 2 | `EASY_VERIFIER_REPORTS_DIR` set → notice does not claim "inside the evaluated repository" and says it is outside it | real destination |
| 3 | HTML notice and returned `advisory` are the same string in both modes | one source of truth |
| 4 | Both texts still name the hosted-model exposure and that excerpts quote real source (NFR-011) | notice purpose kept |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Fixture repo, env unset | today's text | automated test |
| 2 | Fixture repo, env = tmp abs path | outside-repo text in HTML and `advisory` | automated test |

### Verification Command (exact, runnable)

```bash
uv run pytest tests -k "report and advisory" -q
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled in `tasks/TASK_REVIEW_T123.md`. No UI logic change beyond notice text: the three UI Evidence rows are ☐ N/A, with this justification: the existing notice element's text changes, not its layout.

---

## Demonstration

> See `tasks/TASK_REVIEW_T123.md`.

---

## Approach

**Pattern reference**: `SENSITIVITY_ADVISORY` and `_render_advisory`. Pick the text from whether `REPORTS_DIR_ENV` resolved the directory. Keep the constant name exported (it is in `__all__`, `core/report.py:1982`), or add a second constant beside it.

**Vital slice**: two notice texts and one selection point.
**Cut list**: nothing else.

---

## Edge Case Checklist

- [ ] `EASY_VERIFIER_REPORTS_DIR` set but empty → treated as unset (today's rule), so default text
- [ ] Doc test pinning identifiers still passes if a constant is added
- [ ] `docs/EVALUATION_GUIDE.md` quoting the notice, if it does, updated

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/report.py` | Second notice text, selection |
| `tests/...` | Tests above |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `adapters/mcp_server.py` `score` | Owner declined score-writes-report |

---

## Test Plan

`write_report` on a fixture repo, env unset vs set (monkeypatch); assert HTML contains and `advisory` equals the
expected text.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T123.md`
- [ ] `Skill({ skill: "verify" })` run
- [ ] Supervisor notified: task ready for Stage 4 review
