# PRD — easy-verifier-mcp
**Last updated**: 2026-08-14
**Status**: Approved
**Owner**: thunderkds (hungnh1110@gmail.com)

> **Scope of this document**: *What* to build and *why* — product intent, user stories, requirements, success metrics.
> Technical decisions, architecture, agent config, and task state live in `PROJECT_SPEC.md`.
> Source of intent: `REQUIREMENT.md` (high-level plan) + Phase 0 clarification session (2026-08-14).

---

## Overview

Developers and agentic supervisors need deep evaluation of code and features, but today's options
fail in opposite directions: static linters are shallow and see no intent, while asking an LLM to
"review this repo" produces confident judgments unfounded in any real artifact. Neither tells you
what it *did not know*.

`easy-verifier-mcp` closes that gap. It gathers real, citable evidence from a target repository —
kit artifacts when they exist, docs and code when they don't — hands that evidence to a reasoning
agent, and renders the agent's findings into a self-contained HTML report written back into the
evaluated repo. The engine itself never reasons and never invents: when context is missing it says
so, loudly, as a measurable coverage score. The result is an evaluation a developer can trust
*because it can be checked*.

---

## Personas

| ID | Name | Role | Pain Point |
|----|------|------|-----------|
| P1 | Kit Supervisor | The `personal-agentic-claude` Supervisor agent running Stage 4 review | Its review skills reason over whatever happens to be in context; it has no uniform, repeatable way to pull grounded evidence across all evaluation dimensions for a task or branch. |
| P2 | Standalone Developer | An engineer with an ordinary repo and an agent CLI, no kit artifacts | Wants a real review of a PR or working tree. Gets either shallow lint output or an LLM opinion with no evidence trail and no admission of what it couldn't see. |
| P3 | Reviewing Agent | Any LLM agent (Claude Code or another CLI) asked to evaluate a repo | Must decide what to read, from where, in what order. Wastes context on irrelevant files and silently fills gaps with plausible invention. |

---

## User Stories

| ID | Story | Persona |
|----|-------|---------|
| US-001 | As a Kit Supervisor, I want to call focused evaluation tools over MCP that read `PROJECT_SPEC.md`, `tasks/`, and `memory/` as ground truth, so my Stage 4 review is architecture-aware rather than guesswork. | P1 |
| US-002 | As a Standalone Developer, I want to point the verifier at any repo path from my agent CLI and get a useful review, so I am not blocked by the repo lacking kit artifacts. | P2 |
| US-003 | As a Standalone Developer, I want the report to state plainly what context was unavailable, so I can calibrate how much to trust each finding. | P2, P1 |
| US-004 | As a Reviewing Agent, I want evidence returned as structured, citable packs per dimension, so I reason over facts instead of deciding what to read. | P3 |
| US-005 | As a Reviewing Agent, I want my findings rejected when they carry no evidence reference or confidence value, so I cannot silently emit an unfounded claim. | P3 |
| US-006 | As either caller, I want to choose the evaluation scope — a single task, a PR/commit range/branch, the working tree, or the whole project — so the evaluation matches the question I am asking. | P1, P2 |
| US-007 | As a Kit Supervisor, I want security evaluation always present and expected on non-trivial changes, so security is never quietly skipped. | P1, P2 |
| US-008 | As either caller, I want a self-contained HTML report written into the evaluated repo under `reports/`, so the result is browsable and lives with the code it judges. | P1, P2 |
| US-009 | As a Standalone Developer, I want the same tool to work whether or not the repo was kit-built, so I learn one workflow. | P2 |
| US-010 | As either caller, I want one report that spans several dimensions and carries suggested improvements, so I get a synthesized evaluation rather than seven disconnected documents I have to reconcile myself. | P1, P2 |
| US-011 | As a Reviewing Agent, I want to discover which dimensions exist and what context each one seeks, so I can choose the right ones without reading the verifier's source. | P3 |
| US-012 | As either caller, I want to point the verifier at a repository or feature and get quality numbers back in one run, so I can gauge quality without first standing up a reasoning agent — and I want it to decline to give me a number rather than give me an unfounded one. | P1, P2 |

---

## Functional Requirements

Each FR must trace to at least one User Story.

