# BRAINSTORMING_LOG.md — Source discovery & agent hard gates
**Generated**: 2026-09-26
**Task / Context**: DDR-0006 · PRD FR-031…FR-040 · candidate tasks T026/T027 (IDs final at Stage 2)
**Skill**: `Skill({ skill: "brainstorming" })` — **Tier: Standard** (requirements locked in Stage 0.5;
only the implementation shape is open)

---

## The Problem Space

v0.1.0 abstained on 2–5 of 7 dimensions for kitchd (pnpm monorepo), bryony and ai-training because
each dimension's `SOURCES_SOUGHT` is a tuple of exact filenames
(`src/easy_verifier/dimensions/code_quality.py:36` — `CONTRIBUTING.md`, `ruff.toml`, `.flake8`, …),
and `pipeline.py:95` clamps "found" to that exact list. Requirements now demand:

- coverage over **roles**, any language (FR-016 amended, FR-031, FR-032);
- additive `.easy-verifier.toml` (FR-033);
- replayable **agent input** (picks + gate evaluations) in both adapters (FR-034, FR-022 amended);
- MCP-only `needs_input` for detect and evaluate gates, ±10% band, one round each (FR-035, FR-036);
- validated gate evaluations, capped blend `w = 0.5·c`, provenance + disclosure (FR-037…FR-039);
- engine never calls a model (FR-040 / NFR-001).

Non-negotiable constraints verified in code:
- Project convention "static descriptor data plus one `collect` generator … No base class, no
  registry, no subclassing" (`dimensions/code_quality.py:3-5`).
- `collect` must stay lazy — `DimensionDescriptor.collect` docstring (`core/models.py:106-111`).
- Walks already skip vendor dirs (`core/context.py:120` `_EXCLUDED_DIRS`, includes `node_modules`)
  and `context.read_sources(pattern)` already expands globs (`core/context.py:340`).
- Floors/abstentions live in `core/judge.py` (`below_coverage_floor`, `:311`); score orchestration in
  `core/score.py` (`score_repository`, `:56`); MCP `score` tool at `adapters/mcp_server.py:96-101`.

---

## Questions for the User

1. Which path (A recommended)?
2. Split the agent work into two tasks — **detect** (picks round) and **evaluate** (gate round +
   blend) — so each stays ≤C3? (Recommended: yes → T026, T027, T028.)

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | Roles-as-data in place | Add `roles` data to each descriptor; one `core/roles.py` resolver (generic + ecosystem pattern tables + TOML); one stateless `core/gate.py` (needs_input, validation, blend) | Medium | ~800 src + tests | Medium | ✅ Yes |
| B | Pluggable discovery engine | Ecosystem profile classes + registry, a separate resolution stage producing a SourceMap, gate as a session state machine | High | ~1,600 src + tests | High | |
| C | Minimal glob widening | Keep string tuples, turn entries into `role:glob|glob` strings, inline all patterns, blend in `score.py` only | Low | ~350 src + tests | Medium | |

### Option A — Roles-as-data in place
**Approach**:
- `SourceRole(name, patterns)` frozen dataclass; `DimensionDescriptor.roles`. `sources_sought`
  stays, **derived** as the tuple of role names → field names, discovery output shape and FR-016a
  miss list keep working.
- `core/roles.py`: `GENERIC_PATTERNS` (language-agnostic table), `ECOSYSTEM_PATTERNS` (Python, JS/TS,
  Rust, Java — plain dicts keyed by role, activated by manifest detection), `load_repo_config()` via
  stdlib `tomllib` (add-only, unknown keys → `ValidationError`), `resolve(repo) → {role: files}`
  — sorted, deterministic, reusing the `_EXCLUDED_DIRS` walk.
- Pipeline counts a role found if ≥1 resolved file was read; coverage = roles found / roles declared.
- `core/gate.py` (pure functions, no state): `detect_gates(packs, rating)` → `needs_input`;
  `validate_agent_input(doc, packs, gates)`; `blend(R, A, c)` using `Decimal` round-half-up.
- `score_repository(..., agent_input=None)`; MCP `score(agent_input=...)`; CLI `--agent-input PATH`.
  Only MCP attaches `needs_input` (flag passed by adapter; core stays shared per FR-021).
- Report: provenance line + blend parts next to each rating; overall disclosure gains
  rule-rated / blended / agent-rated / abstained counts.
**Pros**: Matches the no-registry convention; data-only extensibility (new ecosystem = new dict);
stateless rounds (agent input carries everything) → FR-022 replay is trivial; small surface.
**Cons**: Touches every dimension descriptor and the coverage math — every existing coverage
snapshot changes once.
**Why it might fail**: bespoke dimensions (`security`, `test_strategy`, `blast_radius`) read sources
in their own loops (`security.py:187` `PSEUDO_SOURCES`, `test_strategy.py:331`); if roles are wired
only into `_doc_extract`, those three silently keep exact-name behavior. Mitigation: T026 AC must
assert role coverage for all seven, with a non-Python fixture repo.

