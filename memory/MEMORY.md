# MEMORY.md — Hot-Tier Memory Index

> **Rules**: Supervisor-only writes. Max 50,000 characters — a ratchet: `/compact-memory` may lower
> it, never raise it to fit growth. One-line summaries + links to cold files.
> Passed to every sub-agent as a path to read; the contents are not pasted into the spawn prompt.
> Updated by the Supervisor — prompted by the PostToolUse hook on `git push` / `git merge` (diff-driven pass), or via the `/compact-memory` skill.

---

## Memory Architecture

- [decisions.md](decisions.md) — code + infra architectural decisions (the "why")
- [glossary.md](glossary.md) — canonical biz domain terms and core domain models
- [learnings.md](learnings.md) — specs/requirement clarifications, patterns, gotchas

---

## ▶ START HERE — handoff from the 2026-09-16 session

**State**: **20 of 22 tasks done.** T022 and T016 both closed this session, each with Stage 5
verification driven at a real surface. Post-merge: **570 tests, ruff clean.**

**Push state**: all of this session's work is **pushed** — `github/develop` is at `ec3b393`
(the merge resolving the parallel T016 fix), confirmed after the user ran the push. Only the commit
carrying this handoff may be outstanding; check with `git rev-list --left-right --count
github/develop...develop` and raise it only if the right-hand number is non-zero. The remote is
**`github`**, not `origin`, and the `git-guardrails` hook blocks `git push` from the Supervisor by
design — the user runs it as `! git push github develop`.

> Note for whoever writes here next: the same hook pattern-matches the literal string `git push`
> **inside heredoc text**, not just in an executed command, so a Bash call that merely *documents*
> that command is refused. Edit this file with the Write tool when the content mentions it.

**Only T017 remains, and it is now spawnable.** Its HITL gate closed today via **DDR-0005**: parity
is byte-equality after a closed three-rule normalization — paths repo-relative, timestamps one
fixed token, report filename excluded — with every other field compared byte-for-byte and no
tolerance. **Binding on the implementer: widening that list is a spec change, not a test fix; an
agent that finds a fourth difference stops and reports.** T017 is C2 / High Risk / P0, owned by
`qa-expert`, guide at `tasks/TASK_GUIDE_T017.md`, and mandates `security-review` at Stage 4. T022's
Stage 5 is the existence proof that the parity is reachable — the CLI and the MCP server returned
the same `overall` and the same rating/abstention sequence for identical arguments.

**What T016 turned out to be — read this before trusting any "blocked" status.** T016 sat open for
two weeks labelled "Docker unreachable / static tests pass". Docker became reachable today and the
container was correct all along. What was broken was `scripts/verify_container.sh`, in a way that
**could not fail**: it closed stdin, the MCP server dropped trailing responses, and
`for request_id in (3, 4)` raised `KeyError` before any pass/fail. The command had never once run to
completion. **PR #11 (`8e3c560`, 2026-09-12) fixed the stale tool count and still could not reach the
assertion** — a correct check added to a script that could not get to it, merged while Docker was
unreachable so nothing ran it. Three consecutive status updates described a container nothing had
verified. The generalizable form, now in `learnings.md`: **"blocked" was blocking *discovery*, not
merely verification, and a check that has always failed for a plausible reason is indistinguishable
from one that cannot pass.**

**The defect recurred inside its own fix**, which is the part worth remembering: the first
remediation made the timeout path print the entire expected id set instead of the missing one — a
harness that knew exactly which id had vanished and declined to say. Caught only by driving a
sabotaged copy, never by reading the diff. **The check that works: withhold one input deliberately
and confirm the harness fails naming that input.** Running the real thing and seeing PASS cannot
establish it, because the broken harness passed too.

**Open follow-up, highest value**: T022 residue (a) — `ScoreResult.to_dict()` emits no `scope` and
no `warnings`, so an unresolved `--scope task` reports a confident **overall 70** against a resolved
project run's **66**, because abstention drops low contributors out of the average. Honest in every
part, misleading in the headline; the ninth instance of that class and the first outside a single
pack. Closing it is a schema addition and needs its own task.

**New this session**: `.claude/skills/verify/SKILL.md` now exists and covers all four surfaces —
CLI, MCP over stdio, HTML report, and the container (including the FIFO trick for driving the
containerized server without losing the last response). Read it before any cold verification.