### Context detection & loading

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-001 | The system must detect whether the target repository contains kit context by probing for `PROJECT_SPEC.md`, `PRD.md`, `PROJECT_KANBAN.md`, `tasks/TASK_GUIDE_*.md`, and `memory/`. | US-001, US-009 |
| FR-002 | When kit artifacts are present, the system must operate in **kit-aware mode** and load those artifacts as ground truth for architecture, solution-fit, and requirement-fidelity evidence. | US-001 |
| FR-003 | When kit artifacts are absent, the system must operate in **standalone mode**, scanning available documentation first (`README*`, `docs/`, ADRs, `CONTRIBUTING*`) and falling back to code only where docs are silent. | US-002, US-009 |
| FR-004 | In standalone mode, the system must emit an explicit limited-context warning in every tool response and in every rendered report. | US-003 |
| FR-005 | The system must never synthesize, infer, or substitute content for a context artifact it did not find. Absent context must be reported as absent. | US-003, US-005 |

### Scope selection

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-006 | The system must support four evaluation scopes: `task` (a single task/feature), `changes` (a PR, commit range, or branch diff), `worktree` (uncommitted working tree), and `project` (whole repository). | US-006 |
| FR-007 | For `task` scope in kit-aware mode, the system must resolve the named task to its `tasks/TASK_GUIDE_Txxx.md` and include its acceptance criteria in the evidence pack. | US-001, US-006 |
| FR-008 | For `changes` scope, the system must derive the changed-file set and diff from git without requiring a network remote. | US-006 |

### Evaluation dimensions

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-009 | The system must expose each evaluation dimension as a **separate** callable unit, not a single monolithic `evaluate` entry point. | US-004 |
| FR-010 | v1 must ship all seven dimensions: **architecture**, **solution-fit**, **requirement-fidelity**, **test-strategy**, **security**, **blast-radius**, and **code-quality**. | US-001, US-004 |
| FR-011 | Every dimension must return a structured evidence pack containing: the files and artifacts actually read, citable excerpts with file path and line references, and a list of context items sought but not found. | US-004, US-003 |
| FR-011a | Each evidence pack must respect a per-dimension byte budget, defaulting to 120 KB and overridable per call. Candidate content must be ordered by relevance to the active scope (changed files first, then spec-referenced files, then the remainder) so truncation drops the least-relevant tail. | US-004 |
| FR-011b | A truncated pack must report truncation explicitly as a structured field stating that truncation occurred and how many items were omitted. Silent truncation is prohibited, and omitted items must appear in the coverage list defined by FR-016a. | US-003, US-004 |
| FR-012 | The security dimension must be callable in both modes and in every scope, and must never be gated behind kit-aware mode. | US-007 |
| FR-013 | No dimension may return a verdict, score, or judgment the engine **inferred**. Dimensions return evidence only; semantic reasoning is performed by the calling agent. **Amended 2026-08-26 (DDR-0003)**: a *rating* computed by declared, inspectable rules over measured metrics is permitted, and must cite the metric values it was computed from. NFR-001 is untouched — the judge is arithmetic, never a model. | US-004, US-012 |
| FR-013a | The system must expose a **discovery** operation listing every available dimension with its human-readable purpose and its declared `sources_sought` list, available in both adapters. | US-011 |

### Findings, confidence & reporting

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-014 | The system must expose a `write_report` operation accepting the calling agent's findings as structured JSON, and must render them into a self-contained HTML report. | US-008 |
| FR-015 | Every finding must carry **both** an evidence reference and a confidence value. `write_report` must reject the submission if **either** is missing from **any** finding, returning a validation error naming the offending finding and the missing field. A finding with evidence but no confidence is rejected; so is a finding with confidence but no evidence. | US-005 |
| FR-015a | `write_report` must reject a finding whose evidence reference does not resolve to an item present in the evidence pack it cites — a dangling citation is an unfounded claim wearing a citation's clothes. | US-005 |
| FR-016 | Each dimension must declare, as static data, the list of context sources it seeks. The engine must compute a **context-coverage score** as the unweighted ratio `found / sought` over that declared list. All sources are equally weighted; the engine must apply no importance judgment. | US-003 |
| FR-016a | The coverage score must never be rendered alone. Every presentation of it — in a tool response and in a report — must be accompanied by the named list of sources sought but not found, so a reader can audit the number. | US-003 |
| FR-017 | Reports must be written into the **evaluated** repository under `reports/`, never into the verifier's own repository. | US-008 |
| FR-018 | Rendered HTML reports must be self-contained: no external CSS, JS, font, or image requests. | US-008 |
| FR-018a | A report must be able to span **multiple dimensions** in a single document. `write_report` accepts findings tagged by dimension and renders them grouped, alongside a combined summary and the per-dimension coverage scores. Seven separate single-dimension reports is not a conforming implementation. | US-008, US-010 |
| FR-018b | Report filenames must be unique and self-describing, incorporating scope and a UTC timestamp with sufficient resolution that two reports written in the same second cannot collide. Writing a report must never overwrite an existing one. | US-008 |

