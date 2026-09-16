# TASK_REVIEW — T022: shared score operation and report panel

## Evidence

| Check | Result | Notes / output snippet |
|---|---|---|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | Pass | `tests/test_score_operation.py` contains 8 tests covering no-findings CLI scoring, all-abstained exit 0, CLI/MCP parity, findings file/stdin, assessments/divergences, numeric and abstaining report states, failed-dimension escaping, self-containment, path scrubbing, and structural adapter thinness. |
| Verification command run | Pass with environment substitution | The isolated clone has no `.venv`; `PYTHONPATH=src <compatible-venv>/bin/python -m pytest tests/test_score_operation.py -q` → **8 passed, 1 upstream warning in 0.76s**. |
| Negative cases hold | Pass | A deliberately empty standalone repo returns seven typed `rating_abstention` objects, no numeric `value` on any of them, an overall `no_dimension_rated` abstention, and exit 0. A fabricated collector failure renders as `dimension_failed`, is styled separately from a floor abstention, and escapes injected HTML. |
| verify | Pass via real CLI substitution | `score --repo . --scope project` at the real CLI exited 0 and returned seven numeric ratings, **77 cited metrics**, overall **65**, and disclosure `7 of 7 dimensions contributed ... none abstained`. The named `verify` skill is unavailable in this Codex session. |
| Review scope bounded to the change's blast radius | Pass | Reviewed the new core composition boundary, CLI/MCP registrations, report renderer and path/redaction chokepoints, changed tool-count assertions, README contract, and T013–T015/T018 compatibility. T019/T020/T021 arithmetic modules were not changed. Manual P0–P3 result: P0 0 / P1 0 / P2 0. The named `code-review` skill is unavailable in this Codex session. |
| Full smoke suite still green (no regression) | Pass | `PYTHONPATH=src <compatible-venv>/bin/python -m pytest -q` → **570 passed, 1 upstream Pydantic warning in 11.14s**. Ruff check passed, Ruff format passed, and `git diff --check` is clean. |
| **UI: Visual regression (diff or verdict pasted)** | N/A | No interactive UI exists (PROJECT_SPEC Constraint 11). The static HTML report is covered by parsed-document assertions and a generated all-abstained artifact; sandboxed Snap Chromium could not start because `/run/user/1000` is read-only. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | No design system or UI surface; the report extends the existing self-contained inline CSS and adds no dependency. |
| **UI: Responsiveness at target viewports** | N/A | No application UI. The static report retains its viewport metadata and uses an auto-fit score grid; structural report tests pass. |

## Security review

N/A by task risk policy (Low). Direct substitution found no new filesystem, subprocess, network,
model-client, or outbound-request primitive. Findings still pass through `validate_findings`,
caller-authored prose through `_Ctx.agent_text`, metric paths through `_Ctx.path`, and failures
through `_Ctx.esc`. The score core delegates all reads to the pre-existing combined-pack pipeline.

## Demonstration

**BEFORE (2026-09-12):** focused test collection failed with
`ModuleNotFoundError: No module named 'easy_verifier.core.score'`; neither adapter registered a
`score` operation and reports had no quality panel.

**AFTER (2026-09-12):** the real CLI returned exit 0 with seven ratings, 77 cited metrics, overall
65, and its contributor/abstention disclosure. The same payload is returned by MCP; optional
findings add separate assessments and divergences; a report renders these signals without external
resources or container paths.

**DELTA:** an operator can now point either adapter at a repository and receive the complete,
inspectable quality result without an agent or findings, while reports render the same declared
signals.

**WITNESS:** Codex Supervisor, 2026-09-12, using the isolated `feat/t022-score` checkout and a
compatible provisioned Python environment.

## Review findings and remediation

| Severity | Finding | Remediation |
|---|---|---|
| P1 | The first renderer branch identified a numeric overall through an attribute that only the abstention type has, so a real numeric result would raise `AttributeError`. | Replaced attribute probing with exact typed branches and added a numeric-overall report regression test. |
| P1 | A failed dimension initially shared the same visual class as a below-floor abstention, leaving two distinct absence causes differentiated only by prose. | Added the validated reason code to the card class, a red failure treatment, and an escaped hostile-failure regression test. |
| P2 | `README.md` still claimed that the approved engine never returns a score. | Reframed the promise as no inferred verdict, documented declared ratings/assessments/divergence, and added the runnable score command to the existing doc-truth gate. |

Post-remediation result: P0 0 / P1 0 / P2 0.

## Stage 5 verification (Supervisor, 2026-09-16)

Run on `develop` at `94cdc65` (post-merge), not in the implementer's worktree — the first
independent run of T022 at the real surfaces after integration. Cold start: the repo's `.venv` did
not have the project installed, so `easy-verifier` was not on PATH until `.venv/bin/python -m pip
install -e .`. The recipe is now persisted at `.claude/skills/verify/SKILL.md` so the next session
skips this.

