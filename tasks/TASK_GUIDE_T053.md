# TASK_GUIDE — T053: Remaining redaction noise: versioned URL paths, commit SHAs in prose, checksum lines; API_TOKEN detector gap
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: High
**Priority**: P1
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
7. Read `docs/ddr/0001-redact-secrets-at-evidence-layer.md`, `tasks/TASK_REVIEW_T029.md`, `tasks/TASK_REVIEW_T051.md` (remaining false-positive classes and residual risks)

---

## Requirement (Pillar 1 — Adapt the requirement)

T051 Stage 4 (2026-09-28): after the three T051 exemptions, 125 hits remain over 4 repos. Remaining false-positive classes: digit-bearing URL path segments (e.g. `v5.0.0_release` in the vendored `registry/vendored/asvs.json`, 346 hits on a tracked-file sweep), commit SHAs in CHANGELOG/prose and URLs, `sha256sum`-style `<hex>  <file>` lines, `key=CONSTANT` shapes (`content=SYSTEM_PROMPT`, `license: BSD-3-Clause`), and generated report filenames. Also `credential_assignment` misses `API_TOKEN = …` (no word boundary after `_`).

**Restated intent**:
> The remaining non-secret shapes stop being fingerprinted without opening a path for real secrets embedded in URLs, and `API_TOKEN = …` is caught by the named detector.

**Out of scope**:
- Lowering entropy bars
- Changing the fingerprint format
- Changing rule weights

**Requirement Refs**:
- DDR-0001: secrets redacted at the evidence layer
- FR-043 security rule validity
- NFR-002

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T051 — hash/identifier exemptions and ignore filter

**Entry point**: `redact`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | A URL path segment that is a version/release label (e.g. `v5.0.0_release`, `1.2.3`, `release-2024-01`) is not fingerprinted; a high-entropy mixed-case+digit segment in a URL path or query (webhook token shape) still is — twins for both | versioned URL paths vs embedded tokens |
| 2 | A 7–40 hex commit SHA in prose or a changelog/URL commit path (`/commit/<sha>`) is not fingerprinted; `sha256sum` output lines (`<64 hex>  <path>`) are not; a hex value under a secret-named key still is | commit SHAs + checksum lines |
| 3 | `KEY=UPPER_SNAKE_CONSTANT` and SPDX licence identifiers are not fingerprinted; quoted random values are | constants |
| 4 | `credential_assignment` catches `API_TOKEN = "…"`, `SERVICE_API_KEY=…`, `db_password: …` (underscore-joined secret names) | detector gap |
| 5 | Tracked-file sweep of this repo: 0 fingerprints on files with no real secret (including vendored asvs.json); 4-repo counts before/after recorded with a sample of what remains | real evidence |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `https://github.com/OWASP/ASVS/blob/v5.0.0_release/x.json` | unchanged | automated test |
| 2 | `https://hooks.slack.com/services/T0A1B2C3/B4D5E6F7/aB3xK9mQ7rT2vY8wZ1cD` | token segment fingerprinted | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T053.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T053.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/redact.py` T029/T051 exemptions — position + shape, each guard sabotage-tested, residual risk in the docstring

Narrow, context-anchored exemptions only; every exemption paired with a still-caught twin and a sabotage test. Prefer fixing the named detector (word-boundary handling for `_`-joined secret names) over new entropy exemptions.

---

## Edge Case Checklist

- [ ] Short SHAs vs short random tokens (length floor)
- [ ] URL query strings (`?token=…`) must stay caught
- [ ] Base64 JWT segments in URLs stay caught

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/redact.py` | exemptions + detector fix |
| `tests/` | twins + sweeps |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | rule weights |
| fingerprint format | stable |

---

## Test Plan

Twins per class, sabotage per guard, tracked-file sweep, 4-repo counts (read-only).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T053.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
