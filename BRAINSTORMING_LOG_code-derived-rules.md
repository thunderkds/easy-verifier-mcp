# BRAINSTORMING_LOG.md — Code-derived rules: rate architecture and requirement-fidelity without kit-style docs
**Generated**: 2026-10-04
**Task / Context**: User observation after coffee-shop-api / area-coverage review — document rules "just stick on the personal" workflow; reference: Understand-Anything (github.com/Egonex-AI/Understand-Anything, MIT).
**Skill**: `Skill({ skill: "brainstorming" })` — tier **Deep** (changes user-signed weights DDR-0007/0008; new evidence class)
**Branch**: `plan/code-derived-rules`

---

## The Problem Space

Three of seven dimensions are rated mostly from documents written in this project's own workflow
style (verified in `judge.RATING_RULES` / dimension `sources_sought`, 2026-10-04):

| Dimension | Weight on document existence | Coverage-floor sources | Typical result on an ordinary repo |
|---|---|---|---|
| architecture | 60 of 100 (`architecture_description_missing` 30, `decision_records_missing` 30) | architecture-doc, decision-record, readme (floor 0.40) | abstains or fails |
| requirement-fidelity | 100 of 100 (AC↔code 35, AC↔test 35, `requirements_docs_count` 15, `code_commits_with_docs_share` 15) | requirements-doc, spec-doc, **task-breakdown** (floor 0.50) | `below_coverage_floor` almost always |
| solution-fit | no rule (agent-only) | requirements-doc, decision-record | agent-rated only |

coffee-shop-api (a well-built NestJS repo with `specs/` phase plans) is rated on 2 of 7 dimensions;
its plans do not even count as requirements docs.

Understand-Anything shows the split we already use: deterministic structure (tree-sitter: files,
imports, calls, classes) + an LLM layer for meaning (layers, domains, flows). Our engine keeps the
deterministic half; meaning stays with the calling agent and never becomes a number.

Non-negotiable: no inference in the engine; no number without evidence (DDR-0010); every rule's
metric and threshold cited (DDR-0007); adapter parity (DDR-0005); weight changes need user sign-off.

---

## Decisions Locked with the User (this session)

| # | Question | Answer |
|---|---|---|
| Q1 | Replace document rules, keep both, or profiles? | **Merge (both weigh)** — code and documents are both evidence in the repo |
| Q2 | Split inside architecture and requirement-fidelity | **20 documents / 80 code** |
| Q3 | How to read code structure | **A — cited registry tokens** (textual, no new dependency); UA graph import later at most |
| G1 | requirement-fidelity code rules | **B** — routes + commit issue references (then G2 adds requirement items) |
| G2 | AC tracing | **Flexible, not one format** — `requirement_items_traced_share` over any requirement-item form; abstains when none. Final weights: docs 10+10, routes 40, issue refs 20, items 20 |
| G3 | architecture code rules | **A** — cycles 40 + layer direction 40 (+ docs 10+10); layer rule abstains when < 50% of sources classify |
| G4 | Coverage floors | **A** — floors also count code evidence; `task-breakdown` dropped |
| G5 | solution-fit; route overlap with T044 | Supervisor defaults: solution-fit unchanged; validation/versioning stay in T044 |

Recorded: **DDR-0011**, PRD FR-067…FR-071, US-021; glossary: Convention pattern, Requirement item, Layer.

Derived rules (Supervisor, accepted with Q1): a missing document is a **failed** rule, never missing
evidence; document patterns accept common conventions; coverage floors stop requiring kit-only
documents to produce a number.

---

## Questions for the User (resolve in grill-with-docs)

1. Which code rules, with which thresholds, carry the 80? (Candidate set below.)
2. Route rules overlap the planned **api** dimension (T044, area 7). Put route↔test traceability in
   requirement-fidelity (area 2) and leave validation/versioning to T044?
3. Acceptance-criteria tracing needs AC docs: keep it inside the 20 document share, abstaining when no
   ACs exist?
4. solution-fit stays agent-only?
5. Coverage-floor sources: replace `task-breakdown` with code roles (route file, test file)?

---

## Candidate rule set (for grilling; weights are proposals)

**architecture** (area 1) — documents 20 / code 80

| Rule | Kind | Weight | Threshold | Standard |
|---|---|---|---|---|
| `architecture_description_missing` (now accepts README "Architecture" section, `docs/architecture*`) | doc | 10 | at most 0 | ISO/IEC/IEEE 42010:2022 |
| `decision_records_missing` | doc | 10 | at most 0 | ISO/IEC/IEEE 42010:2022 |
| `top_level_import_cycles` | code | 30 | at most 0 | Martin, Acyclic Dependencies Principle |
| `layer_direction_violations` (new: data → service → api allowed; reverse imports counted) | code | 30 | at most 0 | Martin, Stable Dependencies Principle; 42010 viewpoints |
| `max_module_fan_out` (new: most modules imported by one module) | code | 20 | project default | Martin package metrics (efferent coupling) |

**requirement-fidelity** (areas 2, 27) — documents 20 / code 80

