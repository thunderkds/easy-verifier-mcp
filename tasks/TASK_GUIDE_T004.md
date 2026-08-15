# TASK_GUIDE — T004: redact.py — evidence-layer secret fingerprinting
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: **High**
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## ⛔ HITL Gate — do not start until this is answered

**Open item #14 (DDR-0001 follow-up).** The Supervisor must record the user's decision here before
this task is spawned:

| Question | Options | Decision |
|---|---|---|
| Is the fingerprint hash **salted**? | **Unsalted** — the same secret fingerprints identically across scans, so a reviewer can correlate "this key appears in three places" — but low-entropy secrets (short passwords, common tokens) become dictionary-attackable from the fingerprint alone. **Salted** — resists that attack, but destroys cross-scan and cross-file correlation, and the salt then needs a lifetime and a storage location, which is new surface. | _unanswered_ |
| Hash algorithm | SHA-256 is the safe default | _unanswered_ |
| Hash prefix length | e.g. first 8 or 12 hex chars — long enough to avoid collisions in one report, short enough to stay unusable | _unanswered_ |
| Mask width | e.g. first 4 chars of the raw value retained, remainder masked — retaining *any* prefix is itself a small disclosure | _unanswered_ |

> Recommendation if the user has no preference: **unsalted SHA-256, 12-char hash prefix, 4-char
> masked prefix** — correlation across a report is the property that makes a fingerprint actionable,
> and the dictionary-attack risk is mitigated by never emitting the fingerprint anywhere the raw
> secret was not already present. Record the choice in `memory/decisions.md` as a DDR-0001 follow-up
> either way.

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2 / High Risk** — apply the C2 process from the Complexity matrix; expect mandatory `security-review` at Stage 4
6. **C2** — read `memory/codebase-map.md`
7. Read `docs/ddr/0001-redact-secrets-at-evidence-layer.md` **if present** — it is gitignored and local-only, so it may be absent; `memory/decisions.md` duplicates its rationale

---

## Requirement (Pillar 1 — Adapt the requirement)

Make it structurally impossible for a raw secret value to leave the engine.

**Restated intent**:
> `redact(text)` replaces every detected secret with a non-reversible fingerprint (masked prefix +
> hash prefix) at the moment content enters an evidence pack. Detector name, file path and line
> number survive, so the finding stays actionable. The raw value never reaches the calling agent, a
> report, a log line, or an exception message.

**Out of scope**:
- The `security` dimension itself (T008) — that dimension *uses* redaction; this task provides it.
- Reporting or rendering (T013).
- Remediation advice about found secrets.

**Requirement Refs**:
- NFR-010: redact to a non-reversible fingerprint at the moment of entry; preserve detector name, path, line
- NFR-002: no invention
- FR-013: no verdict from the engine — redaction annotates, it does not judge severity
- NFR-011: first-write advisory (T013 renders it; this task supplies the signal that secrets were found)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] HITL gate above answered and recorded in `memory/decisions.md`
- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T001 — the redaction seam and its signature already exist as a documented passthrough; this task fills it.

**Entry point**: `redact`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `redact(text) -> RedactionResult` returns the redacted text plus a list of `RedactionHit` (detector name, offset, fingerprint) — the raw value appears on **no** returned field | NFR-010 |
| 2 | The fingerprint is non-reversible and matches the format decided at the HITL gate | NFR-010 |
| 3 | Redaction happens inside `run_dimension()` before an excerpt is placed on a pack — a test proves no code path constructs a pack from unredacted text | NFR-010, Critical Constraint 4 |
| 4 | Detector name, file path and line number are preserved on every hit | NFR-010 |
| 5 | **No raw value in any log record**: a test captures logging at DEBUG across a full run over a repo seeded with fake secrets and asserts none appears | NFR-010 |
| 6 | **No raw value in any exception message**: a test forces failures mid-pipeline on secret-bearing content and asserts no raw value appears in the traceback text | NFR-010 |
| 7 | The same raw value fingerprints consistently within a single run (so a reader can correlate occurrences), per the HITL decision | NFR-010 |
| 8 | Detectors cover at minimum: AWS access key IDs and secret keys, generic `api_key`/`token`/`secret`/`password` assignments, private key PEM blocks, JWTs, and high-entropy base64/hex strings above a threshold | NFR-010 |
| 9 | Redaction assigns no severity, score, or verdict — only detector name and location | FR-013 |
| 10 | A run that redacted at least one hit sets a flag on the pack so T013 can render the NFR-011 advisory | NFR-011 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Text containing `AKIAIOSFODNN7EXAMPLE` and a matching fake secret key | Both replaced by fingerprints; hits name the AWS detectors; neither raw value present anywhere in the result | automated test |
| 2 | A full pipeline run over a temp repo seeded with 10 distinct fake secrets, with logging at DEBUG | Zero raw values in the pack, in captured logs, and in stdout | automated test |
| 3 | Text with no secrets | Returned unchanged, zero hits, no false positives on ordinary prose or code | automated test |
| 4 | The same secret appearing 3 times in 2 files | 3 hits, identical fingerprint, correct per-occurrence locations | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t004_redact.py -q -p no:randomly
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T004.md`.
> This task's Evidence table is the audit artifact for NFR-010. The negative tests (AC #5, #6) must
> show pasted output, not a ticked box.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T004.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/pipeline.py` (T001) — the seam is already called from there with the final signature; do not change the call site's contract without Supervisor approval, since T002/T003/T005 are written against it.