### Synthesis & suggestions

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-023 | Every finding must support an optional **suggested improvement** field. Where a finding carries one, the report must render it alongside the finding. | US-010 |
| FR-024 | Suggestions are advisory text only. The system must never apply, patch, or auto-fix anything in the target repository (reinforces NFR-007). | US-010 |
| FR-025 | The engine must provide a **combined pack** operation that runs several named dimensions in one call and returns their packs together with an aggregate coverage summary, so a caller can synthesize across dimensions without issuing seven separate calls and reassembling them by hand. | US-004, US-010 |
| FR-026 | Cross-dimension synthesis — deciding what the findings *mean together* — is performed by the calling agent, not the engine. The engine's contribution to synthesis is aggregation and presentation only, never interpretation (reinforces FR-013, NFR-001). | US-010 |

### Quality rating & assessment

| FR-027 | The engine must compute **metrics** — measured, citable facts about the target (test strength, security surface, evidence coverage, code shape) — exclusively from the evidence pack a dimension already produced. A metric may never read a file the pack did not cite, so that every number is auditable against the evidence beside it. | US-012 |
| FR-027a | Every metric must declare whether it is **whole-set-dependent** (ratios, densities, aggregate counts) or **evidence-local** (a detector hit, which is real regardless of what else was dropped). A whole-set-dependent metric computed over a truncated pack describes what survived the byte budget, not the repository, and must therefore abstain rather than report a value (DDR-0003). | US-003, US-012 |
| FR-028 | The engine must compute a per-dimension **rating** (0–100) from those metrics using rules declared as static, inspectable data. The rules must be readable without reading the engine's source, and a threshold change must be a value change rather than a code change. | US-012 |
| FR-028a | Each dimension must declare a **coverage floor**. Below it, the engine emits **no rating** for that dimension — it emits a structured abstention naming the floor, the achieved coverage, and the sources not reached. An abstention is a distinct state and must never be encoded as `0`, `None`, or a low rating: "we could not see this" must be indistinguishable from nothing except itself, and never mistakable for "this is bad" (FR-005, DDR-0003). | US-003, US-012 |
| FR-028b | An **overall** rating must average only the dimensions that rated, and must disclose in the same field how many of the seven contributed and which abstained, with each abstention's reason. An aggregate that does not state what bounded it is prohibited. Note that an abstaining dimension can *raise* the overall, which makes the disclosure load-bearing. | US-003, US-012 |
| FR-029 | When the calling agent submits findings, the engine must compute an **assessment** (0–100) per dimension as a severity- and confidence-weighted rollup of those findings. The engine performs the arithmetic; the judgment remains the agent's (FR-026). | US-010, US-012 |
| FR-029a | Where a rating and an assessment both exist for a dimension, the report and both adapters must render them **side by side** with their **divergence**, and must never blend, reconcile, or adjudicate between them. Disagreement between measured rules and an agent's judgment is signal to be surfaced, not an error to resolve. | US-010, US-012 |
| FR-030 | A rating must be obtainable from a **single invocation against a repository path**, with no findings submitted and no agent in the loop. The assessment layer enriches that output when findings are present; it is never a precondition for a number. | US-002, US-012 |

### Entry points

| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-019 | The system must expose an **MCP adapter** serving all dimensions, discovery, and `write_report` as MCP tools, registrable in Claude Code and the personal-agentic harness. The harness connects to it **locally, via a Docker container** — never over the internet. | US-001 |
| FR-019a | The default and required transport is **stdio**, spoken across the container boundary (`docker run -i`). This needs no port, no bind address, and no server lifecycle to manage. | US-001 |
| FR-019b | An HTTP/SSE transport may be offered as an opt-in flag for harness convenience. When enabled it must bind to the loopback interface (`127.0.0.1`) only, and must never bind `0.0.0.0` or any routable address, including inside a container. | US-001 |
| FR-020 | The system must expose a **CLI adapter** that runs the same dimensions against a repository given by filesystem path, with no server process required. | US-002 |
| FR-021 | Both adapters must delegate to one shared core; neither may contain evaluation, context-loading, or rendering logic of its own. | US-009 |
| FR-021a | The MCP adapter must ship a Dockerfile and compose configuration in v1, with all configuration supplied via environment variables and no host-absolute paths. The target repository must be mountable as a volume, and the container must speak stdio by default so no port need be published. | US-001, US-002 |
| FR-021c | Paths inside the container must never leak into written reports. A report generated for a repo mounted at `/workspace` must reference the paths the operator recognises on the host, not container-internal ones. | US-008, US-009 |
| FR-021b | The CLI adapter must remain runnable with no container and no server process, so Case B works from a plain checkout. | US-002 |
| FR-022 | Both adapters must produce identical evidence packs and identical report output for the same repository, scope, and dimension. | US-009 |

