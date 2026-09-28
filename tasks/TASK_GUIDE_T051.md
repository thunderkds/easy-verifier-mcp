# TASK_GUIDE — T051: Redaction false positives: content hashes, long identifiers, git-ignored files
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
7. Read `docs/ddr/0001-redact-secrets-at-evidence-layer.md`, `docs/ddr/0002-never-read-secret-bearing-files.md`, `tasks/TASK_REVIEW_T029.md` and `tasks/TASK_REVIEW_T035.md` (sign-off findings)

---

## Requirement (Pillar 1 — Adapt the requirement)

User sign-off of T035 (2026-09-28, 'Merge + fix tasks'): security's `redaction_hits_observed ≤ 0` rule (40/100) is dominated by false positives. On this repo 94 hits are sha256 content hashes in `.claude/harness-lock.json`; most others are long snake_case test names (`def test_agent_guide_dedup…()`) and suffix-less paths; the scan also reads git-ignored `.claude/`. kitchd 222, bryony 132, ai-training 271 hits.

**Restated intent**:
> `redaction_hits_observed` counts real secret shapes only: labelled content hashes and word-only identifiers are not fingerprinted, git-ignored files are not scanned, and every real secret shape the suite covers is still caught.

**Out of scope**:
- Changing named detectors or the fingerprint format
- Changing the security rule weights (T035)

**Requirement Refs**:
- DDR-0001/0002: secrets still redacted at the evidence layer
- FR-043 security rule validity
- NFR-002: no invented findings

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T035 — security rule weighs redaction hits at 40

**Entry point**: `redact`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Hex digests in a hash context (JSON/TOML/YAML value or key named like sha1/sha256/sha512/integrity/hash/checksum/digest, lockfile integrity fields like `sha512-…`, git SHAs in lock files) are not fingerprinted; a hex-looking value under a secret-named key (token, secret, password, api_key) still is | content hashes |
| 2 | Word-only identifiers (letters-only pieces joined by `_`, e.g. `test_agent_guide_dedup_rules_apply`) are not fingerprinted by the long-token rule even without a file suffix — extending T029's piece-shape exemption with the same guards (≥2 pieces, each single-case or Capitalized letters-only); any digit or mixed-case piece keeps the current behaviour | long identifiers |
| 3 | The evidence walk skips files ignored by the target repo's `.gitignore` (git available: `git check-ignore`/`ls-files --others --ignored --exclude-standard`; no git: current behaviour) — decided once per run, documented; secret-bearing file guard unchanged | git-ignored files |
| 4 | All existing redaction/secret tests still pass; a sweep over this repo shows 0 fingerprints on tracked files that contain no real secret; kitchd/bryony/ai-training counts before/after recorded | no regression + real-repo evidence |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `"sha256": "<64 hex>"` in a lock JSON | unchanged | automated test |
| 2 | `API_TOKEN = "<64 hex>"` | fingerprinted | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T051.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T051.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/redact.py` T029 `_WORD_JOINED_NAME` exemption with sabotage-tested guards

Three narrow, sabotage-tested exemptions; never lower entropy bars. Hash context is decided from the key/label on the same line, not from the value alone. Record residual risk in the module docstring as T029 did.

---

## Edge Case Checklist

- [ ] A real secret stored under a key named `hash` — document as residual
- [ ] Monorepo nested .gitignore files
- [ ] Repo that is not a git repo (tarball) — unchanged behaviour
- [ ] Performance: git ignore check done once per run, not per file

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/redact.py` | hash-context + identifier exemptions |
| `src/easy_verifier/core/context.py` | honour .gitignore in the walk |
| `tests/` | reproducers + sweeps |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | rule weights are T035's |
| fingerprint format | stable by decision |

---

## Test Plan

Reproducers for each false-positive class; still-caught twins; this-repo sweep; before/after counts on the 3 external repos (read-only).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T051.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
