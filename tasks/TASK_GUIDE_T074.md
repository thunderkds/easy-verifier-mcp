# TASK_GUIDE — T074: architecture from code + documents (20/80) — layer direction, widened doc conventions, code-aware floor
**Date**: 2026-10-04
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` (glossary: Convention pattern, Requirement item, Layer, Source role)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`, `BRAINSTORMING_LOG_code-derived-rules.md`, and
   `/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/docs/ddr/0011-code-derived-rules-and-flexible-conventions.md`
   (docs/ddr is gitignored — main checkout only), plus DDR-0007 (registry citations)

---

## Requirement (Pillar 1 — Adapt the requirement)

User decisions (2026-10-04, DDR-0011, grilling G3/G4): architecture = documents 20 (description 10,
decision records 10) + code 80 (import cycles 40, layer direction 40); a missing document is a failed
rule; the layer rule abstains when < 50% of source files classify; the coverage floor also counts code
evidence; document roles accept common conventions (e.g. a README "Architecture" section).

**Restated intent**:
> A repository with clean module structure but no architecture docs gets an architecture number from its
> code, losing only the 20 document points; layer-direction violations become a cited, measured rule.

**Out of scope**: requirement-fidelity (T075); new layers beyond api/service/data; fan-out rule.

**Requirement Refs**: FR-067, FR-069, FR-071 (architecture part), FR-068 (uses T073 patterns).

### Requirement Fidelity Gate

- [x] Restated intent confirmed (user: "yes, plan and run them automatically", 2026-10-04, after grilling G1–G5)
- [x] Domain terms align with the glossary
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T073 — `layer_of` and layer patterns
**Entry point**: `layer_direction_violations`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | `RATING_RULES['architecture']` = `architecture_description_missing` 10, `decision_records_missing` 10, `top_level_import_cycles` 40, `layer_direction_violations` 40; areas and citations set (42010 for docs; Martin ADP / SDP for code; thresholds at most 0) | FR-069 |
| 2 | New metric `layer_direction_violations`: count of import statements from a lower to a higher layer (data→service, service→api, data→api) among classified source files; derivation lists classified share and up to N example edges with file:line; abstains when classified share < 0.50 or no imports read | FR-069 |
| 3 | Missing architecture description / decision records = failed document rule (value 1), never abstention, when the search ran | FR-067 |
| 4 | `architecture-doc` role also filled by a README section whose heading contains "Architecture" (cited excerpt), `docs/architecture*`, `ARCHITECTURE.md`; extendable | FR-068 |
| 5 | Coverage floor counts code evidence: architecture also seeks a source role for files with imports, so a repo with code + README passes the floor | FR-071 |
| 6 | Batches (T068) and measured-weight floor (T067) still apply; sampled metrics labelled | DDR-0010 |
| 7 | `docs/SCORING_RULES.md` and `docs/AREA_COVERAGE.md` updated (T072 sync test passes) | FR-066 |
| 8 | CLI/MCP parity and replay unchanged in form | FR-022 |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|---|---|---|
| 1 | Fixture repo: controllers/services/repositories, one repository importing a service | 1 violation, cited | automated |
| 2 | Fixture with no docs, no cycles, no violations | architecture 80 (documents fail) | automated |
| 3 | Fixture where < 50% files classify | layer rule abstains; rated on cycles + docs (60% measured) | automated |
| 4 | README with `## Architecture` | description rule passes | automated |
| 5 | coffee-shop-api, bryony, kitchd | before/after table (Supervisor) | verify |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t074_architecture_code_rules.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T074.md`.

---

## Demonstration

> BEFORE (Supervisor, scratchpad `t073/before.txt`): coffee-shop-api architecture `below_coverage_floor`; bryony 70; kitchd 100.

---

## UI / Design Acceptance Criteria

Pure backend/rules task — no UI change. Evidence rows: ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/architecture.py` + `core/metrics.py` (`top_level_import_cycles` derivation and abstention style), `core/judge.py` RATING_RULES entries with citations.

Update existing tests that pin the old architecture weights; cite DDR-0011 in each changed test.

Environment notes for the implementer: worktrees have no .venv — `PYTHONPATH=src <main>/.venv/bin/python -m pytest`; `</dev/null` on CLI calls; the 2 container tests fail on a stale Docker image (ignore); no network installs; never write into real repo trees. Budget ~60 tool calls (the step-limit hook stops at 90); the Supervisor runs real-repo before/after and screenshots at Stage 5.

---

## Edge Case Checklist

- [ ] Imports resolved textually (stem match) — same approach and wording as import cycles
- [ ] Unclassified files and test files never counted
- [ ] Monorepo: classify per file; edges only between classified files
- [ ] Old stored agent input / replay still validates (rule set changed → document in DDR)

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `core/judge.py` | architecture rules/weights (user-signed via DDR-0011) |
| `core/metrics.py`, `dimensions/architecture.py` | new metric + code role |
| registry roles | architecture-doc conventions |
| `docs/SCORING_RULES.md`, `docs/AREA_COVERAGE.md` | update (`git add -f`) |
| `tests/test_t074_architecture_code_rules.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| requirement-fidelity rules | T075 |
| rating arithmetic, gates, floors logic | DDR-0010 |

---

## Completion Checklist

- [ ] Implementation done; tests pass; ruff clean
- [ ] Supervisor notified
