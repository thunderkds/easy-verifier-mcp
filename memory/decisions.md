# decisions.md — Architectural Decisions (the "why")

> Cold-tier memory. Supervisor-only writes. Indexed from `memory/MEMORY.md`.

---

## 2026-08-14 — Context-packer architecture: no LLM inside the engine

**Decision**: `easy-verifier-mcp` performs no model inference. Evaluation dimensions gather and
structure evidence; all reasoning is performed by the calling agent. In MCP mode the caller is the
main agent; in path/CLI mode the caller is the user's agent CLI.

**Why**: Removes API-key requirement and cost from the engine, and removes the engine as a
hallucination source entirely — it can only report what it actually read. Directly serves
`REQUIREMENT.md` NFR "must never invent missing context".

**Trade-off accepted**: the engine cannot produce a report unaided; a caller is always required.

---

## 2026-08-14 — Two adapters, one core

**Decision**: Two entry points over one shared core library — `mcp_server.py` (FastMCP, HTTP/SSE)
and `cli.py` (target repo by filesystem path). Adapters are thin and hold no evaluation,
context-loading, or rendering logic. Both must produce identical output for identical input.

**Why**: The two real usage cases are an agent calling the MCP, and a single agent running the
verifier directly against a repo path. Case B must work with no server process running, which is
what "works on any repository" requires.

---

## 2026-08-14 — Two-step report flow

**Decision**: Evidence packs are returned to the caller; the caller reasons; the caller submits
findings as structured JSON to `write_report`, which validates and renders the HTML into the target
repo's `reports/`.

**Why**: The only shape that keeps the engine free of reasoning (see above) while still producing a
report containing actual judgments, as `REQUIREMENT.md` §5 requires.

---

## 2026-08-14 — Redact secrets at the evidence layer, not the report layer

**Decision**: Detected secret values are replaced with a non-reversible fingerprint (masked prefix +
hash prefix) at the moment they enter an evidence pack. The raw value never reaches the calling
agent, a report, or a log. Detector name, file path, and line number are preserved.

**Why**: The security dimension greps a target repo for secrets and the result is rendered into an
HTML file written **inside that same repo** — likely to be committed. Without redaction the verifier
would materialize a plaintext secrets inventory that did not previously exist as a single document.
Redacting at the report layer alone still leaks through the agent's context and any transcript.

**Trade-off accepted**: the agent cannot inspect the raw value to judge whether a hit is a real
secret or a test fixture, so some false positives will survive to the report.

**DDR gate**: 3/3 (hard to reverse, surprising without context, genuine trade-off) — ADR-eligible;
user elected the lighter DDR tier. → see DDR-0001
(`docs/ddr/0001-redact-secrets-at-evidence-layer.md`)

---

## 2026-08-14 — Context-coverage score is an auditable checklist ratio

**Decision**: Each dimension declares the context sources it seeks as static data. Coverage =
unweighted `found / sought`. The score may never be rendered without the accompanying named list of
sources sought but not found.

**Why**: A bare percentage is exactly the unfounded precision this project exists to prevent — "62%"
invites trust it cannot justify. Unweighted keeps the engine free of importance judgments, which
would be opinions smuggled into a component defined as opinion-free.

---

## 2026-08-14 — Docker in v1 (user override)

**Decision**: Dockerfile + compose ship in the v1 milestone; target repo mounted as a volume, all
config via environment variables. The CLI adapter remains runnable with no container.

**Why**: User decision, overriding the Supervisor recommendation to defer to v1.1. Matches
`easy-ui-mcp` operational style from day one.

---

## 2026-08-14 — Dimension structure: pipeline function + descriptors (Option D)

**Decision**: One module-level `run_dimension(spec, repo, scope, budget)` owns the whole pipeline
(context → collect → redact → budget → coverage → pack). Each dimension supplies a `sources_sought`
data list plus a single `collect` callable. No base class, no registry, no decorators; `DIMENSIONS`
is an explicit dict. `collect` returns `Iterable[Excerpt]` and `budget()` consumes it lazily.

