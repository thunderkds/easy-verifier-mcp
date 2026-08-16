# PROJECT_SPEC.md
**Last updated**: 2026-08-15
**Version**: 1.0

> **Scope of this document**: *How* to build it safely — architecture, agent config, constraints, risk areas, task state, and accumulated learnings.
> Product intent (personas, user stories, FR/NFR, success metrics) lives in `PRD.md`.
> If Critical Constraints here conflict with Out of Scope in `PRD.md`, resolve before Stage 2.

---

## Project Identity

- **Name**: easy-verifier-mcp
- **Repo**: `/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp` (GitHub: `thunderkds/easy-verifier-mcp`)
- **Primary tech**: Python 3.11+ · `mcp` SDK (FastMCP) · Jinja-free self-contained HTML rendering
- **Type**: MCP server + CLI (dual adapter over one shared core). No UI, no web frontend.
- **Deployment target**: Local Docker container, stdio transport, reached by the operator's agent harness. Never internet-exposed (NFR-012).
- **Key stakeholders**: thunderkds (owner / sole operator)

---

## Architecture Summary

`easy-verifier-mcp` is a **context packer**, not a reviewer. It gathers citable evidence from a
target repository and hands it to a calling LLM agent; the engine itself performs **no inference**
(NFR-001) and **never invents** absent context (FR-005, NFR-002). Two thin adapters — an MCP server
(`adapters/mcp_server.py`) and a path-mode CLI (`adapters/cli.py`) — delegate to a single core and
must produce identical output for identical input (FR-021, FR-022).

The core is built on **Option D** (see `BRAINSTORMING_LOG.md`): one `run_dimension()` pipeline
function owns every cross-cutting rule — redaction, relevance ordering, byte budgeting, truncation
reporting, and coverage scoring — and each of the seven dimensions supplies only static
`sources_sought` data plus a `collect` callable. There is no base class and no registry: the
cross-cutting rules are unbypassable because a dimension never gets the chance to bypass them.

Reporting is a **two-step flow**: the caller requests evidence packs, reasons over them itself, then
submits structured findings to `write_report`, which validates every finding (evidence reference +
confidence, both mandatory, citations must resolve) and renders a self-contained multi-dimension
HTML report into the *evaluated* repo's `reports/` directory.

### Layer map

```
src/easy_verifier/
  adapters/mcp_server.py    FastMCP, stdio default              FR-019, 019a/b
  adapters/cli.py           path mode, no server                FR-020, 021b
  core/pipeline.py          run_dimension() — the choke point   Option D
  core/context.py           kit detection, kit-aware|standalone FR-001..005
  core/scope.py             task|changes|worktree|project       FR-006..008
  core/redact.py            evidence-layer fingerprinting       NFR-010, DDR-0001
  core/budget.py            relevance order, lazy truncation    FR-011a/b
  core/findings.py          schema + write_report validation    FR-015, 015a
  core/synthesis.py         combined pack, aggregate coverage   FR-025, 026
  core/report.py            self-contained multi-dim HTML       FR-014, 017, 018, 018a/b
  dimensions/*.py           seven descriptors                   FR-010
```

---

## Domain Glossary

| Term | Meaning |
|---|---|
| **Evidence pack** | The structured return value of one dimension: files actually read, citable excerpts with path + line refs, `sources_sought` misses, coverage score, truncation field. Contains no verdict. |
| **Dimension** | One evaluation axis (7 in v1). Implemented as static descriptor data + a `collect` callable, executed by `run_dimension()`. Never a class, never registered. |
| **Coverage score** | Unweighted `found / sought` over a dimension's declared source checklist. Never rendered without the named miss list (FR-016a). |
| **Kit-aware mode** | Target repo contains kit artifacts (`PROJECT_SPEC.md`, `PRD.md`, `PROJECT_KANBAN.md`, `tasks/`, `memory/`); these are loaded as ground truth. |
| **Standalone mode** | No kit artifacts. Docs first (`README*`, `docs/`, ADRs, `CONTRIBUTING*`), code only where docs are silent. Emits a limited-context warning everywhere. |
| **Scope** | One of `task`, `changes`, `worktree`, `project` — what slice of the repo is under evaluation. |
| **Finding** | A caller-produced claim. Must carry an evidence reference *and* a confidence value; may carry an optional suggested improvement. |
| **Fingerprint** | The non-reversible replacement for a detected secret: masked prefix + hash prefix. Applied at the evidence layer, before anything leaves the engine. |
| **Excerpt** | A single citable unit: file path, line range, text. `collect` yields these lazily as `Iterable[Excerpt]`. |

---

## Critical Constraints

