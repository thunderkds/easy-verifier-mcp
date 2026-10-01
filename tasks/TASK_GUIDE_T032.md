# TASK_GUIDE — T032: Build-time vendoring of Linguist, OWASP ASVS and MITRE CWE (version-pinned)
**Date**: 2026-09-28
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: common-infrastructure
**Agent guide**: `.claude/agents/common-infrastructure.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/common-infrastructure.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): "we should build the RAG source also I think, maybe a online database, or resource to refer"; decided (B3): vendor structured sources offline — Linguist (MIT), OWASP ASVS (CC BY-SA 4.0), MITRE CWE; no Semgrep, no RAG, no runtime network.

**Restated intent**:
> A maintainer script refreshes pinned snapshots of the three sources into the package; the engine reads only the vendored files at runtime.

**Out of scope**:
- Any runtime network access
- Semgrep rules
- Writing per-dimension rules (T035)

**Requirement Refs**:
- FR-049: offline, version-pinned seeding
- NFR-001 / no-network constraint

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T030 — registry location and schema

**Entry point**: `vendor_sources.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `scripts/vendor_sources.py` downloads Linguist `languages.yml`, ASVS JSON and CWE XML at pinned versions/commits, extracts only needed fields (extensions/filenames; requirement IDs+titles+URLs; CWE IDs+names+URLs) into `registry/vendored/` | vendor offline |
| 2 | Each vendored file records source URL, version/commit, retrieval date and licence (SPDX id + attribution) | pinned + licensed |
| 3 | Runtime code never imports the script and makes no network call (test asserts no `urllib`/`socket` use under `src/`) | no runtime network |
| 4 | Vendored files stay small (target < 500 KB total) and are committed | bounded footprint |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | run script with pinned versions | reproducible byte-identical output | manual + automated checksum test |
| 2 | grep `src/` for network modules | no hits | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
python scripts/vendor_sources.py --check  # verifies committed snapshots match pins
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T032.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T032.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `scripts/` existing maintainer scripts (e.g. `scripts/verify_container.sh`) — standalone, not part of the package

Standard library only (`urllib.request` in the script, never in `src/`). Filter aggressively: keep only fields the registry uses. Include CC BY-SA attribution for ASVS in `registry/vendored/NOTICE`.

---

## Edge Case Checklist

- [ ] Upstream format change → script fails loudly, committed snapshot unaffected
- [ ] `--check` mode for CI without network uses committed checksums

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `scripts/vendor_sources.py` | new |
| `src/easy_verifier/registry/vendored/*` | new snapshots + NOTICE |
| `pyproject.toml` | package data |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/* | runtime stays offline |

---

## Test Plan

Checksum test of committed snapshots; no-network import test.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T032.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
