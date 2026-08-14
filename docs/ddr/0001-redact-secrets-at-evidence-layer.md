# 0001. Redact detected secrets at the evidence layer

**Status**: Accepted
**Date**: 2026-08-14
**Deciders**: thunderkds (user), Supervisor
**Related**: NFR-010 · NFR-011 · FR-011 · FR-012 · security dimension tasks (Stage 2, TBD)

---

## Context

`easy-verifier-mcp` is a context-packer: its evaluation dimensions gather evidence from a target
repository and return it to a calling agent, which reasons and submits findings back to
`write_report`. Reports are rendered as HTML **into the evaluated repository** under `reports/`
(FR-017).

The security dimension (FR-012) scans the target repo for hardcoded credentials. Following the
default evidence contract (FR-011: "citable excerpts with file path and line references"), a hit on
`AWS_SECRET_KEY=AKIA…` in `config/prod.py` would travel as a raw excerpt through the evidence pack,
into the calling agent's context, into the submitted finding, and finally into a plaintext HTML file
written inside the scanned repository — a file very likely to be committed.

The verifier would therefore **create** a consolidated plaintext secrets inventory that did not
previously exist as a single document, and place it in the repository it was asked to protect. This
is a leak the tool manufactures rather than one it discovers.

A decision is needed now because the redaction boundary is part of the evidence-pack contract that
all seven dimensions are built against; choosing it after implementation means rewriting that
contract.

**Gate criteria** — all three apply (ADR-eligible; user elected DDR):
1. **Hard to reverse** — the evidence contract is a shared dependency of every dimension module.
2. **Surprising without context** — a future maintainer will reasonably ask why the reasoning agent
   is denied the value it is reasoning about.
3. **Genuine trade-off** — real alternatives existed, each with a defensible case.

---

## Decision

We will redact detected secret values to a non-reversible fingerprint **at the moment they enter an
evidence pack** — inside the engine, before any value crosses an adapter boundary.

- The fingerprint is a masked prefix plus a hash prefix (e.g. `AKIA****…3f2a`).
- The raw value must never be returned to the calling agent, written to a report, or written to a
  log.
- Detector name, file path, and line number are preserved so the finding remains actionable: the
  operator can open the file and see the value themselves.
- On first write to a target repo's `reports/`, the operator is advised that reports may contain
  sensitive findings and should be reviewed before committing (NFR-011).

---

## Alternatives Considered

| Alternative | Pros | Cons | Why not chosen |
|-------------|------|------|----------------|
| **Redact at the evidence layer** | Raw value never leaves the engine; no downstream path can leak it, including agent context, transcripts, and logs. Single enforcement point. | Agent cannot inspect the value to judge real-secret vs. test fixture. | **Selected** |
| Redact at report render | Agent sees raw values and reasons better about false positives; report output is equally clean. | Leak surface remains: the agent's context, the conversation transcript, any request log, and any other tool the agent subsequently calls. Enforcement sits at the last step instead of the first. | Rejected — moves the boundary to the point of least protection. The transcript is as durable as the report. |
| No redaction; warn and gitignore | Maximum fidelity for the reasoning agent. Simplest to implement. | Manufactures a plaintext secrets inventory inside the target repo. `.gitignore` is advisory and routinely overridden; a warning does not undo a committed file. | Rejected — incompatible with NFR-007's intent and indefensible for a tool positioned as a security reviewer. |

---

## Consequences

### Positive
- The engine cannot leak a credential it detected, by construction rather than by convention.
- Enforcement is a single choke point, testable in isolation.
- Consistent across both adapters (MCP and CLI) at no extra cost, preserving FR-022 parity.
- Strengthens the project's central claim: the engine only ever emits what it can justify.

### Negative (accepted trade-offs)
- The reasoning agent cannot distinguish a live credential from a test fixture, a documentation
  placeholder, or an already-rotated value. Some false positives will reach the report.
- Findings about secrets carry lower confidence than they otherwise would, and the operator must
  open the file to adjudicate.
- Fingerprints are not comparable across scans unless the hash is stable, which constrains the
  implementation.

### Follow-up
- [ ] Define the fingerprint format precisely (mask width, hash algorithm, hash prefix length) during
      Stage 2 task breakdown.
- [ ] Decide whether the hash is salted. Unsalted allows cross-scan correlation of the same secret;
      salted prevents dictionary attacks against low-entropy values. Trade-off to be resolved.
- [ ] Add a redaction unit test asserting no raw detected value appears in any pack, report, or log
      output — this is the Evidence-Gate proof for NFR-010.
- [ ] Consider a future `--reveal` escape hatch, explicitly opt-in and never default, if false
      positives prove unmanageable in practice.
