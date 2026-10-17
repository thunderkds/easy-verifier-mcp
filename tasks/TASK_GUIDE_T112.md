# TASK_GUIDE — T112: Agent-confirmed test ↔ changed-symbol pairs (change-risk slice 2)
**Date**: 2026-10-17
**Complexity Level**: C2
**Risk Level**: Medium (changes which tests count as matched, so `change_risk` moves for bugfix/feature changes; new MCP gate on untrusted agent input)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary: **Change kind**, **Matched test**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` FR-081, FR-082, FR-084; `docs/ddr/0014-change-risk-dimension.md`; `BRAINSTORMING_LOG_change-risk.md` decision 2
7. Read the T109 gate end to end — it is the pattern to copy: `core/gate.py` (`change_kind_request`,
   `parse_change_kind`), `core/score.py` (`_change_kind_answer`, `change_kind_question`),
   `core/synthesis.py` (`_confirmed_kind`), `core/pipeline.py` (`confirmed_kind`),
   `adapters/mcp_server.py` (`needs_input["change_kind"]`), `core/roles.py` (`_AGENT_INPUT_KEYS`),
   `core/report.py` (change-kind block)
8. Read `dimensions/change_risk.py` (`_bugfix_metric`, `_feature_metric`) and
   `dimensions/blast_radius.py` (`_diff_files`, `_declared_name`, `tables.public_declarations`) — the
   diff parser and declaration patterns to reuse, not rewrite

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16 (DDR-0014 decision 2, brainstorming): *"ask supervisor agent about that, if not ask
general llm"* — the engine proposes changed-test ↔ changed-symbol pairs (symbol reference first,
naming convention second); a gate asks the calling agent to confirm each; unanswered → the
deterministic match stands, labelled `detected`. User, 2026-10-17: picked "Change-risk S2" as the
next work.

**Restated intent**:
> Today a test is *matched* to changed code only by file name (`test_dates.py` ↔ `dates.py`). Slice 2
> adds a second, stronger signal and lets the calling agent judge both:
> 1. **Changed symbols** — for each changed source file, the names the diff touches: declarations on
>    added/removed lines, plus the enclosing declaration git names in each hunk header, both read with
>    the registry's `public_declarations` pattern for that file's suffix. A language without a pattern
>    yields no symbols for that file (disclosed; naming still applies).
> 2. **Proposed pairs** — a test file added or changed in the scope (live, not deleted, same project)
>    pairs with a changed source file when the test's text references one of that file's changed
>    symbols as a whole word (`basis: "symbol"`, cited test line), else when names correspond
>    (`basis: "name"`, today's rule). Each pair carries its basis and evidence.
> 3. **Gate** — MCP returns `needs_input.test_pairs` (the proposals, the unpaired changed tests and
>    unpaired changed sources, fixed instructions). The agent answers `agent_input.test_pairs` =
>    a list of `{source, test, verdict: "confirm" | "reject", reason}`; it may also **add** a pair not
>    proposed, which must name a live changed test and a changed source in the same project and cite
>    a `ref` (`test-path:line`) whose line exists in that test file. CLI never asks; it accepts the
>    same answer via `--agent-input`. Replay with the same agent input is byte-equal (FR-022).
> 4. **Effect** — `bugfix_without_regression_test` and `new_code_without_test_share` use the final
>    pair set: detected pairs, minus pairs the agent rejected, plus valid pairs the agent added. Each
>    pair in the derivation says `detected` or `confirmed` (or `added`), with its basis. Invalid answer
>    entries are listed as rejected with the reason, never an error, and never change the pair set.
> 5. Refactor rules keep naming correspondence repository-wide (unchanged); chore unchanged.

**Out of scope**: refactor matching, reach to entry points (S3), co-change (S4), contract changes
(S5), any model call in the engine (NFR-001), new languages' declaration patterns.

**Requirement Refs**: FR-084 (new, added with this guide), FR-081, FR-082, US-022.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-17; DDR-0014 decision 2)
- [x] Domain terms align with `PROJECT_SPEC.md` (**Matched test** already names "slice 2: agent-confirmed symbol pairs")
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T110
**Entry point**: `score_repository` via CLI/MCP `score` at `changes`/`worktree` scope, dimension `change-risk`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | Changed symbols: a diff that edits the body of `def parse_date` (Python) or `export function parseDate` (TS) yields that name from the hunk header; a diff adding/removing a declaration line yields that name; a file whose suffix has no `public_declarations` yields none and the derivation says so |
| 2 | A changed test that references a changed symbol as a whole word pairs with that source with `basis: "symbol"` and a cited `test:line`, **even when the file names do not correspond** (e.g. `tests/test_api.py` calling `parse_date` changed in `utils/dates.py`); substrings (`parse_date_v2`) and tests in another project do not pair |
| 3 | Name correspondence pairs stay (`basis: "name"`); a pair found by both is listed once with `basis: "symbol"` |
| 4 | MCP `score` at changes/worktree scope returns `needs_input.test_pairs` with `proposals` (`source`, `test`, `basis`, `symbol`, `ref`), `unpaired_tests`, `unpaired_sources`, `instructions`, capped and the cap disclosed; no gate at project/task scope or when the kind is chore/refactor or there are no changed sources |
| 5 | `agent_input.test_pairs` validated (untrusted): unknown keys, bad verdict, empty/over-long reason (≤ 500 chars), a pair naming a file not in the change, a deleted test, a cross-project pair, or an added pair whose `ref` line does not exist in that test → listed in `test_pairs.rejected` with the reason; valid entries applied; `roles._AGENT_INPUT_KEYS` accepts `test_pairs` |
| 6 | Rejecting the only detected pair of a bugfix flips `bugfix_without_regression_test` from pass to fail; adding a valid pair to an unpaired bugfix flips it to pass; the same for `new_code_without_test_share` share; derivations list each pair with `detected`/`confirmed`/`added` and its basis |
| 7 | CLI `--agent-input` with the same document gives the same payload as MCP (minus `needs_input`); running twice with the same input is byte-equal |
| 8 | `project` scope payloads byte-identical to `develop` on this repo and one real repo (sha256 pasted) |
| 9 | **Real repos, pre-registered** (write the expected `change_risk` and pair list first, then run in the background one at a time): node-monorepo bugfix `09be767d0` (no test: still 0 / fail, no proposals); fullstack-ts bugfix-with-test from T108 (pair now shows its basis; still 100); one real commit where a test pairs by symbol but not by name (find it; if none exists on the 5 repos, say so with the search command used) — paste each headline and pair list |
| 10 | Report renders the pair list (basis + source of each pair) in the change-risk block; existing report tests green |
| 11 | Tests in `tests/test_t112_test_symbol_pairs.py` cover AC1–AC7 and AC10 on synthetic git repos; T108/T109/T110 tests stay green (any changed expectation listed and justified) |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- Pairs, gate and rule effects behave as specified on synthetic and real repos.
- New tests pass; full suite and ruff green; project payloads unchanged.

### Verification Command (exact, runnable)

Py3.12 venv as in T107 (`.venv` is broken — system Python 3.14).

```bash
<py312> -m pytest -q tests/test_t112_test_symbol_pairs.py
<py312> -m pytest -q          # background; read the exit code directly
<py312> -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T112.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T112.md`. BEFORE = a synthetic bugfix whose only test calls the
> changed function but is named differently → `bugfix_without_regression_test` 0 (fail) on `develop`.

---

## UI / Design Acceptance Criteria

> N/A — the pair list is added as rows inside T108's existing change-risk report block; no layout
> change. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T109's `change_kind` gate (request → parse → apply in synthesis → payload
`source`) — copy its shape for `test_pairs`. Reuse `blast_radius._diff_files` / `_declared_name` and
`tables.public_declarations`; if they must move to share them, move them to a core module rather than
duplicating.

1. Capture BEFORE (synthetic repo, `develop`).
2. Changed-symbol extraction, test-first (AC1).
3. Pair proposal with basis (AC2–3), then wire into `_bugfix_metric` / `_feature_metric`.
4. Gate request + parser + application + payload (AC4–7), copying T109.
5. Report rows (AC10). 6. AC8 sha256 check. 7. AC9 real repos, background, one at a time.

---

## Edge Case Checklist

- [ ] Symbol shorter than 3 characters or a common word (`get`, `run`) — never a symbol match on its own (state the rule you choose, e.g. min length + not in the language's keyword list)
- [ ] A test that only *defines* a same-named helper is not a reference (skip declaration lines of the test)
- [ ] Hunk header with no recognisable declaration → no symbol from that hunk
- [ ] Renamed source (`R` entry): symbols read from the new path
- [ ] Diff clipped → change-risk already abstains (T108); no gate
- [ ] Agent confirms a pair that was not proposed without `ref` → rejected, not added
- [ ] Agent answer present but kind is chore/refactor → answer ignored with a note (as T109 does for change_kind with no kind)
- [ ] Redaction: paths and reasons in `needs_input`, payload and report pass through `redact`

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/change_risk.py` | changed symbols, pair proposal, final pair set into bugfix/feature metrics |
| `src/easy_verifier/core/gate.py` | `test_pairs_request`, `parse_test_pairs` |
| `src/easy_verifier/core/score.py`, `core/synthesis.py`, `core/pipeline.py`, `core/models.py` | carry proposals/answers like `change_kind` |
| `src/easy_verifier/core/roles.py` | `test_pairs` agent-input key |
| `src/easy_verifier/adapters/mcp_server.py` | `needs_input["test_pairs"]` + tool description line |
| `src/easy_verifier/core/report.py` | pair rows |
| `tests/test_t112_test_symbol_pairs.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| other dimensions' rules and weights | out of scope |
| `core/judge.py` thresholds | slice 1 rules unchanged; only their inputs change |
| refactor metrics | out of scope (naming stays) |

---

## Test Plan

Synthetic git repos per case (Python + TS); real-repo runs are evidence, not tests.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T112-test-symbol-pairs`
- [ ] AC9 expectations written before the runs; results pasted after
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