Detectors are pattern + entropy rules in one module, expressed as data where possible so the list is
auditable at a glance. Redaction is applied to the *text*, not to a "sanitized copy" held alongside
the original — never keep the raw value in a field "just in case", because every such field is a
leak waiting for a future serializer to find it.

The three leak paths that actually bite are logs, exception messages, and truncation remainders.
Treat AC #5 and #6 as the real deliverable; the detector list is the easy half.

Entropy-based detection will produce false positives (hashes, UUIDs, minified code, base64 assets).
That is the correct trade for this project: a false positive costs a reader one confusing
fingerprint, a false negative costs a leaked credential. Tune toward over-redaction and say so in
the module docstring.

---

## Edge Case Checklist

- [ ] Secret spanning multiple lines (PEM blocks) → fully masked, not just the first line
- [ ] Secret at the exact boundary of a truncated excerpt → the *remainder* must not survive unredacted in the truncation metadata
- [ ] Overlapping detector matches on the same span → single hit, deterministic winner, no double-masking that corrupts offsets
- [ ] Offsets remain valid after replacement changes the string length (redact right-to-left, or build a new string — do not mutate in place with stale offsets)
- [ ] A secret inside a file path or a filename, not just file contents
- [ ] Non-UTF-8 bytes near a match
- [ ] Very long line containing a secret → bounded work, no catastrophic regex backtracking (**ReDoS** — every pattern must be checked for it; this module reads attacker-influenceable content)
- [ ] Empty string / whitespace-only input
- [ ] Fake secrets in this project's own test fixtures must not trip the tool into recursive confusion when it evaluates itself (this repo is the kit fixture)
- [ ] Example/placeholder values (`AKIAIOSFODNN7EXAMPLE`, `xxx`, `changeme`) — still redacted; the engine does not judge whether a secret is real (FR-013)
- [ ] `sources_missing` / error strings that echo file content

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/redact.py` | Replace the T001 passthrough with real detectors + fingerprinting |
| `src/easy_verifier/core/models.py` | Add `RedactionHit`, `RedactionResult`; add `redactions`/`had_redactions` to `EvidencePack` |
| `src/easy_verifier/core/pipeline.py` | Record hits on the pack; ensure no unredacted path exists |
| `tests/test_t004_redact.py` | New — including the log and exception negative tests |
| `memory/decisions.md` | **Supervisor writes** the HITL decision — not the agent |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `memory/**` | Supervisor-only writes (the DDR follow-up is the Supervisor's to record) |
| `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t004_redact.py`, in three layers:

1. **Unit** — each detector against positive and negative samples, table-driven.
2. **Property/format** — fingerprint is stable within a run, non-reversible, correctly formatted.
3. **Negative integration (the important layer)** — build a temp repo seeded with distinct fake
   secrets, run the full pipeline with `caplog` at DEBUG and captured stdout/stderr, and assert each
   raw value appears **zero** times across the pack JSON, the logs, and the output. Repeat with an
   injected failure to cover exception messages.

Fake secrets must be syntactically valid but non-functional. Use documented example values where
they exist (AWS publishes `AKIAIOSFODNN7EXAMPLE` for exactly this purpose).

The Supervisor signs off on this Test Plan as the oracle before spawn — High Risk, so the
implementing agent must not be the sole author of its own acceptance test.

---

## Completion Checklist

- [ ] HITL gate answered and recorded
- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (**High risk — mandatory**)
- [ ] `Skill({ skill: "blast-radius" })` run (sensitive data, High risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T004.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