**Why**: The discriminator was NFR-010 enforcement, not elegance. Flat modules (Option C) make
redaction a convention an implementer can omit — the exact silent failure DDR-0001 forbids. A plugin
registry (Option B) enforces it but pays inheritance ceremony for extensibility nobody requested.
Pure declarative specs (Option A) cannot express blast-radius graph traversal or test-strategy
coverage parsing, and would grow an escape hatch and converge on D anyway. D puts every cross-cutting
rule in one unreachable-around place while leaving `collect` an ordinary function.

**Trade-off accepted**: one layer of indirection over flat modules; the redaction boundary needs its
own dedicated choke-point test.

**Also decided**: `collect` is lazily iterable from day one, because a monorepo large enough to need
budgeting is exactly the one where materialising all excerpts first exhausts memory.

**Migration note**: D→B is mechanical if third-party dimensions ever become a requirement.

→ see `BRAINSTORMING_LOG.md`

---

## 2026-08-14 — Shared extraction helper for document-shaped dimensions only

**Decision**: architecture, solution-fit, requirement-fidelity and code-quality share one
parameterised artifact-extraction helper driven by their `sources_sought` declarations. security,
test-strategy and blast-radius keep bespoke `collect` implementations.

**Why**: 50% Rule outcome. The four document-shaped dimensions genuinely are "locate artifacts,
extract excerpts" and compress well. The other three carry irreducible logic (entropy scanning,
coverage-report parsing, dependency-graph traversal); forcing them into a shared helper is Option A's
mistake. Real reduction is ~25–30%, not 50% — claiming 50% would mean pretending the analytical
dimensions are simpler than they are.

---

## 2026-08-14 — Local-only, stdio-first transport (user correction)

**Decision**: The harness connects to this MCP **locally, through a Docker container — never over
the internet**. stdio is the default and required transport, spoken across the container boundary
via `docker run -i`. HTTP/SSE is optional, opt-in, and must bind `127.0.0.1` only.

**Why**: The spec had inherited "HTTP/SSE" from `easy-ui-mcp`'s operational style without anyone
asking whether this project needs it. It does not. The engine is stateless — every call re-reads the
target repo from disk — so there is no warm cache or session that a long-running server would
protect, and a fresh process per call costs nothing. Against that, a network transport buys a port
to collide, a lifecycle to manage, and an unauthenticated local socket that reads arbitrary source
trees and returns file contents. `docker run -i` handles the container boundary fine, so Docker was
never a reason to need HTTP either.

**Consequences**: NFR-012 (local-only, no outbound requests, no externally reachable socket),
NFR-013 (non-root container, target repo mounted read-only except `reports/`), FR-021c (container
paths must not leak into reports). Authentication is out of scope *because* of locality — an
exclusion that must be revisited first if remote operation is ever added.

**Corrects**: the original `REQUIREMENT.md` line 33 reading, which the PRD had carried forward
unexamined.

---

## 2026-08-14 — Synthesis is aggregation in the engine, interpretation in the caller

**Decision**: The engine provides a combined-pack operation (run several dimensions in one call,
return an aggregate coverage summary) and renders multi-dimension reports with optional suggested
improvements per finding. Deciding what findings *mean together* remains the caller's work.

**Why**: `REQUIREMENT.md` §4 lists a "synthesis + suggestion layer" among the five internal layers,
and §1 asks for "improved suggestions" — but the PRD and the layer map had dropped it entirely.
Recovering it must not smuggle reasoning into an engine defined as reasoning-free, so the split is:
aggregation and presentation are mechanical and belong to the engine; interpretation is judgment and
belongs to the caller.

---

## 2026-08-14 — Evidence packs bounded by relevance-ordered byte budget

**Decision**: 120 KB default per dimension pack, overridable per call. Content ordered changed-files
→ spec-referenced → remainder, so truncation drops the least-relevant tail. Truncation is reported
as an explicit structured field and feeds the coverage miss-list.

**Why**: Byte-measured rather than token-measured keeps output deterministic and model-independent,
preserving the two-adapter parity guarantee; a tokenizer would make packs model-specific.