---

## Non-Functional Requirements

| ID | Requirement | Category |
|----|-------------|----------|
| NFR-001 | The engine must contain no LLM call and must require no model API key to operate in either mode. All reasoning originates from the calling agent. | Architecture |
| NFR-002 | The engine must never invent missing context; every claim it emits must be traceable to a file it actually read. | Integrity |
| NFR-003 | Security evaluation must be available in every mode and scope, and expected on any non-trivial change set. | Security |
| NFR-004 | Low-confidence and unevidenced claims must be structurally impossible to publish: enforcement lives in `write_report` validation, not in caller convention. | Integrity |
| NFR-005 | The system must operate on arbitrary repositories with no prior setup, configuration file, or kit installation in the target. | Usability |
| NFR-006 | The system must follow `easy-ui-mcp` operational style: a local MCP server with Docker packaging. Transport is stdio by default (FR-019a); HTTP/SSE is optional and loopback-bound (FR-019b). | Consistency |
| NFR-012 | The system is **local-only**. It must operate fully with no internet access, must make no outbound network request of its own, and must expose no listening socket reachable from outside the host. The harness reaches it through a local Docker container. | Security |
| NFR-013 | The container must run as a non-root user, mount the target repository read-only except for its `reports/` directory, and require no elevated capabilities. A tool that reads arbitrary source trees and scans them for credentials must hold the least privilege that still does the job. | Security |
| NFR-007 | The system must never write to the target repository outside `reports/`, and must never execute code from the target repository. | Safety |
| NFR-008 | Python + `mcp` SDK (FastMCP) is the mandated runtime. | Platform |
| NFR-009 | Evidence packs must be bounded in size so a whole-project evaluation does not exhaust the calling agent's context; truncation must be explicit and reported, never silent. | Performance |
| NFR-010 | Detected secret values must be redacted to a non-reversible fingerprint (masked prefix + hash prefix) at the moment they enter an evidence pack. The raw value must never be returned to the calling agent, written to a report, or written to a log. Detector name, file path, and line number must be preserved so the finding remains actionable. | Security |
| NFR-011 | On first write to a target repository's `reports/` directory, the system must advise the operator that reports may contain sensitive findings and should be reviewed before committing. | Security |

---

## Success Metrics / KPIs

| Metric | Baseline | Target | How measured |
|--------|----------|--------|--------------|
| Dimensions available as separate tools | 0 | 7 | MCP tool listing + CLI subcommand listing |
| Modes producing a usable report | 0 | 2 (kit-aware, standalone) | Integration test against one kit repo and one plain repo |
| Entry points producing identical output | 0 | 2 (MCP, CLI) | Parity test asserting byte-equal evidence pack for same input |
| Unevidenced findings reaching a report | n/a | 0 | `write_report` validation test suite |
| Limited-context warning present in standalone reports | n/a | 100% | Assertion in standalone-mode integration test |
| Reports requiring a network fetch to render | n/a | 0 | Static scan of rendered HTML for external URLs |

---

## Out of Scope

Explicitly excluded from v1:

- Replacing the kit's own Stage 4 skills. This project **augments** them and is callable **by** them.
- Any model training, fine-tuning, or evaluation-model hosting.
- Automatic fixing or patching of identified issues. Suggestions only.
- Any LLM inference inside the engine, including an "optional LLM layer" behind an env var.
- Fetching or reading the `personal-agentic-claude` and `easy-ui-mcp` repositories over the network for v1 design.
- Non-HTML report formats (JSON export of findings is an internal contract, not a deliverable format).
- Multi-repository or organization-wide evaluation. One target repo per invocation.
- Remote, hosted, or multi-tenant operation. The server is local-only, reached through a local
  Docker container, and is never exposed to the internet (NFR-012).