1. **No LLM inference in the engine, ever.** No model call, no API key, not behind an env var (NFR-001, out-of-scope list). Any task introducing one is rejected at review.
2. **No invention.** Absent context is reported as absent (FR-005). A dimension may never substitute a plausible value.
3. **`collect` returns `Iterable[Excerpt]`, consumed lazily by `budget()`.** Non-negotiable — returning a `list` forces full materialisation on exactly the monorepo size that most needs budgeting.
4. **Redaction happens inside `run_dimension()`, at the evidence layer** (NFR-010, DDR-0001). A raw detected secret must never reach a pack, a report, a log, or an error message. Bypassing `run_dimension()` to build a pack is prohibited.
4a. **Never read the contents of a secret-bearing file** (DDR-0002) — `.env*`, `*.pem`, `*.key`, `id_rsa`, `.netrc`, `.pgpass`, `credentials`, `.npmrc`, `secrets.*` and the rest of the DDR's list. Enforced in `RepoContext.read_source()` so no dimension can bypass it.
   Existence is still reported as `excluded: secret-bearing` — distinct from `not found` and `not examined`; only the bytes are withheld. T008 alone may request such contents, via an operator HITL approval defaulting to refuse.
   **Complements constraint 4, does not replace it**: secrets also appear in files we cannot refuse to read, so exclusion shrinks the intake and redaction covers the residue.
5. **Write nothing outside the target repo's `reports/`.** Never execute code from the target repo (NFR-007).
6. **stdio is the default and required transport** (FR-019a). HTTP/SSE is opt-in and must bind `127.0.0.1` only — never `0.0.0.0`, including inside a container (FR-019b, NFR-012).
7. **Adapters stay thin.** No evaluation, context-loading, or rendering logic in `adapters/` (FR-021).
8. **Shared extraction helper serves the four document-shaped dimensions only.** `security`, `test-strategy` and `blast-radius` stay bespoke — forcing them into the helper is the mistake that sank Option A.
9. **Reports are self-contained** — zero external CSS/JS/font/image requests (FR-018) — and must never leak container-internal paths (FR-021c).
10. **`.claude/hooks/**` is must-not-touch** without explicit user approval.
11. **There is no UI.** Every task deletes the UI/Design AC section from its TASK_GUIDE and marks all three UI Evidence rows ☐ N/A (Hard-Stop Gate 6).

---

## Known Risk Areas

| Area | Risk Level | Reason | Files |
|------|-----------|--------|-------|
| Secret redaction | **High** | A single leak path (log line, exception message, untruncated excerpt) defeats NFR-010 outright and is invisible until it has already happened. Fingerprint salting is still an open question (#14). | `core/redact.py`, `core/pipeline.py` |
| Pipeline contract (`run_dimension`) | **Med** | It is the choke point: every cross-cutting guarantee lives here, and all seven dimensions are written against its signature. Changing it after Wave 2 starts is a broad rewrite. | `core/pipeline.py` |
| Budgeting + lazy consumption | **Med** | Accidental materialisation of the `collect` iterable silently reintroduces the memory blow-up the design exists to prevent, and passes every functional test. | `core/budget.py` |
| Adapter parity (FR-022) | **Med** | "Identical" vs. "byte-equal" is unresolved (#15); timestamps and host-vs-container paths differ by construction. | `adapters/*.py`, parity test |
| Container hardening | **Med** | Non-root, read-only mount except `reports/`, no elevated caps (NFR-013), on a tool that scans arbitrary trees for credentials. | `Dockerfile`, `compose.yaml` |
| `write_report` validation | **Med** | It is the *only* thing standing between an unevidenced claim and a published report (NFR-004). Validation lives here, not in caller convention. | `core/findings.py` |

---

## Sub-Agent Team

Base team, unchanged — no supplemental role is needed (this is a pure backend/infra project, so
Frontend-Implementer is inactive for the whole v1 milestone).

| Agent | Role | CLI Spawn Command |
|---|---|---|
| Common-Infrastructure-Agent | Scaffold, `pyproject.toml`, worktrees, Docker/compose, shared config | `Agent({ subagent_type: "common-infrastructure", prompt: "..." })` |
| Backend-Implementer | Core pipeline, dimensions, adapters, reporting | `Agent({ subagent_type: "backend-developer", prompt: "..." })` |
| Frontend-Implementer | **Inactive** — no UI in v1 | — |
| QA-Automation-Agent | Two-mode integration, parity test, NFR-010 redaction proof, smoke suite | `Agent({ subagent_type: "qa-expert", prompt: "..." })` |

---

## Tasks

Authoritative task state lives in `PROJECT_KANBAN.md`. This table is the planning snapshot.

| ID | Title | Status | Assigned Agent | Complexity | Risk | Priority |
|----|-------|--------|---------------|-----------|------|----------|
| — | Generated at Stage 2 Step 2 (`to-issues`) | — | — | — | — | — |

---

## Memory / Insights

Running log of key decisions, patterns, and lessons learned across tasks.

| Date | Insight | Source Task |
|------|---------|------------|
| 2026-08-14 | Engine performs no inference; it is a context packer. All reasoning belongs to the caller. | Phase 0 |
| 2026-08-14 | Option D chosen over a base class / registry: cross-cutting rules are unbypassable when dimensions never own the pipeline. | Stage 0.5 |
| 2026-08-14 | Transport corrected to stdio-first after user flagged the inherited HTTP/SSE assumption — a local unauthenticated port that reads arbitrary repos is exposure bought for no benefit. | Stage 0.5 |
| 2026-08-14 | Test fixtures are free: this repo is the kit-aware fixture, any installed pip package is the standalone fixture. No synthetic fixtures needed. | Stage 1 |
