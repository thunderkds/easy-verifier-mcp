# TASK_GUIDE — T088: Layers assigned by observed behaviour
**Date**: 2026-10-12
**Complexity Level**: C3
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary **Layer**, updated 2026-10-12)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md` (C3: decompose, then verify each slice)
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` and `docs/ddr/0011-code-derived-rules-and-flexible-conventions.md`
8. Read the probe `BRAINSTORMING_LOG_document-recognition.md` § Round 3 (what the crude probe got wrong)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-12): *"with the architecture, we don't check the document only, it relate to the code
structure, the life cycle of request, or anything from the code overview, code architecture"*. Then,
on the DB question: *"database is not relate to the repos scoring, cause it belong to another
service, we just check what we have"*.

Today `layer_direction_violations` (weight 40) assigns layers only from folder names
(`registry/curated/conventions.toml` `[[layer_paths]]`: `controllers/`, `routes/`, `services/`,
`repositories/`, `dao/`…). bryony's `backend/server/*/routers/*.js` and
`backend/platform/core/models/` are largely unclassified.

**Restated intent**:
> A file's layer comes from what its code does. *api* registers a route (route tokens as extended by T079, and
> decorators). *data* calls a recognised DB/ORM API on an imported model or client symbol.
> *service* sits on the in-repo import path between an api file and a data file. Folder conventions
> are only a hint. The layer rule still counts lower → higher imports among in-repo files, now over
> behaviour-assigned layers.

**Out of scope**:
- Scoring anything about the database or an external service (it is a boundary; user, Q2)
- Request-path reporting (T090)
- Weight changes: `layer_direction_violations` stays at 40 (DDR-0011)
- Frameworks beyond the first set

**Requirement Refs**:
- FR-075 (added 2026-10-12)
- FR-067 (architecture 20/80; weights unchanged)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user: G1 agreed; Q2 answered; "go" 2026-10-12)
- [x] Domain terms align with `PROJECT_SPEC.md` (**Layer** redefined 2026-10-12; *source role* is a different concept)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-075 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T087 (third-party code excluded, so Harbor never contributes layers). T079 (Express routes on any receiver bound to `express()`/`Router()`, exported-function params and properties) and T078 (repo conventions embedded for replay, so `.easy-verifier.toml` layer hints may be used as hints) are Done (merged 2026-10-12)

**Entry point**: `_layer_direction_violations` in `src/easy_verifier/core/metrics.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Registry fields per framework, each cited: **api** evidence (route tokens and decorators) and **data** evidence (DB/ORM call forms). First set: Express (+ Mongoose, `pg`/`mysql2`, Knex), NestJS (+ TypeORM, Prisma), FastAPI (+ SQLAlchemy), Django (views/urls + ORM `objects.*`) | behaviour, cited registry |
| 2 | **data** requires the receiver to be a symbol **imported or defined** in the file as a model or client (e.g. `const User = mongoose.model(...)`, `import { PrismaClient }`, `from sqlalchemy.orm import Session`). Bare `.find(` on an arbitrary receiver (e.g. `Array.find`) never makes a file data | precision (probe false positive) |
| 3 | **service** = a non-api, non-data in-repo file on an import path from an api file to a data file. Files on no such path are unclassified (not counted), as today | behaviour |
| 4 | A file with both api and data evidence is **api** (the route is the entry). Its direct DB access is **not** a violation and is not scored (user Q2) | boundary not scored |
| 5 | A violation is an in-repo import from a lower to a higher layer (data → service, service → api, data → api), cited by `file:line` with the import statement, max 5 examples as today | structural defect only |
| 6 | Path conventions (`layer_paths`) become a **hint**. When hint and behaviour disagree, behaviour wins and the payload lists the disagreement (file, hint layer, behaviour layer, evidence line) | hint, reported |
| 7 | Framework not recognised and no hint classifies ≥ `MIN_CLASSIFIED_SHARE`: the rule abstains with reason code `framework_not_recognized`, distinct from "no routes found" | honest abstention |
| 8 | **Embarrass-the-implementation fixtures**: arbitrary Express receivers (`webapp`), `Array.prototype.find` lookalikes, a Nest controller whose service is constructor-injected (relative TS import present), and a FastAPI router using `Depends(get_db)` | adversarial |
| 9 | **Real repos (paste)**: bryony, kitchd, coffee-shop-api, ai-training, scraping-devops before and after. For each: classified share, violation count, cited examples, disagreements with path hints. Hand-check at least 3 cited violations and 3 disagreements per repo against the source | real-repo verified |
| 10 | CLI/MCP parity (DDR-0005). The DDR-0011 floor `MIN_CLASSIFIED_SHARE` is unchanged | parity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Express fixture: `server/r.js` (webapp.get + imports `lib/svc.js`), `lib/svc.js` imports `lib/store.js` (mongoose model `.find`) | r=api, svc=service, store=data; 0 violations | automated test |
| 2 | same, plus `lib/store.js` imports `server/r.js` | 1 violation data → api, cited | automated test |
| 3 | `util.js` using `[].find(x => …)` only | not data | automated test |
| 4 | route file calling `User.find()` directly | api, no violation | automated test |
| 5 | Folder `services/` holding a route registration | behaviour api; disagreement listed | automated test |
| 6 | unknown-framework fixture, no hints | abstains `framework_not_recognized` | automated test |
| 7 | sabotage: make the data predicate always false | SC 1 and 2 fail (proves the test pins it) | automated test, both extremes |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
# real repos, one at a time, run_in_background:
.venv/bin/easy-verifier score --repo <repo> --scope project > /tmp/<name>.json
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T088.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `_layer_direction_violations` and `_top_level_import_cycles` in
`core/metrics.py` (import graph, citation format, `MAX_LAYER_EXAMPLES`); `[[route_tokens]]` and
`[[layer_paths]]` in the registry (how cited patterns are declared); the scratchpad probe
`arch_probe.py` (BFS idea only; its regexes are known wrong).

Decompose (C3): (a) registry fields + loader; (b) per-file evidence detection; (c) layer assignment
over the existing import graph; (d) rule over assigned layers + disagreement reporting; (e) real-repo
pass. Reuse the import graph the cycle rule already builds. Do not build a second one.

---

## Edge Case Checklist

- [ ] Re-exports / barrel files (`index.ts`) on the path: still service, not unclassified
- [ ] A data file imported by two api files: one data file, no double counting
- [ ] Circular imports between api and service: cycle rule counts it; the layer rule counts each edge once
- [ ] Test files never take a layer
- [ ] Batches (DDR-0010): a layer derived from files in an unread batch is not assumed. Disclose as today
- [ ] Python relative imports (`from ..db import session`) resolve

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/curated/js-ts.toml`, `python.toml` | per-framework api/data evidence fields, cited |
| `src/easy_verifier/core/registry.py` | load and validate the new fields |
| `src/easy_verifier/core/structure.py` / `metrics.py` | behaviour layer assignment; rule uses it; hints → disagreements |
| `src/easy_verifier/registry/curated/conventions.toml` | header comment: `layer_paths` are hints |
| `docs/SCORING_RULES.md` | layer rule row |
| `tests/test_t084_behaviour_layers.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` weights in `core/judge.py` | DDR-0011 weights unchanged |
| document rules (`_document_rule`) | T089 |

---

## Test Plan

Fixtures per framework (SC 1–7), including both-extremes sabotage. Real-repo pass on 5 repos,
with hand-checked citations.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T088.md`
- [ ] Real-repo runs pasted and hand-checked (AC 9)
- [ ] Supervisor notified: task ready for Stage 4 review