**Spawn-prompt additions earned so far — keep all four in every spawn:**
1. *"Commit your work before reporting ready-for-review."* (T003 reported done with zero commits.)
2. *"Before writing any file walk or path resolver, find the existing one and port its hardening."*
3. *"Implement the guide's prescribed Approach; if you intend to substitute a different design, say so
   before you build it, not in the completion report."*
4. *"Reproduce the reported defect before fixing it, and confirm your new test fails on the pre-fix
   commit."*

**A verification harness is code — pin it to both extremes too.** T016 (2026-09-16) is the eighth
instance of the green-test-that-cannot-fail class and the **first outside a test file**: the
container was correct for two weeks while `scripts/verify_container.sh` could never reach its own
final assertion (it closed stdin, the MCP server dropped trailing responses, `KeyError` before any
pass/fail). "Static tests pass" on the board meant nothing. A script that exits non-zero for a
plausible reason reads as a known failure rather than a broken check, which is exactly why it
survived where unit-test instances were caught. The check that works: **drive a sabotaged copy with
one input deliberately withheld and confirm it fails naming that input** — running the real thing
and seeing PASS cannot establish it, because the broken harness passed too. It then recurred inside
its own fix (the timeout named every id instead of the missing one). See `learnings.md`.

**Cheapest reliable check for this project's most persistent defect class**: hardwire the predicate a
test depends on to each of its extremes and re-run. A test that passes under both is pinning nothing.
That is how T018's P1(b) was caught, and it retroactively explains T005, T008 and T010.

**The miss-list defect class has now moved up a layer — this is the thing to watch.** Eight instances
so far, all one property: *the output is honest in its parts and misleading in its headline.* T022's
Stage 5 found the ninth and it is the first **outside** a single dimension's pack, so DDR-0004's
structural fix cannot reach it: `ScoreResult.to_dict()` emits no `scope` and no `warnings`, so a
`--scope task` run whose selector was never supplied reports a confident **overall 70** — *higher*
than a fully-resolved project run's **66**, because abstention drops low contributors out of the
average. Every miss reason names the unresolved scope and the panel says abstention can raise the
overall, so nothing lies. What is missing is **elevation**. Recorded as residue (a) in
`TASK_REVIEW_T022.md`; closing it is a schema addition and needs its own task.

**Review procedure — seven sessions have proved it out**: re-run a selection or ordering AC against
**a repo built to embarrass the implementation**, never the author's fixture. Cross-check
`sources_missing` against `files_read` and `excerpts` in the same pack, and ask what *bounded* the
search and whether the miss reason says so. **Now add: ask what the headline number omits, and
whether the payload says which scope produced it.**

**Stage 5 `verify` has now passed first-try twice (T010, T022) after failing T008 and T009.** Both
first-try passes happened because Stage 4 *ran the thing* rather than reading the diff. A clean
Stage 4 is still no evidence about Stage 5 unless Stage 4 actually drove the surface. `verify` is
user-invocation-only — the Supervisor cannot call it via the Skill tool and must hand back to the user.

**Tooling gotchas**:
- **The repo's checked-in `.venv` does not have the project installed** — `easy-verifier` is off
  PATH until `.venv/bin/python -m pip install -e .`. This blocks any cold verification; the recipe
  and the surface-driving commands are now captured in **`.claude/skills/verify/SKILL.md`**.
- **The shell here is zsh**: an unquoted `$VAR` holding several flags is *not* word-split. Write each
  invocation out in full.
- `score --scope project` runs **5–10 minutes printing nothing** and will blow a 120s tool timeout;
  background it, and do not run two at once (a concurrent second call was starved into a 600s timeout
  that did not reproduce alone). Use `--scope worktree` or `--scope task` for probes.
- The built-in `security-review` skill **cannot run in this repo** — it resolves the diff via
  `origin/HEAD` and the remote is named `github`. Review the diff surface directly and record the
  substitution in the evidence.
- The `pre_agent` hook warns that a task's Demonstration BEFORE field is blank by reading the
  **guide**, but since T064 that block lives in `tasks/TASK_REVIEW_Txxx.md`. Advisory only.

