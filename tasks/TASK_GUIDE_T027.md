# TASK_GUIDE — T027: MCP detect gate — `needs_input.picks` candidates for unfilled roles
**Date**: 2026-09-26
**Complexity Level**: C2
**Risk Level**: Medium
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
7. Read `docs/ddr/0006-any-language-roles-and-agent-hard-gates.md` and `BRAINSTORMING_LOG_source-discovery.md`
8. Read the merged T026 code (`core/roles.py`, agent-input handling in `core/score.py`)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-26): "ask agent llm for hard gate to detect and evaluate … just use in some case that
we need LLM to think, not for all steps, so we can save a lot of token/cost". This task is the
**detect** half.

**Restated intent**:
> Over MCP only, when the rules leave a source role unfilled but the repository holds files that
> could fill it, `score` returns — alongside its normal result — a short, redacted candidate list
> per role so the calling agent can answer with `picks`. When nothing qualifies, nothing extra is
> returned and zero extra tokens are spent.

**Out of scope**:
- Gate evaluations, the ±10% band, blend, rating provenance (T028).
- Any CLI prompting — the CLI never emits `needs_input` (FR-034, FR-040).
- Any model call.

**Requirement Refs**:
- FR-035: detect gate, ≤20 candidates/role, path + first heading, redacted, one round, result never withheld
- FR-034: picks round-trip (consumes T026's picks input)
- FR-040 / NFR-001: engine makes no model call
- NFR-009: bounded payload; NFR-010: redaction of candidate text
- US-014

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, Stage 0.5 2026-09-26)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (hard gate, needs_input, picks, candidate)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria

---

## Dependencies & Reachability

**Depends on**: T026 — source roles, resolver, and `agent_input.picks` handling must exist

**Entry point**: `needs_input`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | MCP `score` without `agent_input`, on a fixture where role R is unfilled and ≥1 unmatched doc/config file exists, returns `needs_input.picks` listing R with candidates **and** the full normal ratings in the same response. | FR-035 |
| 2 | Each candidate is only `{path, heading}` — repo-relative path + first markdown heading or first non-empty line (≤200 chars) — passed through redaction; a fixture whose first line holds a fake credential shows the fingerprint, never the raw value. | FR-035, NFR-010 |
| 3 | At most 20 candidates per role, sorted deterministically; overflow is disclosed as a count (`omitted: N`), never silent. | FR-035, NFR-009 |
| 4 | Candidates exclude: files already filling any role, vendor/build dirs, secret-bearing files (DDR-0002), binary files. | FR-035, DDR-0002 |
| 5 | No `needs_input` key when every role is filled **or** no candidate exists. | FR-035 |
| 6 | A `score` call carrying `agent_input.picks` never emits `needs_input.picks` (one round). | FR-035 |
| 7 | CLI `score` never emits `needs_input`, with or without `--agent-input`; parity test excludes nothing new — `needs_input` is an MCP-only field documented as such, and the parity comparison covers it by comparing the MCP payload minus `needs_input` (declare this in the test, do **not** add it to DDR-0005 normalization; if that is not acceptable, STOP and report). | FR-034, FR-040, DDR-0005 |
| 8 | Round trip: agent picks returned from the candidate list, fed back via `agent_input`, raise that dimension's coverage and show provenance `rules + agent picks (N files)`. | FR-034, FR-039 |
| 9 | MCP tool description tells the calling agent, in ≤3 sentences, how to answer `needs_input.picks`. | US-014 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Fixture with `notes/product-brief.md` and no requirements-doc match | `needs_input.picks["requirements-doc"]` contains that path + its heading | automated test |
| 2 | Fully-resolved fixture | no `needs_input` key | automated test |
| 3 | 30 candidate files for one role | 20 listed, `omitted: 10` | automated test |
| 4 | Real MCP stdio session against the Docker image on `bryony` | `needs_input` present; second call with picks raises coverage | `verify` run, transcript pasted |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled in `tasks/TASK_REVIEW_T027.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T027.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/_doc_extract.py` — reuse `_ATX_HEADING` /
`_SETEXT_UNDERLINE` for the first heading; `src/easy_verifier/core/redact.py` public API for
redaction; `src/easy_verifier/adapters/mcp_server.py` `score` tool for the adapter-only flag.

New `core/gate.py` (pure functions, no state): `detect_pick_gates(resolution, repo) -> NeedsInput |
None`. Core returns it; only the MCP adapter includes it in the payload (core stays shared, FR-021).
Stateless: "round" is decided solely by whether `agent_input.picks` was supplied.

---

## Edge Case Checklist

- [ ] Candidate heading redacted before it leaves the engine
- [ ] Binary / oversized files never read for a heading (bound the read to the first few KB)
- [ ] Deterministic ordering; overflow count disclosed
- [ ] No candidates from `node_modules`, `target`, `dist`, `build`, `.venv`, `vendor`, `.git`
- [ ] Empty repo / repo with only filled roles → no `needs_input`
- [ ] Picks round suppresses `needs_input.picks`

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/gate.py` (new) | detect-gate candidate builder |
| `src/easy_verifier/core/score.py` | return `needs_input` data from core |
| `src/easy_verifier/adapters/mcp_server.py` | include `needs_input` in MCP `score` payload; tool description |
| `tests/…` | per AC |
| `docs/LOCAL_MCP_GUIDE.md`, `docs/DOCKER_MCP_GUIDE.md`, `README.md` | the two-call flow |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/adapters/cli.py` | CLI never emits `needs_input` |
| `src/easy_verifier/core/judge.py` | rating rules unchanged in this task |
| `core/redact.py`, `core/budget.py`, `Dockerfile`, `compose.yaml` | reuse only / hardening stays |

---

## Test Plan

Unit: candidate builder (filters, cap, ordering, redaction, heading extraction). Integration: MCP
`score` two-call round trip over stdio; CLI never emits the key; parity. Live: Docker image on
`bryony` via MCP stdio.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — repo text leaves the engine)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T027.md` (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] Supervisor notified: task ready for Stage 4 review
