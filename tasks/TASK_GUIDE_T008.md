# TASK_GUIDE — T008: security dimension (bespoke)
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2** — apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md`
7. Read `src/easy_verifier/core/redact.py` (T004) end to end before writing a line — this dimension surfaces exactly the content redaction exists to protect

---

## Requirement (Pillar 1 — Adapt the requirement)

Gather security-relevant evidence from any repository, in any mode, in any scope — and never let a
raw credential out while doing it.

**Restated intent**:
> The `security` dimension returns citable evidence about the repo's security surface — credential
> material (fingerprinted, never raw), dependency manifests, auth/crypto-touching code, permission
> and container configuration — with a declared `sources_sought` list. It is available in standalone
> mode and in every scope, and is never gated behind kit-aware mode.

**Out of scope**:
- Judging severity, exploitability, or whether a finding is a real vulnerability — that is the
  calling agent's reasoning (FR-013).
- Running any external scanner that executes target-repo code or reaches the network.
- Fixing anything (FR-024, NFR-007).

**Requirement Refs**:
- FR-010: `security`, 1 of 7
- FR-011: structured evidence pack with citable excerpts and a miss list
- FR-012: callable in both modes and every scope, never gated behind kit-aware mode
- FR-013: evidence only, no verdict
- NFR-003: available in every mode and scope, expected on non-trivial change sets
- NFR-010: detected secrets fingerprinted at the evidence layer
- NFR-007: never write to the target repo, never execute its code
- NFR-012: no outbound network request

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T004 — real redaction must be in place before a dimension deliberately seeks credential material; T005 — `budget()` for lazy bounded output.

**Entry point**: `collect` (in `dimensions/security.py`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `security` ships as a descriptor + `collect`, **bespoke** — it does not import `_doc_extract` | FR-009, Constraint 8 |
| 2 | Returns a valid pack in standalone mode with zero kit artifacts present | FR-012, NFR-003 |
| 3 | Returns a valid pack in all four scopes | FR-012 |
| 4 | Every excerpt passes through redaction — a test seeds fake secrets and asserts zero raw values in the pack | NFR-010 |
| 5 | Credential hits preserve detector name, file path and line number so the finding stays actionable | NFR-010 |
| 6 | Evidence categories covered: credential material, dependency manifests/lockfiles, auth- and crypto-touching code, permission/container/CI configuration | FR-010, FR-011 |
| 7 | `sources_sought` is declared statically and the miss list names what was absent | FR-016, FR-016a |
| 8 | No severity, CVSS, risk rating or verdict field anywhere in the output | FR-013 |
| 9 | Makes no network request and executes nothing from the target repo — asserted structurally | NFR-012, NFR-007 |
| 10 | `collect` returns a lazily-consumed `Iterable[Excerpt]` | Critical Constraint 3 |
| 11 | **Secret-bearing files are never read by default.** `security` may report that a `.env`/`*.pem`/`id_rsa` *exists* — itself a legitimate finding — but its contents are withheld and the source is recorded `excluded: secret-bearing`, distinct from `not found` and `not examined`. A test asserts the bytes never reach a pack | DDR-0002, Constraint 4a |
| 12 | **HITL gate**: when this dimension needs an excluded file's contents, it surfaces a per-file approval request to the operator and **defaults to refuse** — it neither silently refuses nor silently complies. A test asserts the default path withholds contents when no approval is given | DDR-0002 |
| 13 | Coverage accounting stays honest with exclusions present — an excluded file is not counted as `found` for a dimension that never saw its contents | FR-016, DDR-0002 |

> **Note (DDR-0002).** `security` is the **only** planned dimension with a genuine
> reason to request excluded contents, which is why the HITL gate lives here and
> nowhere else. The friction is deliberate: a security tool that silently reads
> every credential it finds is precisely the outcome being avoided. Beware the
> rubber-stamp failure mode — if operators approve without reading, the gate is
> worse than useless because it manufactures a false record of consent.

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Temp repo seeded with 5 distinct fake secrets across 3 files | 5 fingerprinted hits with correct paths and line numbers; zero raw values in the serialized pack | automated test |
| 2 | A plain standalone repo (installed pip package) | Valid pack, standalone warning present, no crash on absent kit artifacts | automated test |
| 3 | This repo, `changes` scope over the last commit | Evidence limited to the changed set | automated test |
| 4 | A repo with no dependency manifest and no auth code | Valid pack, sources in the miss list, coverage below 1.0, nothing invented | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t008_security.py -q && \
  python -m easy_verifier.adapters.cli security --repo . --scope project | head -30
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T008.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T008.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/architecture.py` (T001) for the descriptor shape; `src/easy_verifier/core/redact.py` (T004) for the detector-as-data style.

Bespoke means bespoke: this dimension's evidence is not "passages from documents", so forcing it
through `_doc_extract` would require widening that helper with security-specific branching —
precisely the failure mode `PROJECT_SPEC.md` Constraint 8 exists to prevent. Write it standalone
even where a few lines look duplicative.

Reuse T004's detectors for credential discovery rather than writing a second detector set. Two
divergent detector lists in one codebase is a guarantee that one of them is wrong.

Keep the "is this bad?" question entirely out of the module. A `requirements.txt` with a pinned old
version is evidence; whether that matters is the agent's call with its own knowledge of advisories,
which the engine does not have and must not pretend to (NFR-001).

---

## Edge Case Checklist

- [ ] A secret in a file that is itself in `.gitignore` (a real `.env` on disk) → found, fingerprinted; note that it is untracked
- [ ] `.env.example` / `.env.sample` with placeholder values → still redacted (the engine does not judge realness)
- [ ] Enormous lockfile (`package-lock.json` at MB scale) → bounded, does not consume the whole budget alone
- [ ] Vendored dependencies / `node_modules` / `.venv` → excluded, or the scan drowns in third-party code
- [ ] Binary files, images, compiled artifacts → skipped, not scanned as text
- [ ] Minified JS with high-entropy strings → false positives expected; bounded, and the pack must not become 100% noise
- [ ] Git history containing a removed secret → **out of scope** for v1; state this explicitly in the miss list rather than silently not looking
- [ ] `changes` scope where the diff *removes* a secret → the removed line should not be re-surfaced as a live finding
- [ ] Repo with no `.git` at all → `project` scope still works
- [ ] Symlinks pointing outside the repo → not followed
- [ ] This repo evaluating itself: T004's own test fixtures are full of fake secrets → the dimension will flag them, which is correct behaviour and should be visible in the demo, not suppressed

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/security.py` | New — bespoke descriptor + `collect` |
| `tests/test_t008_security.py` | New |
| `tests/fixtures/seeded_secrets/` | New — fake, non-functional secret fixtures |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/redact.py` | Owned by T004 — reuse it, do not edit it; if a detector is missing, raise it with the Supervisor as a T004 follow-up |
| `src/easy_verifier/dimensions/_doc_extract.py` | Owned by T007 and capped at four callers |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t008_security.py`. The load-bearing test is AC #4's: build a temp repo with known fake
secrets, run the full dimension through `run_dimension()`, serialize the pack, and assert each raw
value appears zero times — this is the same class of proof as T004's and is repeated here because
this is the dimension that goes looking for the material on purpose. Add a structural test asserting
`security.py` neither imports `_doc_extract` nor contains any network or subprocess call.

Fake secrets must be syntactically valid and non-functional; use published example values where they
exist.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required)
- [ ] `Skill({ skill: "blast-radius" })` run (sensitive-data handling, Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T008.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