### Option B — Pluggable discovery engine
**Approach**: `EcosystemProfile` base class + registry, auto-discovered; `Resolver` stage builds a
`SourceMap` injected into `DimensionContext`; gate as a server-side session with round IDs.
**Pros**: Most extensible; clean separation of discovery from collection.
**Cons**: Violates the project's explicit "no base class, no registry" rule; server-side session
state breaks statelessness and complicates FR-022 replay; double the code.
**Why it might fail**: Session state across MCP calls in a `--rm` container that exits per session
is fragile; the registry is exactly the abstraction the Option A post-mortem (`_doc_extract.py:6-9`)
warns against.

### Option C — Minimal glob widening
**Approach**: Rewrite each `SOURCES_SOUGHT` entry as `"lockfile: *.lock|*-lock.*|…"`; parse in
pipeline; skip TOML; picks + blend inline in `score.py`.
**Pros**: Smallest diff; ships fastest.
**Cons**: Stringly-typed roles leak into discovery output and reports; ecosystem sets inlined
everywhere; FR-033 unmet; `score.py` absorbs gate logic.
**Why it might fail**: Does not satisfy locked FR-033/FR-039; guaranteed follow-up rework.

---

## 50% Rule Check

For Option A, the same goal with ~half the code:
- Ecosystem sets are **data tables**, not code — no detection classes, one `if manifest exists`
  loop.
- Reuse `context.read_sources` glob expansion and `_EXCLUDED_DIRS`; no new walker.
- Candidate "first heading" reuses `_doc_extract`'s ATX/setext heading regexes.
- No server-side state: rounds are just "was `agent_input` supplied?".
- `tomllib` is stdlib (Python 3.12 image) — no new dependency.

---

## Edge Case Checklist (inject into every TASK_GUIDE)

1. **Vendor/build noise**: generic globs must never match inside `node_modules`, `target/`,
   `dist/`, `build/`, `.venv/`, `vendor/` — extend `_EXCLUDED_DIRS` if needed, test with a fixture.
2. **Glob cost on monorepos**: role resolution must be bounded (reuse `MAX_DOC_SOURCES`-style caps)
   and report truncation, never silently stop.
3. **Determinism**: role → files ordering sorted; candidate lists sorted; FR-022 parity test must
   cover a run *with* agent input.
4. **Secret-bearing matches**: `.env`, `*.pem` matched by a role → excluded per DDR-0002; decide
   whether the role counts as found (recommend: **not found**, reason `excluded: secret-bearing`).
5. **Picks validation**: `..`, absolute paths, symlinks escaping the repo, non-existent, unknown
   role, secret-bearing → each rejected with a named error.
6. **TOML**: unknown key, wrong type, attempt to set a floor or remove a role → validation error
   naming the key; absent file → identical output to today's generic path.
7. **Blend rounding**: Python `round()` is banker's rounding — use `Decimal` ROUND_HALF_UP; clamp
   0–100; `confidence` outside [0,1] rejected.
8. **±10% band at threshold 0**: band collapses to exact equality — acceptable, but test it.
9. **Gate evaluation for a non-gated dimension** → rejected (FR-037); evaluation citing a ref not in
   the pack → rejected (FR-015a).
10. **Candidate headings** pass through redaction (NFR-010) before entering `needs_input`.
11. **Snapshot churn**: coverage semantics change → existing coverage/report snapshots update once,
    in T026 only, with the diff explained in Evidence.
12. **Parity normalization list** (DDR-0005) must **not** grow; if it has to, stop and report.

---

## Surgical Scope

**Should touch**: `core/models.py` (SourceRole, descriptor field), new `core/roles.py`, new
`core/gate.py`, `core/pipeline.py` (role coverage), `core/judge.py` (disclosure states),
`core/score.py`, `core/report.py`, `dimensions/*.py` (roles data), both adapters (one parameter
each), tests + one non-Python fixture repo, `README.md` / MCP guides.

**Must not touch**: `core/redact.py` logic, `core/budget.py` policy, `core/findings.py` validation
rules (reuse, don't fork), the Dockerfile/compose hardening (`--network none` stays),
DDR-0005 normalization list.

---

## Recommended Path

**Option A — Roles-as-data in place**, split into three tasks:

| Task | Scope | Complexity / Risk |
|---|---|---|
| T026 | Roles, generic + ecosystem pattern tables, `.easy-verifier.toml`, role coverage in all 7 dimensions, picks replay (`agent_input.picks`) in both adapters, source provenance | C3 / High (structural; coverage semantics change) |
| T027 | MCP detect gate: `needs_input.picks` candidates (≤20, path + heading, redacted, sorted) | C2 / Medium |
| T028 | Evaluate gate: ±10% / abstention detection, `gate_evaluations` validation, capped blend, rating provenance, overall disclosure, report rendering | C3 / High |

## Next Actions (Stage 2)

1. Confirm Option A and the three-task split.
2. `to-issues` → Kanban rows T026–T028 (T027, T028 depend on T026).
3. Generate `tasks/TASK_GUIDE_T026.md`…`T028.md` from the template, each carrying the Edge Case
   Checklist above.
4. `PROJECT_SPEC.md` glossary: *source role*, *ecosystem pattern set*, *agent input*, *hard gate*,
   *gate evaluation*, *capped blend*, *agent-rated*.
