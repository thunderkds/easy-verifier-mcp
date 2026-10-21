# TASK_GUIDE — T121: Secret hits in context files must not lower a narrow-scope security score
**Date**: 2026-10-21
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
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
6. Read `memory/codebase-map.md` (C2)

---

## Requirement (Pillar 1 — Adapt the requirement)

Field report (2026-10-21, consumer easy-personal-mcp, a `changes`-scope `score` of HUN-34 =
`3f4aceb^1...3f4aceb^2`): security scored **18** for a change that holds no secret. `redaction_hits_observed`
counted **123** hits. The Supervisor reproduced the run on develop `2004992` and grouped the hits by file:

| Hits | File | Detector | Changed by HUN-34? |
|---|---|---|---|
| 116 | `.claude/harness-lock.json` (path → sha256 manifest) | `high_entropy_hex` | No |
| 5 | `tasks/TASK_REVIEW_HUN-34.md` | `key_material_segment` ×3, `high_entropy_string` ×2 | Yes |
| 2 | `web/package-lock.json` | `high_entropy_string` | No |
| 0 | `uv.lock` | — | No |

The reporter suspected `uv.lock`, but most hits come from `.claude/harness-lock.json`. It matches the `lockfile`
role pattern `**/*-lock.*` (`core/roles.py:208`). `lockfile` is a **context role** (FR-078, `CONTEXT_ROLES`
in `core/roles.py:895`), so at a narrow scope it is read from the whole repository. FR-078 and the warning shown
to users (`CONTEXT_ROLE_WARNING`) both say context files are "cited, not measured". But
`_redaction_hits_observed` / `_redacted_file_share` (`core/metrics.py:781`, `:794`) count every
`pack.redactions` hit, context files included. Code the change never touched decides the security score. The
metric is weight 35 with target `≤ 0` (`core/judge.py:745`), so one hit fails it. A wrong low score teaches
people to ignore the security rating.

**Restated intent** (Supervisor's interpretation, in this project's domain language):
> At a narrow scope (`changes`, `worktree`, `task`), security's `redaction_hits_observed` and
> `redacted_file_share` measure only files in the scope's own file set. Secret hits in context-role files read
> from the whole repository are still redacted and still reported, but do not count in these metrics.
> `project` scope is unchanged.

**Out of scope** (what this task explicitly does NOT do):
- Any change to redaction itself: context files are still scanned and their values still replaced by fingerprints (never un-redact)
- New entropy exemptions (e.g. path → sha256 manifests like `harness-lock.json`). This is a possible follow-up only if project-scope noise proves material
- Changing the `lockfile` role patterns or the `CONTEXT_ROLES` set
- `project`-scope output (must stay byte-identical, as FR-078 requires)
- Other dimensions' metrics

**Requirement Refs**:
- FR-078 (context roles are cited, not measured): this task makes security's secret metrics obey it
- FR-088: "At a narrow scope, security's secret metrics count only hits in the scope's measured files; context-file hits are reported separately and do not lower the score."

### Requirement Fidelity Gate (sign off BEFORE implementation) — signed 2026-10-21, owner said "start and merge to develop for all tasks"

- [x] Restated intent confirmed to match the user's request
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (context role, measured files, narrow scope)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] New FR added to `PRD.md` and covered by the Acceptance Criteria

> An agent must NOT start implementing until this gate is checked.

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `score` / `write_report` → `core/metrics.py` `_redaction_hits_observed`, `_redacted_file_share` via `_PackView`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `changes` scope; secret-shaped value only in an unchanged lockfile (context role) → `redaction_hits_observed` = 0 and passes | context not measured |
| 2 | `changes` scope; same value in a changed source file → counted (≥ 1), fails as today | measured files still count |
| 3 | The context-file hits stay visible: their count appears in the metric's derivation (or a warning), and the excerpt text still carries the fingerprint, never the raw value | still redacted and reported |
| 4 | `redacted_file_share` uses the same measured-file set for numerator and denominator | both metrics |
| 5 | `project` scope payload is byte-identical to before on an existing fixture | FR-078 byte-equality |
| 6 | Regression fixture modelled on HUN-34: a changed `.py` file plus an unchanged `.claude/x-lock.json` holding 64-hex digests → no secret hits counted | field report |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Fixture repo, commit A→B touches only `src/a.py`; `x-lock.json` holds hex digests | security `redaction_hits_observed` = 0 at `changes` | automated test |
| 2 | Same, but `src/a.py` gains `API_TOKEN = "<high-entropy>"` | count ≥ 1, metric fails | automated test |
| 3 | Real run: `easy-personal-mcp`, `--scope changes --ref 3f4aceb^1...3f4aceb^2` | security rating no longer driven by `harness-lock.json`; record before/after | `verify` skill, pasted in TASK_REVIEW |

### Verification Command (exact, runnable)

```bash
uv run pytest tests -k "redaction or context_role" -q
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled in `tasks/TASK_REVIEW_T121.md`. No UI: the three UI Evidence rows are ☐ N/A.

---

## Demonstration

> See `tasks/TASK_REVIEW_T121.md`. BEFORE: security 18, 123 hits (116 from `.claude/harness-lock.json`), develop `2004992`.

---

## Approach

**Pattern reference**: `role_files_in_scope` / `note_context_roles` (`core/roles.py`): how measured vs context files are already told apart; `_PackView.source_files` (`core/metrics.py:652`) for a filtered file set on the view.

**Vital slice**: the two secret metrics filter `pack.redactions` and `view.files` to measured (in-scope) paths at narrow scope.
**Cut list**: no new detector exemptions; no new payload keys beyond what AC 3 needs.

The pack must know which of its files are in scope. Use what the scope already resolves. Do not re-run git
inside the metric.

---

## Edge Case Checklist

- [ ] Narrow scope whose diff changes the lockfile itself → that lockfile is in scope, its hits count
- [ ] Hit with `path is None` → keep today's treatment, and document it
- [ ] Empty narrow scope → metric abstains as today
- [ ] `docs/EVALUATION_GUIDE.md` / `docs/SCORING_RULES.md` wording re-checked (learning 2026-10-05: rule changes must re-check EVALUATION_GUIDE)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | Measured-file filter for the two secret metrics |
| pack/view model (if the scope file set is not yet on the pack) | Carry the scope's file set |
| `tests/...` | Tests above |
| `PRD.md` | New FR (after gate) |
| `docs/SCORING_RULES.md`, `docs/EVALUATION_GUIDE.md` | One line: narrow scope counts measured files only |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/redact.py` | Redaction behaviour unchanged |
| `core/roles.py` `CONTEXT_ROLES` / patterns | Out of scope |

---

## Test Plan

Fixture git repo with two commits; assert the metric at `changes` and `project` scope; byte-equality on an
existing `project` fixture; canary that the raw value never appears in the payload.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T121.md`
- [ ] `Skill({ skill: "verify" })` run
- [ ] Supervisor notified: task ready for Stage 4 review
