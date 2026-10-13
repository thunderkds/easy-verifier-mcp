# TASK_GUIDE — T093: The layer rule's classified-share floor counts only backend units
**Date**: 2026-10-13
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` (glossary **Layer**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from `.claude/agents/general-agent-template.md`
6. Read `tasks/TASK_GUIDE_T088.md` and `tasks/TASK_REVIEW_T088.md` (behaviour layers, real-repo shares)

---

## Requirement (Pillar 1 — Adapt the requirement)

T088 follow-up (2026-10-13): `layer_direction_violations` abstains when fewer than
`MIN_CLASSIFIED_SHARE` (0.50) of non-shared source files classify. The denominator is the whole
repository, including frontend apps whose files can never be api, service or data. Results:
kitchd 49/177 (28%; 88 of 177 are `apps/web` + `apps/mobile`); bryony `--all` 450/1063 (42%,
including `frontend/` and `design/`).

Question to the user: "Should we count only the backend part of the repo? My suggestion: yes."
User (2026-10-13): **"yes, agree"**.

**Restated intent**:
> The classified share is computed within **backend units** only. A backend unit is the nearest
> directory, at or above an api file (by behaviour), that holds a package manifest (the existing
> `package-manifest` source role patterns). Source files outside every backend unit leave the
> denominator, and the derivation says how many left and why. With no api file found, the
> denominator stays the whole repository, as today.

**Out of scope**:
- `MIN_CLASSIFIED_SHARE` (stays 0.50) and the weights
- Violations: still counted over all classified in-repo files
- Scoring frontend architecture

**Requirement Refs**:
- FR-075 (behaviour layers); user decision 2026-10-13

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user, 2026-10-13: "yes, agree")
- [x] Domain terms align with `PROJECT_SPEC.md` (layer, source role)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-075 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T088 (behaviour layers, merged)

**Entry point**: the `MIN_CLASSIFIED_SHARE` check in `_layer_direction_violations`, `src/easy_verifier/core/metrics.py`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Backend unit = for each api file (behaviour), the deepest ancestor directory holding a file matching the `package-manifest` role patterns (repo root included). The union of those directories forms the backend units | defined without folder names |
| 2 | The share denominator = non-shared source files inside a backend unit. When a unit is nested in another, the **deepest** unit containing the api file is used, so the root `package.json` of a monorepo does not swallow `apps/web` | monorepo frontends leave |
| 3 | No api file → the denominator is the whole repository (today's behaviour) | no regression |
| 4 | The derivation states: the backend unit(s) used, files in units / total, and the count of files outside every unit ("N source files outside backend units (apps/web, apps/mobile) are not counted") | disclosed |
| 5 | Single-manifest repo (coffee-shop-api): result identical to today | no regression |
| 6 | Both extremes pinned: a monorepo fixture `apps/api` (manifest, route, model, service) + `apps/web` (manifest, 10 React files) is measured; sabotage the unit predicate to "whole repo" and it must abstain | pinned |
| 7 | **Real repos (paste, hand-checked)**: kitchd (expect about 49/87, measured), bryony `--all` (backend/ unit), coffee-shop-api (unchanged), ai-training (no api file → unchanged). For each newly measured repo: the violations value and up to 3 cited violations checked by hand against the source | real-repo verified |

---

## Evaluation & Acceptance

### Verification Command

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope project < /dev/null
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T093.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: the share computation in `_layer_direction_violations`; the
`package-manifest` patterns in `core/roles.py` (reuse them, never a new name list). The pack
already carries the file set the layer rule considers. Find the manifest paths in that set or the
resolved roles, with no new disk walk (metrics do no I/O).

---

## Edge Case Checklist

- [ ] Manifest at the repo root only: unit = root → same as today
- [ ] An api file with no manifest above it except the root: root unit
- [ ] Several backend units (two services): union of their files
- [ ] Third-party excluded paths (T087) are never units
- [ ] Batches: a unit whose manifest is in an unread batch. Use the manifest paths from role resolution, which see the whole repository

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | backend-unit denominator + derivation |
| `docs/SCORING_RULES.md` | layer row |
| `tests/test_t093_backend_unit_share.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `MIN_CLASSIFIED_SHARE`, `RATING_RULES` | unchanged |

---

## Completion Checklist

- [ ] Implementation done; tests written and pass; real-repo runs pasted and hand-checked (AC 7)
- [ ] Supervisor notified: task ready for Stage 4 review
