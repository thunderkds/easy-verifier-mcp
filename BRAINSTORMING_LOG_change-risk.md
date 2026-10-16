# BRAINSTORMING_LOG.md — Change-risk scoring (feature / bugfix scope)
**Generated**: 2026-10-16
**Task / Context**: User 2026-10-16: "most of the scoring feature support the repository code, but for the
medium/small scope, like implement, and fix bugs, does this repos cover them as good as" → "yes, let
/brainstorming && /grill-with-docs this upgrade". Builds on the 2026-10-05 T081 finding and the user's
change-risk vision recorded in `memory/learnings.md` (2026-10-05 T081).
**Skill**: `Skill({ skill: "brainstorming" })` — tier **Deep** (architecture choice; changes every
`changes`-scope score).

---

## The Problem Space

`score --scope changes --ref main...HEAD` narrows **which files are read** but keeps **repository-health
rules**. Measured 2026-10-05: a one-file node-monorepo bugfix with no test scored **97** (architecture 90,
code-quality 100, blast-radius 100; test-strategy, security, requirement-fidelity abstained).

Verified causes (code, 2026-10-16):

| # | Cause | Where |
|---|---|---|
| 1 | Role files (test config, CI, lockfile, …) count only when they are **in the diff**; otherwise `"not in the resolved changes scope"` → the dimension falls below its coverage floor and abstains | `dimensions/test_strategy.py:239-251`; same pattern in `security.py:239`, `supply_chain.py:111`, `operations.py:189`, `infrastructure.py:192`, `api.py:200`, `data.py:156`, `reliability.py:144` |
| 2 | Test ↔ source correspondence only sees tests **inside** the scope, so "this change has no test" is never a rated fact, only a `sources_missing` note | `dimensions/test_strategy.py:303-307` |
| 3 | No notion of *what kind* of change it is, so nothing can require a regression test for a bugfix | — (absent) |
| 4 | Reach is file fan-in with a 400-file sweep ceiling that often abstains | `dimensions/blast_radius.py:100` (`MAX_SCAN_FILES`) |
| 5 | Abstention drops low contributors out of the average, so a narrow scope can score **higher** than the whole repo | T022 residue (a) |

Reusable pieces that already exist: `core/structure.py:find_routes` (entry points), `find_issue_references`
("fixes #N"), `requirement_fidelity.py:CO_CHANGE_WINDOW` (git co-change history, 200 commits),
blast-radius `public_symbols_removed` / `destructive_migration_ops` (contract breaks, changes-scope only),
`_deleted_change_set_tests` (deleted tests), the MCP gate pattern with validated agent input
(`core/gate.py`, DDR-0006) and CLI `--agent-input` replay (`adapters/cli.py:119`).

Non-negotiable constraints: NFR-001 / FR-040 (the engine makes no model call), FR-022 (replay with the same
agent input is byte-equal), FR-021/FR-034 (gates reach the wire only through MCP), and **`project`-scope
scores stay byte-identical** (no repository-health regression).

---

## Decisions taken in this session (user, 2026-10-16)

1. **Change kind** — `bugfix | feature | refactor | chore` (chore = docs/config/dependency-only). The
   engine *detects* a proposal from the diff's file kinds, branch name, commit subjects and issue
   references; a new MCP gate `needs_input.change_kind` asks the calling agent (the Supervisor, else
   whatever LLM drives the MCP client) to confirm or override; the answer returns as
   `agent_input.change_kind` (CLI: `--agent-input`). Unanswered → the detected kind is used and the
   payload says `source: "detected"` rather than `"confirmed"`.
   *User: "you will need to ask about the kind of thing to score, or you may depend on the changes file to
   detect and confirm with supervisor from llm about that".*