**Waiting on the user (do not proceed without a decision)**:
- ~~**T017 HITL gate**~~ — **CLOSED 2026-09-16 (DDR-0005)**: parity is byte-equality after a closed
  three-rule normalization (paths repo-relative, timestamps one fixed token, report filename
  excluded); everything else byte-for-byte, no tolerance. T017 is spawnable. **Binding**: widening
  that list is a spec change, not a test fix — an agent finding a fourth difference stops and reports.
- **T010 residue (d)** — under `project` scope `blast-radius` yields zero citable excerpts unless the
  repo declares an entry point, and in a non-git directory the pack is entirely empty.

**Open follow-up candidates (none scheduled)**: elevate scope/warnings into the `score` payload
(T022 residue (a) — the highest-value one); add `vendor` to `core/scope.py:_EXCLUDED_DIRS`;
`files_read` duplicated 2×; make `pipeline.py:60`'s "never widen on failure" invariant structural
rather than conventional; close T004's two detector floors; thread `secret_approval` through the
adapters so T008's HITL gate is operable; `--budget-bytes 0` traceback at the CLI; a manifest read
but declaring nothing is credited in `sources_found` and counts toward `coverage_score`; the
`[Errno 2]` repr leak on a missing `--findings` path.


**Standing traps — read `learnings.md` before verifying or merging**:
- Agent worktrees have **no `.venv`**; verify with the main checkout's interpreter and read pytest's
  **exit code directly** (piping through `tail` masks it, and did let a commit land on a red suite).
- The merge gate blocks while the board still shows the task **In Progress** — move it to Done and
  copy `TASK_REVIEW_Txxx.md` into the main checkout *before* merging.
- The gate's own error message recommends `CLAUDE_ACTIVE_TASK=`, which **cannot work** from inside a
  Bash call. Use the state file, written with `date -u`; a **future** timestamp is rejected as hard as
  a stale one. Clear it when the task finishes.
- **Never commit realistic credential shapes**, even in tests — assemble them at runtime.

---

## Index