- Authentication, authorization, or multi-user access control — out of scope precisely *because*
  the server is local and single-user. If remote operation is ever added, this exclusion must be
  revisited first: an unauthenticated endpoint that reads arbitrary repositories would be a
  serious exposure.

---

## Open Questions / Assumptions

Resolved during Stage 0.5 requirement grilling (2026-08-14).

| # | Question / Assumption | Status | Owner |
|---|----------------------|--------|-------|
| 1 | Two-step report flow (pack → agent reasons → `write_report`) is the intended contract. | **Confirmed** by user, Phase 0. | thunderkds |
| 2 | `easy-ui-mcp` conventions (layout, Docker setup, transport config, report handling) are approximated from `REQUIREMENT.md` §4, not verified against source. | **Accepted risk** — user chose no network fetch. Revisit if drift becomes costly; resolvable by reading a local checkout. | thunderkds |
| 3 | Docker packaging in v1 scope. | **Confirmed in v1** by user (G3), overriding the supervisor recommendation to defer. See FR-021a. | thunderkds |
| 4 | Evidence-pack size ceiling. | **Resolved** (G4): per-dimension 120 KB default, relevance-ordered, explicit truncation. See FR-011a/FR-011b. | thunderkds |
| 5 | CLI `write_report` input shape. | **Resolved** (G5): `--findings <path>`, or stdin JSON when the flag is omitted. Both call the identical core path, preserving FR-022 parity. | Supervisor |
| 6 | Authenticated CLIs. | **Confirmed**: Claude Code only; all sub-agents spawn via the in-session `Agent` tool. | thunderkds |
| 7 | Secret values reaching evidence packs and reports. | **Resolved** (G1): redact at the evidence layer to a non-reversible fingerprint. See NFR-010/NFR-011. | thunderkds |
| 8 | Context-coverage score definition. | **Resolved** (G2): unweighted `found / sought` over a declared per-dimension checklist, never rendered without the miss list. See FR-016/FR-016a. | thunderkds |

Added during the Stage 2 pre-flight gap audit (2026-08-14).

| # | Gap found | Status | Owner |
|---|---|--------|-------|
| 9 | **FR-015 was ambiguous** — "lacks both an evidence reference and a confidence value" parses as reject-if-both-missing *or* reject-if-either-missing. The loose reading silently defeats NFR-004. | **Resolved** (G6): both fields are mandatory; rejection triggers if *either* is missing. Dangling citations rejected too (FR-015a). | Supervisor |
| 10 | **Synthesis + suggestion layer was missing entirely** — named in `REQUIREMENT.md` §4's five internal layers and implied by §1 ("improved suggestions") and the "suggestions only" exclusion, but absent from the PRD and the layer map. | **Resolved** (G7): FR-023…FR-026 added, plus US-010. Engine aggregates and presents; the caller interprets. | Supervisor |
| 11 | **Report scope undefined** — FR-014 never said whether a report covers one dimension or several, so seven disconnected reports was a conforming implementation. | **Resolved** (G8): FR-018a requires multi-dimension reports; FR-018b requires collision-proof filenames. | Supervisor |
| 12 | **No dimension discovery** — a caller had no way to learn what dimensions exist or what context each seeks without reading the source. | **Resolved** (G9): FR-013a, US-011. | Supervisor |
| 13 | **Transport mismatch** — HTTP/SSE was mandated by inheritance from `easy-ui-mcp`, but the engine is stateless and the harness connects locally via Docker. An unauthenticated local port that reads arbitrary repos is exposure bought for no benefit. | **Resolved** (G11) by user correction: harness connects **locally via Docker container, never the internet**. stdio is the default and required transport (FR-019a); HTTP/SSE is opt-in and loopback-bound (FR-019b). Added NFR-012 (local-only), NFR-013 (least-privilege container), FR-021c (no container-path leakage). | thunderkds |
| 14 | **Open**: whether the redaction fingerprint hash is salted. Unsalted allows correlating the same secret across scans; salted resists dictionary attacks on low-entropy values. | Open — must be closed when the redaction task is planned. DDR-0001 follow-up. | thunderkds |
| 15 | **Open**: FR-022 says adapters produce "identical" output, and the KPI table says "byte-equal". Timestamps and absolute paths differ between host and container runs, so byte-equality needs a defined normalization or a weaker, precise word. | Open — resolve when the parity test is specified. | Supervisor |