2. **"The change has a test"** — same pattern: the engine proposes changed-test ↔ changed-symbol pairs
   (symbol reference first, naming convention second); a gate asks the agent to confirm each, with cited
   refs validated against the pack (the `gate_evaluations` validator); unanswered → the deterministic
   match stands, labelled `detected`. *User: "ask supervisor agent about that, if not ask general llm".*

Principle for every new signal: **engine detects → agent confirms → deterministic fallback, disclosed.**

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|--------|------|---------|-------------|------------|----------------|--------------|
| A | Patch the existing dimensions | Read role files repo-wide; add change rules inside test-strategy / blast-radius | Medium (8 dimensions) | ~600 lines | Medium | |
| B | A `change-risk` dimension + shared context fix | New dimension active only at `changes`/`worktree`, owning kind, test match, reach, co-change, contract; one shared "context roles are repo-wide" rule for the others | Medium | ~1,200 lines over 4–5 slices | Low at project scope | ✅ Yes |
| C | Change checklist, not a score | At `changes` scope, emit an unrated checklist and suppress the headline overall | Low | ~250 lines | Low | |

### Option A — Patch the existing dimensions
**Approach**: Change the role probe in the 8 dimensions so context roles are read from the whole repo while
measurement stays on the diff; add `changed_code_without_test` to test-strategy and a symbol-reach rule to
blast-radius; the kind gate feeds test-strategy.
**Pros**: No new concept for readers; reuses each dimension's weights and report sections.
**Cons**: Change rules diluted inside repo-health weights (a missing regression test is one rule among
test-strategy's seven); kind logic spread over several dimensions; the headline still mixes repo health
with change risk.
**Why it might fail**: The 97 becomes maybe 85 — still "good" for a bugfix without a test, because
architecture 90 and code-quality 100 keep the average high. Weight retuning per scope turns into a
second weight table nobody can reason about.

### Option B — A `change-risk` dimension + shared context fix ✅
**Approach**:
1. **Shared context fix** (all dimensions): at a narrow scope, *context roles* (test config, CI,
   lockfile, linters, specs) are read from the whole repository and cited as context; *measured* files
   stay the diff. Ends cause #1 without new rules.
2. **`change-risk` dimension**, rated only at `changes`/`worktree` (abstains, with a reason, at
   `project`/`task` — so project scores stay byte-identical). Rules, by slice:
   - S1 `change_kind` gate + `bugfix_without_regression_test` / `new_code_without_test` (kind-dependent;
     chore → N/A, refactor → existing covering tests must still exist and none deleted).
   - S2 test-match gate (agent confirms pairs; deterministic symbol/name match fallback).
   - S3 reach: changed symbols → routes/handlers via `find_routes` + reference search, bounded and
     disclosed (no silent 400-file ceiling).
   - S4 missed co-change: files that changed together with the changed files in ≥ N of the last 200
     commits but are absent from this diff (`CO_CHANGE_WINDOW` reused).
   - S5 contract: move `public_symbols_removed` / `destructive_migration_ops` here (or reference them),
     plus API spec / schema changes without a version or changelog entry.
3. **Headline**: at `changes` scope, report `change_risk` as its own headline next to `overall`, and
   say plainly which dimensions abstained (cause #5).
**Pros**: Change risk is a first-class, explainable number; project scope untouched; slices ship
independently; reuses gates, agent-input replay, structure helpers and git history.
**Cons**: One more dimension, weights and report section; the 32-area coverage table gains rows.
**Why it might fail**: (a) Detection of kind is noisy on mixed PRs (fix + refactor) — needs a "mixed"
answer or the most demanding kind wins. (b) Agents rubber-stamp the proposal, so "confirmed" means
little — the deterministic proposal must be good on its own. (c) Symbol extraction across languages is
uneven; Python/TS first, others fall back to naming, disclosed. (d) Co-change on young repos (< 50
commits) is noise — abstain below a history floor.

### Option C — Change checklist, not a score
**Approach**: At `changes` scope, skip the overall; emit a checklist (kind, tests touched, deleted tests,
removed public symbols, co-change misses) as findings without a rating.
**Pros**: Honest by construction; tiny.
**Cons**: The user asked for scoring "as good as" the repo scoring; no number to gate a PR on; agents
cannot compare two changes.
**Why it might fail**: It is the abstention problem renamed — users will still read the old overall
from elsewhere and get 97.

---

## 50% Rule Check

Ship **S1 + the shared context fix** only: change-kind gate (detect + confirm) and one rule,
`changed_code_without_test` (bugfix/feature), using today's naming correspondence widened to tests
anywhere in the repo — no symbol extraction, no reach, no co-change. That alone moves the measured 97
case to a failing change-risk rating, ends the abstentions, and is roughly 40–50 % of B's code. S2–S5
follow only if real-repo runs show S1's naming fallback misses real tests.

---

## Selected Path

**User selected Option B, sliced (2026-10-16).**

## Recommended Path

**Option B — `change-risk` dimension + shared context fix, delivered as slices; S1 + context fix first
(the 50 % cut is the first milestone).**

It is the only option that turns "bugfix without a test" into a rated, explainable fact without touching
repository-health weights or project-scope scores, and every later signal (reach, co-change, contract)
has a home. Verification per slice on the real repos (node-monorepo, fullstack-ts, python-ml, …) with a
known bugfix-with-test and a bugfix-without-test commit each — pre-registered expectations before running.

---

## Surgical Scope

Files that **should** be touched (B, S1 + context fix):
- `src/easy_verifier/dimensions/change_risk.py` — new dimension
- `src/easy_verifier/dimensions/__init__.py` — register it
- `src/easy_verifier/core/gate.py` — `change_kind` (and later test-match) gate
- `src/easy_verifier/core/judge.py`, `core/metrics.py` — rules, weights, coverage floor, citations
- the 8 dimensions' role probe (`test_strategy.py:239`, `security.py:239`, `supply_chain.py:111`,
  `operations.py:189`, `infrastructure.py:192`, `api.py:200`, `data.py:156`, `reliability.py:144`) —
  context roles repo-wide at narrow scopes, ideally through one shared helper
- `src/easy_verifier/adapters/mcp_server.py` — emit the gate; `adapters/cli.py` — nothing beyond `--agent-input`
- `core/report.py`, `core/improve.py` — section + plan entries; README § Checking a feature or bugfix; PRD/SPEC

Files that **must not** be touched:
- `core/scope.py` resolution semantics (changes = diff files; never widen silently)
- project-scope rule tables and weights (byte-identical project payloads)
- `experiments/` (unrelated harness)

---

## Edge Case Checklist for TASK_GUIDE

- [ ] Project-scope payload byte-identical before/after on this repo + 3 real repos
- [ ] Mixed change (fix + refactor + docs): kind answer allows `mixed` or the most demanding kind applies — decided at grilling
- [ ] Unanswered gate: detected kind used, payload `source: "detected"`; CLI run without `--agent-input` gives the same result as MCP with no answer
- [ ] Agent answer outside the enum, or citing a ref not in the pack → rejected with a structured reason, detected value kept
- [ ] Deleted test in the diff (`_deleted_change_set_tests`) counts against a bugfix/refactor, never as "test touched"
- [ ] Test-only change, docs-only change, lockfile-only change → chore / N/A, not "code without test"
- [ ] Generated files, vendored/third-party paths (T087 exclusion) never count as changed code
- [ ] Rename-only diffs (git `R100`) are not new code
- [ ] Root commit / empty diff / clipped diff (`MAX_DIFF_CHARS`) disclosed, never silently rated
- [ ] Monorepo: a test in another package does not cover a change (`_project_boundary` reused)
- [ ] Replay: same diff + same agent input → byte-equal payload (FR-022)
- [ ] Narrow-scope overall can no longer exceed the project overall silently (cause #5 disclosed)