**Verdict: PASS.**

| Surface | Driven | Observed |
|---|---|---|
| CLI | `easy-verifier score --repo . --scope project` | exit 0; 125 KB payload; 7 ratings, 77 metrics, `overall.value 66`, 7/7 contributors |
| CLI + findings | `… --findings f.json` (2 architecture findings) | payload gains `assessments` + `divergences`; architecture rating 82 vs assessment 69, `signed_gap -13`, `direction agent_harsher` — reported side by side, never blended |
| MCP | `stdio_client` → `call_tool("score", {"repo":".","scope":"task"})` | tool list includes `score`; `overall 70` and the identical `rating`/`rating_abstention` kind sequence as the CLI at the same arguments — **FR-022 parity holds on this pair** |
| Report | `write-report --scope task --findings f.json` | `<h2>Quality score</h2>` panel renders overall 70/100, the "abstention can raise the overall" disclosure, per-rule arithmetic with `computed_from` refs, unavailable-metric reasons, `Rating withheld — below_coverage_floor · Declared floor: 25.0% · achieved: 0.0%` with full miss lists, and `Assessment 70/100 · Divergence -12 (agent_harsher)` |

Note: the Demonstration block above records overall **65** from the implementer's 2026-09-12
worktree; this run observed **66** on `develop`. The difference is repository drift between the two
commits, not a scoring change — the operation is deterministic for a fixed tree.

**Probes driven at the surface (all held):**

- `write-report < /dev/null` → unchanged `validation error … malformed JSON`, exit 2. The
  `_read_findings(required=False)` refactor did **not** loosen `write-report`; this was the main
  regression risk in the diff.
- `score < /dev/null` → exit 0, full score. Empty stdin correctly reads as "no findings".
- Malformed findings → `finding[-1] (None) [<payload>]: malformed JSON at line 1, column 1`;
  unknown field → `finding[0] ('x') [<unknown>]: unknown field(s): bogus`. Both exit 2, both name
  the offender.
- `--repo /nonexistent` → exit **3 from both `score` and a single dimension**; no exit-code
  divergence between operations.
- `--scope task` with no `--task` → exit 0, matching the single-dimension path. Three dimensions
  abstain and every miss reason reads `not examined: the task scope could not be resolved (its
  required selector was not supplied)` — **T008's widening class does not reproduce** in the
  abstention layer.
- `--budget-bytes 0`, `--findings` passed twice, `--findings /dev/null` → no traceback; last flag
  wins; empty file rejected as malformed JSON.

## Open residue (recorded, not fixed)

(a) **The `score` payload never states what scope produced it, or that the scope failed.**
`ScoreResult.to_dict()` emits only `ratings` / `overall` / `metrics` — no `scope`, no `warnings`.
Under `--scope task` with no `--task`, `architecture` still rates **82** (it reads repo-root docs,
which is mode-driven rather than scope-driven) while three siblings abstain citing the unresolved
scope, and the run reports a confident **overall 70** — *higher* than the fully-resolved
`--scope project` run's **66**, because abstention removes low contributors from the average. The
truth is present in every miss reason and in the panel's own "abstention can raise the overall"
line, so nothing here is a lie; what is missing is elevation. This is **this project's recurring
miss-list defect class moved one layer up**: honest in the parts, misleading in the headline. The
prior seven instances were all inside a single dimension's pack, where DDR-0004's structural fix
reaches; a composition layer that re-publishes those packs as one number is outside that fix's
scope. The obvious closure is a `scope` block on the payload carrying the resolved kind, its
selector, and any pipeline warnings — a schema addition, so it needs its own task rather than a
review-stage patch.

(b) **`score --scope project` takes 5–10 minutes and prints nothing until it finishes.** No
progress output on a seven-dimension gather. It had to be backgrounded to survive a 120s tool
timeout, and a concurrent second invocation was starved into a 600s timeout that did not reproduce
when run alone. This is friction in the operation most likely to be a user's first command.

(c) **`--findings` on a missing path leaks a raw errno**: `operational error: [Errno 2] No such
file or directory: '/…/nope.json'` (exit 3). Every other error at this surface is phrased for the
operator (`target repository path does not exist: …`); this one exposes the exception's `repr`.
Cosmetic, but it is the error a user is most likely to reach by typo.

(d) `--findings /dev/null` (an empty **file**) reports `malformed JSON at line 1, column 1`, while
*omitting* `--findings` entirely is accepted. Passing an empty file is the likelier accident and
gets the less helpful message.

(e) Environment, not T022: the checked-in `.venv` does not have the project installed, so
`easy-verifier` is absent from PATH until `pip install -e .`. It blocks any cold verification.

(f) Pre-existing T009/T010 residue, newly visible as an asymmetry: `files_read` duplicates 2× on
`architecture --scope task --task T022` (6 entries for 3 files) but **not** on the same command
without `--task` (3 entries).
