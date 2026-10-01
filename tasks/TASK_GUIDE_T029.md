# TASK_GUIDE — T029: Bugfix: redact.py high_entropy_string false positive on ordinary filenames
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: High
**Priority**: P0
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0001-redact-secrets-at-evidence-layer.md` and `docs/ddr/0002-never-read-secret-bearing-files.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

Found by T026 (kanban): `redact.py`'s `high_entropy_string` detector rewrites ordinary repo paths, e.g. `BRAINSTORMING_LOG_source-discovery.md` → `BRAI…****:54e5675171d4.md` (4 of 156 tracked paths), so citations to those files cannot resolve. `core/roles.py` narrows the decision-record glob to the exact `BRAINSTORMING_LOG.md` as a temporary workaround. Prerequisite for the registry work (DDR-0007): registry citations must survive redaction.

**Restated intent**:
> Ordinary file names and repo-relative paths survive redaction unchanged, while every secret the current detectors catch is still fingerprinted.

**Out of scope**:
- Changing any named detector or the fingerprint format
- Any registry work (T030+)

**Requirement Refs**:
- NFR-010 / FR-015a: citations must resolve (paths survive redaction)
- DDR-0001, DDR-0002: secrets still redacted at the evidence layer
- FR-031: decision-record role pattern can be widened back

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `redact`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | A reproducing test: `redact("BRAINSTORMING_LOG_source-discovery.md")` returns the input unchanged (fails before the fix) | false positive on ordinary paths |
| 2 | All 156 tracked paths of this repo (`git ls-files`) pass through `redact` unchanged | 4 of 156 paths |
| 3 | Every existing redaction test still passes; a mixed-case+digit high-entropy token (e.g. `pB4kQ9zXmR7tY2wEaB3xK9mQ7rT2vY8w`) is still fingerprinted, including inside a path segment | secrets still caught |
| 4 | The `decision-record` role in `core/roles.py` is widened back to `BRAINSTORMING_LOG*.md` and a citation to `BRAINSTORMING_LOG_source-discovery.md` resolves | temporary narrowing removed |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `redact("BRAINSTORMING_LOG_source-discovery.md")` | unchanged string | automated test |
| 2 | a 32-char random mixed-case+digit token in a path segment | fingerprinted | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T029.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T029.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/redact.py` `_PATHISH` / `_KEY_MATERIAL_CANDIDATE` — the existing path-safety reasoning; extend it rather than add a bypass

Bug-fix flavour (Task Transformation Table): write the reproducing test first, then diagnose with `Skill({ skill: "diagnose" })`. Likely cause: the long-token `_ENTROPY_CANDIDATE` (`[A-Za-z0-9+/=_-]{32,512}`) matches underscore/hyphen-joined words that clear the 4.0-bit bar. Prefer a narrow rule (e.g. a candidate made of dictionary-like word segments separated by `_`/`-` with a file suffix is not key material) over weakening the entropy bar. Record the residual risk in the module docstring, as existing rules do.

---

## Edge Case Checklist

- [ ] A real secret that happens to contain `_` or `-` (e.g. base64url tokens) must still fingerprint
- [ ] Long snake_case identifiers in code (not paths) — decide and test explicitly
- [ ] Paths with a hash-like segment (e.g. build artefact names) — keep current behaviour documented

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/redact.py` | narrow the long-token rule |
| `src/easy_verifier/core/roles.py` | widen decision-record back to `BRAINSTORMING_LOG*.md` |
| `tests/` | reproducing + regression tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| named detectors in `redact.py` | out of scope |
| fingerprint format | stable across runs by decision |

---

## Test Plan

Reproducing unit test; whole-repo path sweep test over `git ls-files`; existing redaction suite unchanged.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T029.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