<!-- Format: - [Title](cold-file.md#section) — one-line summary.
     Target ≤150 chars/entry. Advisory: reported by the size test, never enforced.
     The enforced gate is the 50,000-character whole-file budget above. -->

### Decisions

- ▶ **[T022 score operation merged](../tasks/TASK_REVIEW_T022.md)** (2026-09-12, PR #10, merge `94cdc65`). One `core.score` path composes combined evidence, metrics, ratings, overall disclosure, and optional assessments/divergences for both adapters. Full seven-dimension reports add a self-contained score panel; typed floor and failure abstentions remain visually distinct from numeric ratings and from each other. Final gates: 8 focused tests, 570 compatible full-suite tests, Ruff clean, and real CLI overall 65 from 77 cited metrics. T016's container verifier must now require the exact 11-tool surface, including `score`.
- ▶ **[T021 assessment merged](../tasks/TASK_REVIEW_T021.md)** (2026-09-12, PR #9, merge `a6ca3e6`). User approved optional finding severity with a disclosed declared `medium` default. Assessment starts at 100 and deducts declared severity penalties scaled by declared confidence percentages, rounding once and clamping at zero. Rating and assessment remain side by side; divergence carries both inputs, signed direction, and explicit absence provenance. Final gates: 18 focused assessment tests, 52 assessment/findings tests, 562 compatible full-suite tests, Ruff clean.
- ▶ **[T020 declared rating merged](../tasks/TASK_REVIEW_T020.md)** (recovered, reverified, and merged as an ancestor of PR #9 on 2026-09-12). Declared arithmetic ratings enforce inclusive coverage floors and typed abstention. Four adversarial review rounds closed seven P1 and four P2 boundary defects, including forged constructors, contradictory abstention provenance, malformed miss values, lying arithmetic methods, noncanonical serialization, and inconsistent coverage summaries. Recovery gates: 66 focused tests and 539 compatible full-suite tests passed; the project `.venv` still lacks `mcp`.
- ▶ **[Integration strategy](decisions.md): local merges, one task at a time** (user, 2026-08-15; base updated 2026-08-16). **`develop` is now the Stage 3 integration branch** — `plan/stage2-task-breakdown` was pushed and merged via PR #2 (`e185baa`), closing the old "unpushed base" blocker. Per-task scrutiny is Stage 4 + Stage 5, not the PR.
- ▶ **Stage 2 complete (2026-08-15).** `PROJECT_SPEC.md` + `PROJECT_KANBAN.md` + 17 TASK_GUIDEs exist; `PROJECT_KANBAN.md` is now the single source of in-flight state. `memory/NEXT-SESSION.md` deleted as designed. Stage 3 not started; no product code yet.
- [Codebase Map](codebase-map.md) — structural snapshot: directory tree, entry points, blast-radius hotspots. Refresh via /map-codebase.

- [Context-packer architecture](decisions.md) — engine performs no LLM inference; all reasoning comes from the calling agent (MCP main agent, or user's agent CLI).
- [Two adapters, one core](decisions.md) — `mcp_server.py` (FastMCP HTTP/SSE) + `cli.py` (repo path); thin adapters, identical output required.
- [Two-step report flow](decisions.md) — pack → caller reasons → `write_report` validates + renders HTML into target repo `reports/`.
- [T008: security dimension + HITL secret gate](decisions.md) — bespoke two-pass selection (declared probe, then category-ranked sweep); `request_secret_source` is the only door to secret-bearing files and defaults to refuse; a failed `resolve_scope` is **not** `project` scope.
- [A dimension must probe its own declared sources](decisions.md) — `pipeline._missing_sources` can only report reasons some read actually recorded; walk-only selection makes the whole miss list fiction.
- [T009: a declared source is a checklist label, not a path](decisions.md) — bare `SOURCES_SOUGHT` names resolved at repo root only, so a subdirectory config was cited and declared missing in the same pack; `_resolve_declared_source` falls back to a basename match inside the already-computed `scope_files`.
- [T010: blast-radius is textual, and says so](decisions.md) — reference search + git co-change + declared entry points, none parsing or running target code; `project` scope reports repository hotspots because references there are quadratic; `MAX_SCAN_FILES` bounds the tier-1 drain, not the byte budget.
- ⚠️ **[The miss-list defect class has now shipped seven times](learnings.md)** — T007/T008/T009/T010/T018 plus **T012 and T013** (2026-08-25). Standing review questions unchanged, and one added: **a sentinel with two possible causes is this defect in miniature.** `coverage_score is None` meant both "sought nothing" and "crashed"; the renderer had to invent a cause and picked the benign one, printing a crashed dimension as clean. Split the sentinel or carry the cause beside it — never let the display layer guess.
- 🔎 **[Render the document; don't just test it](learnings.md)** — T013's P1 was invisible to 39 tests, a diff review, and the seam contract built to prevent it. Headless Chromium with `--host-resolver-rules="MAP * ~NOTFOUND"` proves FR-018 self-containment *and* gives you a page to read. Snap Chromium can't write into `/tmp/claude-1000` or dotted `$HOME` dirs.
- 🔐 **[A new egress path invalidates upstream redaction](learnings.md)** — excerpts are redacted at the evidence layer; T013's finding *prose* inherited nothing, so a secret the agent quoted landed verbatim in a file written into the target repo. Re-ask the redaction question at every new boundary; `_Ctx.agent_text()` (redact → escape) is the fix shape.
- 🐚 **[zsh does not word-split unquoted variables](learnings.md)** — a CLI probe in a `for` loop reported a phantom argparse error. Use explicit args or arrays.
- 🔒 **[DDR-0005: adapter parity is byte-equality after a declared normalization](decisions.md)** (2026-09-16) — user decision closing PRD open item #15 and the T017 gate. FR-022 said "identical" and the KPI said "byte-equal"; neither was testable, since the container mounts at `/workspace` and FR-018b makes report filenames unique by design. Parity is now byte-equality after exactly three normalizations — paths repo-relative, timestamps one fixed token, report filename excluded — with every other field compared byte-for-byte. The rejected alternative ("semantically identical", field by field) was refused because it hides *which* differences the comparator tolerates, this project's signature defect shape. **Widening the list is a spec change, not a test fix.**
- 🔒 **[DDR-0004: the T012/T013 seam contract is Supervisor-locked](decisions.md)** (2026-08-25) — the user chose to run T012 and T013 **in parallel** over the Supervisor's recommendation to sequence them, so `CombinedPack`/`CoverageSummary`/`DimensionSlot` are fixed at Stage 2 authority and handed identically to both spawns. T012 implements them in `models.py`; T013 imports and never redefines them. `misses` lives **inside** `CoverageSummary` so FR-016a is structural — a renderer cannot reach a score without its miss list. Budget model is **per-dimension** (user decision), carried on the pack as `budget_model` so a future total-budget regime is a value change, not a schema change. Either agent that thinks the contract is wrong **stops and reports before building**.
- ⚠️ **[The miss-list defect class has shipped four times](learnings.md)** — T007 false secret reasons, T008 a wholly fabricated list, T009 the inverse (read happened, miss list denied it), T010 a cap-truncated sweep asserting a repo-wide zero. Standing review questions: cross-check `sources_missing` against `files_read`/`excerpts`, **and ask what bounded the search and whether the miss reason says so**.
- [Route declared-source probes through `read_source`](learnings.md) — it records found/missing itself; that is why T010 is the first dimension not to ship the miss-list contradiction. Structural, not vigilance.
- ⚠️ **[The `pre_agent` Demonstration-BEFORE warning is a false positive](learnings.md)** — it reads the guide, but since T064 the block lives in `TASK_REVIEW_Txxx.md`. Fires on every correct task.
- [T008 test blind spots](learnings.md) — interchangeable cap fixtures, unasserted miss *reasons*, and bogus-vs-missing CLI selectors: three green-suite defects, one caught only by Stage 5 `verify`.
- [Redact secrets at evidence layer](decisions.md) — secret values fingerprinted before leaving the engine; never reach agent, report, or log. → see DDR-0001
- ▶ **[DDR-0002: never read secret-bearing files](decisions.md)** (user, 2026-08-16). `.env*`/`*.pem`/`*.key`/`id_rsa`/… excluded at `read_source()`; existence reported as `excluded: secret-bearing`, contents withheld. T008 gets a per-file HITL gate defaulting to refuse. **Complements, does not replace, DDR-0001** — a live-key-shaped token in a `README.md` proved exclusion alone is insufficient. Landed as Spec Constraint 4a + AC rows on T007/T008/T013 before pickup.
- ⚠️ **Never put a real vendor prefix in a test fixture** (`sk_live_`, `ghp_`, `xoxb-`). Scanners match on shape and cannot tell a fake from a real key — GitHub push protection rejected a push over T004's fixtures. Detectors match on `key=value` shape and character mix, never the prefix, so synthetic values test the same path. Convention: spell the fakeness in, as `FAKEfake…`.
- [Coverage score = auditable checklist ratio](decisions.md) — unweighted found/sought, never rendered without the miss list.
- [Docker in v1](decisions.md) — user override of supervisor's defer-to-v1.1 recommendation.
- [Evidence packs: 120 KB relevance-ordered budget](decisions.md) — byte-measured for determinism; explicit truncation field.
- [Dimension structure = pipeline fn + descriptors](decisions.md) — Option D; cross-cutting rules unbypassable; `collect` lazily iterable. See BRAINSTORMING_LOG.md.
- [Shared extraction helper for doc-shaped dimensions only](decisions.md) — 4 share a helper; security/test-strategy/blast-radius stay bespoke.
- [Local-only, stdio-first transport](decisions.md) — harness connects via local Docker, never the internet; HTTP/SSE opt-in and loopback-bound. Corrects inherited HTTP/SSE assumption.
- [Synthesis = engine aggregates, caller interprets](decisions.md) — recovers REQUIREMENT.md §4's missing synthesis layer without putting reasoning in the engine.
- [T001 is a tracer bullet, not a scaffold](decisions.md) — the pipeline contract lands as a working end-to-end path (repo in, real pack out) rather than an abstract signature; T004 fills the redaction seam it ships.
- [Extract the doc helper last, not first](decisions.md) — T007 builds three dimensions duplicatively, then factors out what the four actually share. Deliberate correction: Option A died from a premature shared abstraction.
- [Redaction fingerprint is unsalted](decisions.md) — SHA-256, 12-hex prefix, 4-char mask. Closes gap #14. Correlation beats dictionary resistance **because reports stay inside the evaluated repo**; revisit if that ever changes.
- [One HITL gate still open into Stage 3](decisions.md) — T017 FR-022 parity definition (gap #15): "identical" vs. "byte-equal". Recorded in PROJECT_KANBAN.md's Blocked table.
- ▶ **[T001 shipped — the `run_dimension()` contract is fixed](decisions.md)** (merged 2026-08-15). Signatures locked; 16 tasks written against it. File reading lives in `ctx.read_source()`, not the dimension. `sources_found` is clamped to `sources_sought` so the two partition it exactly; unprobed sources report `not examined`, never `not found`.
- ▶ **[T004 shipped — redaction is real](decisions.md)** (merged 2026-08-16, `1acfa5c`). Layered detectors: named patterns → entropy → per-segment key material, the last being what makes paths and URI passwords safe while keeping paths readable. **Two misses accepted, not fixed**: a credential assignment whose value is followed by trailing prose with no comment marker, and single-char-class tokens of 12–31 chars. Both anchors exist so the tool stays usable evaluating its own repo. T013 unblocked.
- ▶ **[T002, T006 and T003 merged](decisions.md)** (2026-08-16). `develop`: **198 tests**, ruff clean, **5/17 tasks done**. T003 = `resolve_scope()`, four scope kinds, read-only git only.
- ▶ **[T005 merged — Wave 1 complete](decisions.md)** (2026-08-17, `cd7bb57`). `develop`: **224 tests**, ruff clean, **6/17 done**. `budget(collect, scope, limit_bytes)` — `collect` is a **zero-arg callable**, invoked once per non-empty tier (≤3 passes). `resolve_scope` finally wired into `run_dimension`, closing T003's waived debt; `changes`/`task` still tier as `None` there.
- ⚠️ **[Sabotage is how you tell a passing test from one that cannot fail](learnings.md)** — hardwire the predicate to both extremes; T018's planned-blocks test passed under both. Fifth instance after T005, T008, T010.
- [Pinning docs: fenced commands are checkable, prose is not](learnings.md) — a doc-truth test pins syntax and exit codes, never claims; `shlex.split` with no shell cannot validate `$(pwd)`/pipes/`&&`; a "planned" marker hides a genuinely broken command by construction.
- ▶ **[T018 merged — the repo has a README](decisions.md)** (2026-08-25, `ee12ad6`). `develop`: **339 tests**, ruff clean, **11 of 18 done**. Documents the full intended v1 surface with every command either runnable-today or explicitly marked planned, both halves test-enforced.
- ▶ **[T010 merged — Wave 2 complete](decisions.md)** (2026-08-25, `3e8b573`). `develop`: **333 tests**, ruff clean, **10 of 17 done**. All seven FR-010 dimensions wired. First task to pass Stage 5 `verify` on the first attempt; its Stage 4 P1 (cap-truncated sweep reporting a repo-wide zero) was found by a fixture built to embarrass the implementation.
- ▶ **[T007 doc dimensions complete](decisions.md)** — shared extraction serves exactly four dimensions; kit declarations and task-guide globs are direct candidates, while standalone uses discovered docs then bounded code fallback. Secret exclusion checks resolved targets.
- ✅ **[Tier-2 narrowing revisited](decisions.md)** — no `budget.py` change: source selection makes kit artifacts candidates without forcing a permanent second relevance pass on every call.
- ⚠️ **[A test can pass *because of* the defect's exact shape](learnings.md)** — T005's AC test used a tier-3 prefix exactly short enough for its one-eviction bug to look like tiering; one more excerpt and the pack held zero changed files. Re-run ordering/selection ACs with adversarial numbers, never the author's fixture. An honestly flagged deviation is a pointer to test harder, not sign-off.
- ⚠️ **[A mode test must require mode-specific positive evidence](learnings.md)** — T007's standalone test passed with four empty packs. Pin both branches: docs prevent fallback, and docs-silent input requires a real source excerpt. Resolve paths before secret classification so safe-name aliases cannot expose `.env`.
- ▶ **[A guide's "Files to Change" table is a prediction, not a contract](decisions.md)** — T003 skipped its predicted `models.py`/`pipeline.py`/`cli.py` edits, flagged it, and was waived: the **Acceptance Criteria** are the contract. Judge deviations against ACs, not the file table. Cost: `resolve_scope` unreachable until T005.
- ⚠️ **[A new module re-implementing a traversal re-inherits old bugs](learnings.md)** — T003's `scope.py` rewrote a file walk and reproduced the exact symlink-escape T002 had already fixed in `context.py:_walk`. Canonical containment test is `path.resolve().is_relative_to(repo.resolve())`, on entry **and** for symlinked files; it now lives in two places that must not drift. Check T007/T008 for the same.
- ⚠️ **[Agents may report "ready for review" with zero commits](learnings.md)** — T003 did. Always check `git log develop..HEAD` and `git status` in the worktree before trusting the report.
- ⚠️ **[Agent worktrees have no `.venv`](learnings.md)** — `PATH=.venv/bin:$PATH python` there silently falls back to system python and fails the T001 CLI tests. Use the main checkout's interpreter with `PYTHONPATH=src`, and check pytest's exit code directly (piping through `tail` masks it).
- ⚠️ **[A merge of two green branches can be a regression](learnings.md)** — T002 moved the path check that T004 had hardened with redaction; both suites passed alone, the leak existed only in the combination. **After every conflict resolution, re-probe any cross-cutting property (redaction/validation/auth/logging) that attached to a line the other branch relocated.**
- [Truncation is rejection-triggered; `omitted_count` is a lower bound](decisions.md) — pull until one item doesn't fit, drop it, stop. Never drain to count: for a file-reading `collect` that means reading every file. Fixes a T001 guide contradiction; aligns T001 with T005.
- [T012 budget recommendation: per-dimension, not pooled](decisions.md) — a total budget split across dimensions makes each pack's contents depend on what else was requested, breaking reproducibility. Decision to be recorded when T012 is picked up.
- ▶ **[The verifier now emits a quality *rating*; FR-013 amended](decisions.md)** — engine-computed numbers are allowed when produced by **declared rules over measured metrics** (never a model, NFR-001 intact). Three words, never interchangeable: `coverage_score` = what we READ, **rating** = what our RULES compute, **assessment** = what the AGENT concluded, **divergence** = the gap, reported never reconciled. **Below a declared coverage floor the engine emits NO number** — a structured abstention, never `0`/`None`/a low rating → see DDR-0003. Wave 7 = T019–T022; T022 must follow T014/T015.

### Gotchas (see [learnings.md](learnings.md))

- ⚠️ **Stage 3 worktrees are created off the root commit** — an agent's worktree may contain only `LICENSE`+`README.md`. Every spawn prompt must order the agent to verify `PROJECT_SPEC.md` + its own guide are present and rebase onto the planning branch if not.
- ✅ **Trace state file unwritable from an isolated worktree — RESOLVED, no hook change.** It *is* writable from the main checkout. Standing Stage 5 procedure: Supervisor writes `.claude/hooks/.state/active_task` then runs the guide's Verification Command itself before merging. Not a bypass — it is the independent re-run Stage 5 already requires. Details in [learnings.md](learnings.md).
- **Guardrail hook matches command *mentions*** — a commit message or memory file containing `git push` blocks the whole Bash call. Use Write/Edit or `git commit -F`.
- ⚠️ **Merge gate: two traps, both hit on T001.** (a) Stage 5 evidence must be `git checkout <task-branch> -- tasks/TASK_REVIEW_Txxx.md` into the main checkout *before* merging — the gate reads the pre-merge copy. (b) The verification command must put the runner at a command boundary within 300 chars: `cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/... -q`. An interpreter path prefix (`.venv/bin/python -m pytest`) never matches.
- **The `active_task` state file also feeds the step-limit hook** — Supervisor Bash calls count toward the named task's 90-call budget and will be killed once (auto-resets). Not an agent loop.
- ⚠️ **[`active_task` rejects a FUTURE timestamp as hard as a stale one](learnings.md)** — `age_s < 0` fails too. Always write it with `$(date -u '+%Y-%m-%dT%H:%M:%SZ')`, never a hand-guessed clock time, or the trace silently goes nowhere.
- ⚠️ **[The merge gate's own error hint is dead advice](learnings.md)** — it tells you to prefix `CLAUDE_ACTIVE_TASK=Txxx`, but that channel cannot work from inside a Bash call (hooks are siblings, not children). Use the state file.

### Learning Records

_None yet._
