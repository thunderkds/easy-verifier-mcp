# TASK_GUIDE — T098: The score payload discloses when a rated dimension's inputs were capped
**Date**: 2026-10-14
**Complexity Level**: C2
**Risk Level**: Medium (changes the score payload shape for both adapters; replay parity, DDR-0005)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`
**Depends on**: none

## Feature Task Guide — T098

### Background (follow-up from T094, 2026-10-13)
On k8s-ops (develop `9bfa721`), `easy-verifier score` rates **infrastructure 100**. The only
`computed_from` is 50 manifests, but the repo has 197 Kubernetes manifests. The score JSON says nothing
about that: `'exceed the cap' in json` and `'matched more than' in json` are both False.

Root cause, as the Supervisor diagnosed it:
- `core/roles.py` resolution caps every role at `MAX_ROLE_FILES = 50` (line ~1483) and records only
  the role name in `RoleResolution.truncated_roles`.
- `core/pipeline.py` turns that into a pack **warning** string through `resolution_warnings()`:
  "Source role 'k8s-manifest' matched more than 50 files…". The `infrastructure` pack's
  `warnings` carries it, and the HTML report renders pack warnings.
- `ScoreResult.warnings` (`core/score.py:133`) is a pure function of the ratings. It lists only
  evidence-lack **abstentions**. A *rating* computed from capped inputs is therefore never disclosed in
  the score payload, which is the surface an agent reads.
- Each dimension's own per-role cap (`CAP_WARNING` in `dimensions/infrastructure.py`, `operations.py`,
  `supply_chain.py`, `data.py`, and `SCAN_CAP_WARNING` in `blast_radius.py`) has the same gap. It
  rarely fires behind the 50-file role cap, but it is still the same class of silent bound
  (NFR-009: never a silent stop).

### Supervisor decisions (no score changes, disclosure only)
- New **optional** top-level key `capped` in `ScoreResult.to_dict()`, present only when non-empty. This
  follows the `samples` / `excluded` precedent, so a repository with no cap hit serialises
  **byte-for-byte as before**. Shape, one entry per (dimension, role) bound hit, in canonical dimension
  order and then role name:
  `{"dimension": str, "role": str, "matched": int, "read": int}`.
  - `matched` is the true count of files that matched before the cap (k8s-ops
    k8s-manifest → 197). `RoleResolution` must keep the count, not only the name.
  - `read` is the number actually used (50).
  - A dimension-level cap (`CAP_WARNING`) reports its own `matched`/`read` under the same shape.
- Both adapters (CLI `score` and MCP `score`) carry it identically. Replay
  (`registry_entries` / DDR-0005 parity tests) stays byte-equal.
- The existing pack warning strings stay unchanged. No rating, threshold or weight moves.
- Out of scope: capping or changing the cap values, and changing the report layout. If the report
  already renders pack warnings, leave it as it is.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | A fixture repo with > 50 files in one role yields `capped: [{dimension, role, matched: N, read: 50}]` in `score` output for each dimension that reads that role, with N equal to the true match count |
| 2 | A fixture with no cap hit has no `capped` key, and its serialised payload is byte-identical to develop (existing golden/parity tests pass unedited) |
| 3 | A dimension-level cap (e.g. infrastructure `MAX_FILES_PER_ROLE` reached with the role cap not hit, by monkeypatching the constant) also appears in `capped` |
| 4 | CLI and MCP `score` payloads agree (existing parity normalisation unchanged) |
| 5 | k8s-ops real run: `capped` contains `{"dimension":"infrastructure","role":"k8s-manifest","matched":197,"read":50}` (or the true count, pasted). Every rating before → after is pasted and unchanged |
| 6 | node-monorepo, fullstack-ts, nest-api, python-ml, this repo: ratings before → after are unchanged, and any `capped` entries that appear are pasted and checked by hand against the repo |

### Files to Change (prediction, not contract)
- `src/easy_verifier/core/roles.py`: keep the matched count per truncated role
- `src/easy_verifier/core/pipeline.py` / `core/models.py`: carry structured cap info on the pack (not only the string)
- `src/easy_verifier/dimensions/{infrastructure,operations,supply_chain,data,blast_radius}.py`: record the structured cap beside the existing warning
- `src/easy_verifier/core/score.py`: the `capped` property plus its `to_dict` entry
- `tests/test_t098_capped_disclosure.py` (new)

### Files Must NOT Touch
`core/redact.py`, the rule registry and thresholds, `core/report.py` layout.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

All read-only:
- k8s-ops `<real-repos>/k8s-ops`
- node-monorepo `<real-repos>/node-monorepo`
- fullstack-ts `<real-repos>/fullstack-ts`
- nest-api `<real-repos>/nest-api`
- python-ml `<real-repos>/python-ml`

Command: `.venv/bin/easy-verifier score --repo <path> </dev/null`. Run it in the background. Agent
worktrees have no `.venv`, so use the main checkout's interpreter with `PYTHONPATH=src`.

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T098.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T098.md`.

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.