| Rule | Kind | Weight | Threshold | Standard |
|---|---|---|---|---|
| `requirements_docs_count` (accepts PRD, specs/**, plan.md, OpenAPI) | doc | 10 | ≤ 1 authoritative | ISO/IEC/IEEE 29148 |
| `code_commits_with_docs_share` | doc | 10 | ≥ 0.30 | ISO/IEC/IEEE 26514 |
| `routes_without_test_share` (new: route handlers whose path/handler name no test references) | code | 40 | at most 0.2 | ISO/IEC/IEEE 29119-4 (coverage); 29148 traceability |
| `commits_with_issue_reference_share` (new: commits naming an issue/ticket id) | code | 20 | at least 0.5 | ISO/IEC/IEEE 29148 (traceability) |
| `behaviour_named_tests_share` (new: test names stating a behaviour, e.g. `should …`/`it('…')` text) | code | 20 | project default | ISO/IEC/IEEE 29119-3 |
| AC↔code / AC↔test tracing | doc | inside the 20 if kept | — | 29148 |

New registry fields per language (cited, DDR-0007): `layer_paths` (api/service/data/ui/util path and
name patterns), `route_tokens` (`@Get(`, `app.get(`, `router.`, `@app.route`, `[HttpGet]`, …),
`test_name_tokens`.

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|---|---|---|---|---|---|---|
| A | Minimal: widen doc conventions + floors | Accept README sections/specs/OpenAPI as docs; drop kit-only roles from floors; no new code rules | Low | ~250 lines | Low | |
| B | Merged rule sets via registry tokens | Q1–Q3 as locked: new structure tokens, 3–5 code rules, docs reweighted to 20 | Medium | ~1,500 lines over 3 tasks | Medium | ✅ |
| C | Structure graph module (UA-style, deterministic) | New `core/structure.py` building a module graph (imports, layers, routes) once per pack; all structure rules read it; graph optionally exported for the agent | High | ~2,500 lines | Medium-High | |

### Option A — Minimal
**Approach**: broaden role patterns (`registry` role globs), remove `task-breakdown`/`decision-record` from coverage floors.
**Pros**: fast; fixes "specs/ don't count".
**Cons**: architecture stays 60% documents; repos with no docs still fail most weight; contradicts Q1/Q2.
**Why it might fail**: it reweights nothing, so the user's complaint stands.

### Option B — Merged rule sets (recommended)
**Approach**: three tasks — (1) registry fields + extraction (`layer_paths`, `route_tokens`, `test_name_tokens`) with citations; (2) architecture code rules + reweight 20/80; (3) requirement-fidelity code rules + reweight 20/80 + floor sources.
**Pros**: matches all locked answers; reuses `import_statements`, metric-table and registry machinery; zero new deps; every new number cited.
**Cons**: textual matching is approximate (decorators split over lines, dynamic routes); weights re-signed.
**Why it might fail**:
- Layer classification by path is wrong for unconventional layouts → a false "violation". Mitigation: unclassified files never count; derivation lists the classified share; abstain when < N% of sources classify.
- Route↔test matching by path string misses tests that call helpers (`api-path.util.ts` in coffee-shop-api builds paths). Mitigation: match on handler name **or** path segment; report matched-by; P2-like abstention when no route tokens match.
- Commit-issue share is meaningless on squash-merged or solo repos → abstain below N commits.
- Miss-list class (shipped 7×): every new metric must say what bounded it (budget, batch, unclassified files).

### Option C — Structure graph module
**Approach**: a deterministic module graph like UA's (but token-based), built once and shared; exported in the pack for the agent's domain/flow summary.
**Pros**: one structure source for all dimensions; enables blast-radius/architecture/api reuse; best agent context.
**Cons**: big refactor of architecture/blast-radius extraction; larger payloads (already a T068 follow-up).
**Why it might fail**: scope creep; payload growth; two extraction paths during migration.

---

## 50% Rule Check

Ship B with fewer rules: architecture adds only `layer_direction_violations` (cycles already exist);
requirement-fidelity adds only `routes_without_test_share`. Two new metrics + reweight + floor change
≈ 50% of B and still rates both dimensions on ordinary repos. Fan-out, commit-issue and test-name
rules follow only if real repos show they add signal.

---

## Recommended Path

**Option B, cut per the 50% rule first**: registry tokens → `layer_direction_violations` +
`routes_without_test_share` → reweight 20/80 → floor sources without kit-only roles. Option C's
graph is a later refactor if a third consumer appears.

## Surgical Scope

**Should touch**: `registry/curated/*.toml` (+ citations), `core/metric_tables.py`, `core/metrics.py`,
`core/judge.py` (RATING_RULES / floors — user-signed values), `dimensions/architecture.py`,
`dimensions/requirement_fidelity.py`, role patterns, `docs/SCORING_RULES.md`, `docs/AREA_COVERAGE.md`
(the T072 sync test forces it), PRD + DDR-0011.
**Must not touch**: rating arithmetic, gate/floor logic (DDR-0010), improvement-plan computation,
report structure (T070), other dimensions' weights.

## Edge Case Checklist

- [ ] Unclassified files never count as violations; derivation reports classified share
- [ ] Routes built from helpers/constants (coffee-shop-api `api-path.util.ts`)
- [ ] Monorepos (several apps) — layers per top-level app, not across apps
- [ ] Repos with no routes (CLI, library) → route metric abstains, never fails
- [ ] Squash/solo history → commit-based metrics abstain below a declared minimum
- [ ] Batches (T068): structure metrics over sampled files are labelled sample
- [ ] Measured-weight floor (T067) still holds after reweighting
- [ ] Real-repo verification: coffee-shop-api, bryony, kitchd before/after

## Next Actions (Stage 2)

1. `grill-with-docs` on the open questions and the candidate rule set (terms: layer, route, handler, traceability).
2. DDR-0011 (supersedes parts of DDR-0007/0008 weights) + PRD FRs.
3. Tasks: T073 registry structure tokens; T074 architecture code rules + 20/80; T075 requirement-fidelity code rules + 20/80 + floor sources; each verified on real repos.
