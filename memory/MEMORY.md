# MEMORY.md — Hot-Tier Memory Index

> **Rules**: Supervisor-only writes. Max 32,000 characters (lowered from 50,000 on 2026-10-16) — a ratchet: `/compact-memory` may lower
> it, never raise it to fit growth. One-line summaries + links to cold files.
> Passed to every sub-agent as a path to read; the contents are not pasted into the spawn prompt.
> Updated by the Supervisor — prompted by the PostToolUse hook on `git push` / `git merge` (diff-driven pass), or via the `/compact-memory` skill.

---

## Memory Architecture

- [decisions.md](decisions.md) — code + infra architectural decisions (the "why")
- [glossary.md](glossary.md) — canonical biz domain terms and core domain models
- [learnings.md](learnings.md) — specs/requirement clarifications, patterns, gotchas

---

## ▶ Standing rules (compacted 2026-10-16; the 2026-09-16 handoff is archived verbatim at the end of [learnings.md](learnings.md))

**Push**: remote is **`github`**, not `origin`; the git-guardrails hook blocks `git push` from the
Supervisor — the user runs `! git push github <branch>`. The hook also matches that literal string
inside heredoc/script text, so write files that mention it with the Write tool.

**Spawn-prompt additions — keep all four in every spawn:**
1. *"Commit your work before reporting ready-for-review."*
2. *"Before writing any file walk or path resolver, find the existing one and port its hardening."*
3. *"Implement the guide's prescribed Approach; if you intend to substitute a different design, say so
   before you build it, not in the completion report."*
4. *"Reproduce the reported defect before fixing it, and confirm your new test fails on the pre-fix
   commit."*

**Tooling traps** (details in [learnings.md](learnings.md)): `.venv` is broken (system Python 3.14) —
use a py3.12 venv; shell is zsh (an unquoted `$VAR` of flags is not word-split); `score --scope project`
runs minutes silently — background it, never two at once; built-in `security-review` cannot run here
(resolves `origin/HEAD`) — review the diff directly and say so; read pytest's exit code directly (a
`| tail` masks it); a harness is verified only by a sabotaged copy that fails naming the withheld
input; **never commit realistic credential shapes** — assemble them at runtime. Cold verification:
`.claude/skills/verify/SKILL.md`.

---

## Index

<!-- Format: - [Title](cold-file.md#section) — one-line summary.
     Target ≤150 chars/entry. Advisory: reported by the size test, never enforced.
     The enforced gate is the 32,000-character whole-file budget above. -->

### Decisions
- ▶ **[T107 merged: context roles repo-wide at narrow scopes (2026-10-16)](learnings.md)** — FR-078; project byte-equal on 4 repos; 97→85 on the node-monorepo bugfix; clear active_task after each agent
- 🔒 **[DDR-0014 change-risk (2026-10-16)](decisions.md)** — separate `change_risk` headline; engine detects kind, agent confirms; slice 1 merged (T107 context roles, T108 dimension, T109 kind gate, T110 kind rules); S2–S5 backlog
- 🔬 **[T106 Kev zero-shot rejected (2026-10-16)](decisions.md)** — `--model kev` → own `kev.serve` (`KEV_BASE_URL`); Kev-0.8B 0.625 top-1 / p50 1.65 s, below the free heuristic; reopen only with kev.train + GPU
- 🔬 **[T104 Laya verdict: not yet — CPU latency (2026-10-16)](decisions.md)** — fine-tuned Laya 11/11 on a 3-fold sample vs LLM 0.946/56, but p50 343–808 ms vs ≤200 ms bar; T105 judge stays gated; harness `experiments/t104_laya`
- 🔒 **[Shared container is the primary documented path (T103, 2026-10-15)](decisions.md)** — PRD/spec/guides amended; stdio = supported alternative + bare-command default; no code changed. `.venv` is broken (system py 3.14): use a py3.12 venv.

- ▶ **Wave 16 business-domain coverage** (2026-10-06): **T082 merged `3153741`** — payload `areas_measured` / `areas_without_rule` (derived from rule tables) + disclosure "measured N of 32 evaluation areas" + report folded list … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ▶ **[DDR-0011 code-derived rules](decisions.md)** (2026-10-04, branch `plan/code-derived-rules`; **T073 merged `0581446`**: `core/structure.py` layer_of/find_routes/find_requirement_items/find_issue_references … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ▶ **T081 change-check guide merged `6bf651e`** (2026-10-05, local develop): README § Checking a feature or bugfix + DOCKER_MCP_GUIDE § 5 (`--ref main...HEAD < /dev/null`). Change score is partial (node-monorepo no-test bugfix = … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ▶ **T080 evaluation guide refresh merged `b263b00`** (2026-10-05): guide now matches DDR-0011 (requirement-fidelity code rules, missing document = failed rule); worked examples re-run (nest-api 65 over 4 dims, node-monorepo 69). Rule changes must re-check EVALUATION_GUIDE (see learnings.md 2026-10-05). node-monorepo git repo = `<real-repos>/node-monorepo`.

- ▶ **T071 evaluation guide merged `5b9dd7c`** (2026-10-04, FR-066): `docs/EVALUATION_GUIDE.md` (force-added) is the single reader's map for a score/report; README 'Reading a report'; SCORING_FLOW 'Evidence warnings' + 'Acting on the plan'. A doc test pins every backticked identifier to src/. Note: false secret matches *lower* security (fail redaction_hits_observed), not inflate it.

- ▶ **T070 readable report merged `88c883d`** (2026-10-04, FR-065): order share-notice(folded) → summary(+evidence status) → plan cards (P0/P1 open, P2 folded, top 3 highlighted) → 'What we couldn't measure' (merged warnings) → … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ▶ **T069 report summary merged `de6927f`** (2026-10-04, FR-063/064, user chose B): report opens with an engine summary (N of 7 rated, top 3 P0/P1 with gain + first cited standard, plain could-not-evaluate lines via … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ▶ **[DDR-0010 evidence floor + priority batches](decisions.md)** (2026-10-03; **T067 merged `2bf07ff`**: `judge.MEASURED_WEIGHT_FLOOR`, `EVIDENCE_LACK_REASONS`, gate refuses evidence-lack evaluations, `warnings` in score … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ▶ **[DDR-0009 improvement plan](decisions.md)** (2026-10-03; **T065 merged `71ed3bf`**: `core/improve.py`, `judge.rating_value`/`overall_value` shared arithmetic, `ScoreResult.improvement_plan` property; 1631 passed; **T066 … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ⚠️ **[Kanban gets duplicate rows when guides are committed](learnings.md)** — a row for each new TASK_GUIDE appeared at the top of Todo beside the Supervisor's own wave rows (T065/T066). Grep the board for the ID before moving a task.
- 🔎 **[Headless Chrome's minimum window width is 500px](learnings.md)**: a "400px" screenshot is a cropped 500px layout; use a 400px iframe for a true mobile viewport. `overflow-wrap:anywhere` in a table cell collapses the column; use `break-word`.
- ⚠️ **Container tests fail on a stale local Docker image** (`unexpected=['supply-chain']`): `test_container_parity_is_explicitly_verified` fails on clean `develop` too. Not a regression; rebuild the image to clear it.

- ▶ **[T055 git-evidence areas merged](decisions.md)** (2026-09-29, merge `309e26e`). blast-radius #5: public_symbols_removed and destructive_migration_ops, from the changes-scope diff only, abstaining elsewhere. … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ▶ **[T040 area rules merged](decisions.md)** (2026-09-29, merge `15bca51`). test-strategy gains tests_without_assertions_share/skipped_test_share/network_calls_in_unit_tests_observed; code-quality gains type_escapes_per_kloc … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ⚠️ **[Excerpts clip at 200 lines](learnings.md)**: a per-test metric must not judge the last test of a clipped excerpt (`metrics.excerpt_clipped`). This is a miss-list relative.
- ▶ **[T039 doc rule + areas merged](decisions.md)** (2026-09-29, merge `126471e`). Every rating rule and input carries one of the user's 32 `AREAS` (`judge.AREAS`, verbatim), and the report groups by area. … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ⚠️ **The `pre_agent_step_limit` hook counts the Supervisor's own calls** attributed through `active_task`: 90 calls on one task kills the next call (the counter then resets). Point `active_task` elsewhere once the agent is done.
- ▶ **[T038 review gate merged](decisions.md)** (2026-09-29, merge `89a15f2`). Each local registry entry is shown to the user once through `needs_input.review` (MCP only). good approves it and retags agent-researched entries … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- 🔎 **[`json.dumps` is not a TOML encoder](learnings.md)**: its surrogate-pair escapes make TOML unparseable, so one emoji destroyed a local-registry file. Use `ensure_ascii=False`, escape DEL, and refuse lone surrogates.
- 🐚 **[CLI `score` hangs on an open stdin pipe](learnings.md)**: always use `</dev/null` in agent Bash calls.
- ⚠️ **The merge hook reads the MAIN checkout's KANBAN and `tasks/`**: any In Progress row blocks every merge and rebase. A task waiting on another's merge goes in the Blocked table, not In Progress.

- ▶ **[T022 score operation merged](../tasks/TASK_REVIEW_T022.md)** (2026-09-12, PR #10, merge `94cdc65`). One `core.score` path composes combined evidence, metrics, ratings, overall disclosure, and optional … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ▶ **[T021 assessment merged](../tasks/TASK_REVIEW_T021.md)** (2026-09-12, PR #9, merge `a6ca3e6`). User approved optional finding severity with a disclosed declared `medium` default. Assessment starts at 100 and deducts … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ▶ **[T020 declared rating merged](../tasks/TASK_REVIEW_T020.md)** (recovered, reverified, and merged as an ancestor of PR #9 on 2026-09-12). Declared arithmetic ratings enforce inclusive coverage floors and typed abstention. … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
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
- ⚠️ **[The miss-list defect class has now shipped seven times](learnings.md)** — T007/T008/T009/T010/T018 plus **T012 and T013** (2026-08-25). Standing review questions unchanged, and one added: **a sentinel with two possible … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- 🔎 **[Render the document; don't just test it](learnings.md)** — T013's P1 was invisible to 39 tests, a diff review, and the seam contract built to prevent it. Headless Chromium with `--host-resolver-rules="MAP * ~NOTFOUND"` proves FR-018 self-containment *and* gives you a page to read. Snap Chromium can't write into `/tmp/claude-1000` or dotted `$HOME` dirs.
- 🔐 **[A new egress path invalidates upstream redaction](learnings.md)** — excerpts are redacted at the evidence layer; T013's finding *prose* inherited nothing, so a secret the agent quoted landed verbatim in a file written into the target repo. Re-ask the redaction question at every new boundary; `_Ctx.agent_text()` (redact → escape) is the fix shape.
- 🐚 **[zsh does not word-split unquoted variables](learnings.md)** — a CLI probe in a `for` loop reported a phantom argparse error. Use explicit args or arrays.
- 🔒 **[DDR-0005: adapter parity is byte-equality after a declared normalization](decisions.md)** (2026-09-16) — user decision closing PRD open item #15 and the T017 gate. FR-022 said "identical" and the KPI said "byte-equal" … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- 🔒 **[DDR-0004: the T012/T013 seam contract is Supervisor-locked](decisions.md)** (2026-08-25) — the user chose to run T012 and T013 **in parallel** over the Supervisor's recommendation to sequence them, so … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- [Route declared-source probes through `read_source`](learnings.md) — it records found/missing itself; that is why T010 is the first dimension not to ship the miss-list contradiction. Structural, not vigilance.
- ⚠️ **[The `pre_agent` Demonstration-BEFORE warning is a false positive](learnings.md)** — it reads the guide, but since T064 the block lives in `TASK_REVIEW_Txxx.md`. Fires on every correct task.
- [T008 test blind spots](learnings.md) — interchangeable cap fixtures, unasserted miss *reasons*, and bogus-vs-missing CLI selectors: three green-suite defects, one caught only by Stage 5 `verify`.
- [Redact secrets at evidence layer](decisions.md) — secret values fingerprinted before leaving the engine; never reach agent, report, or log. → see DDR-0001
- ▶ **[DDR-0002: never read secret-bearing files](decisions.md)** (user, 2026-08-16). `.env*`/`*.pem`/`*.key`/`id_rsa`/… excluded at `read_source()`; existence reported as `excluded: secret-bearing`, contents withheld. T008 gets … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
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
- ▶ **[T004 shipped — redaction is real](decisions.md)** (merged 2026-08-16, `1acfa5c`). Layered detectors: named patterns → entropy → per-segment key material, the last being what makes paths and URI passwords safe while keeping … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
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
- ⚠️ **[A new module re-implementing a traversal re-inherits old bugs](learnings.md)** — T003's `scope.py` rewrote a file walk and reproduced the exact symlink-escape T002 had already fixed in `context.py:_walk`. Canonical … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- ⚠️ **[Agents may report "ready for review" with zero commits](learnings.md)** — T003 did. Always check `git log develop..HEAD` and `git status` in the worktree before trusting the report.
- ⚠️ **[Agent worktrees have no `.venv`](learnings.md)** — `PATH=.venv/bin:$PATH python` there silently falls back to system python and fails the T001 CLI tests. Use the main checkout's interpreter with `PYTHONPATH=src`, and check pytest's exit code directly (piping through `tail` masks it).
- ⚠️ **[A merge of two green branches can be a regression](learnings.md)** — T002 moved the path check that T004 had hardened with redaction; both suites passed alone, the leak existed only in the combination. **After every conflict resolution, re-probe any cross-cutting property (redaction/validation/auth/logging) that attached to a line the other branch relocated.**
- [Truncation is rejection-triggered; `omitted_count` is a lower bound](decisions.md) — pull until one item doesn't fit, drop it, stop. Never drain to count: for a file-reading `collect` that means reading every file. Fixes a T001 guide contradiction; aligns T001 with T005.
- [T012 budget recommendation: per-dimension, not pooled](decisions.md) — a total budget split across dimensions makes each pack's contents depend on what else was requested, breaking reproducibility. Decision to be recorded when T012 is picked up.
- ▶ **[The verifier now emits a quality *rating*; FR-013 amended](decisions.md)** — engine-computed numbers are allowed when produced by **declared rules over measured metrics** (never a model, NFR-001 intact). Three words, never … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

- ⚠️ **[T029: entropy exemption = position + piece shape; merge gate needs KANBAN Done first](learnings.md)** (2026-09-28) — filename exemption only when followed by a suffix and every piece is a letters-only word; sabotage-test each guard. `pre_bash` blocks `git merge` while the task is In Progress.
- 💡 **[DEFERRED: TypeSafe AI Jev](decisions.md)** (2026-09-28) — cloud typed-choice model; not for the engine (NFR-001, no network, can't emit strings/citations). Revisit after T029–T049 as an optional agent-side tool (detect picks, pack choice, link pre-screen).
- 🔒 **[DDR-0007/0008: cited reference registry + 32 evaluation areas](decisions.md)** (2026-09-28) — score had no cited standard and 3 disagreeing language tables. Locked: one cited registry (curated 9 languages in package + … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- 🔒 **[DDR-0006: any-language source roles; calling agent contributes only at MCP hard gates](decisions.md)** (2026-09-26) — coverage = roles filled/declared, no language exemptions; generic patterns + Python/JS-TS/Rust/Java … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))

### Gotchas (see [learnings.md](learnings.md))
- ⚠️ **[T093 merged: when an abstention becomes a number, hand-check every citation first](learnings.md)** (2026-10-13). fullstack-ts's layer rule is now measured (0 violations) after removing 4 false ones: hint-only ends and a cross-package name match.
- 🔒 **[User 2026-10-13: test-path sinks not scored (T092 merged); layer share counts backend units only (T093)](decisions.md)**. A budget-freed pack reading more files can only add sink hits, which is how this was found (nest-api 59→18 after T091).
- ▶ **[Wave 17 merged (T087–T091), 2026-10-13](learnings.md)**. Architecture is recognized by behaviour and content, not names (DDR-0012). Open: backend-only layer denominator (user), compose YAML in infrastructure, WCAG URL redaction false positive.
- ⚠️ **[T089: content-shape rules each needed a real-repo precision round](learnings.md)** (2026-10-13). Document roles now filled by content or declaration (`core/documents.py`); kit names out of GENERIC_PATTERNS; follow-ups: WCAG URL redaction false positive, fullstack-ts arch-doc cites a task file list.
- ⚠️ **[T091: negatives must be decided by the changed rule alone](learnings.md)** (2026-10-13). Redaction now admits letter-then-digit name pieces (t087/v2/utf8); boundary pinned by a widening sabotage; the first negatives were caught by other rules and pinned nothing.
- ⚠️ **[T088: behaviour layers merged; repo-wide share denominator keeps monorepos abstaining](learnings.md)** (2026-10-13). Dynamic-prefix imports link a whole directory (node-monorepo controllers). fullstack-ts/node-monorepo still below 0.50 because frontend files count; backend-only denominator awaits the user. The step-limit hook charges Supervisor calls to the active_task.
- ⚠️ **[T087: third-party exclusion is one predicate; Harbor was carrying k8s-ops' ratings](learnings.md)** (2026-10-12). `scope.third_party_filter` feeds both walks + churn ranking; without Harbor every dimension abstains; infrastructure does not read compose YAML (follow-up). Merge gate reads the KANBAN before the command: commit Done separately.
- ⚠️ **[develop may be stale — check integration branches before IDs/scans](learnings.md)** (2026-10-12) — `feat/wave16-business-domain-coverage` was 127 commits ahead (T041–T086 done, T025 in progress); Wave 17 IDs T083–T086 collided.

- ⚠️ **[Parallel tasks: merge gate waits for both; shared active_task mis-attributes step limits; doc 'Not yet' ≠ areas_without_rule](learnings.md)** (2026-10-06, Wave 16).
- ⚠️ **Stage 3 worktrees are created off the root commit** — an agent's worktree may contain only `LICENSE`+`README.md`. Every spawn prompt must order the agent to verify `PROJECT_SPEC.md` + its own guide are present and rebase onto the planning branch if not.
- ✅ **Trace state file unwritable from an isolated worktree — RESOLVED, no hook change.** It *is* writable from the main checkout. Standing Stage 5 procedure: Supervisor writes `.claude/hooks/.state/active_task` then runs the guide's Verification Command itself before merging. Not a bypass — it is the independent re-run Stage 5 already requires. Details in [learnings.md](learnings.md).
- **Guardrail hook matches command *mentions*** — a commit message or memory file containing `git push` blocks the whole Bash call. Use Write/Edit or `git commit -F`.
- ⚠️ **Merge gate: two traps, both hit on T001.** (a) Stage 5 evidence must be `git checkout <task-branch> -- tasks/TASK_REVIEW_Txxx.md` into the main checkout *before* merging — the gate reads the pre-merge copy. (b) The … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
- **The `active_task` state file also feeds the step-limit hook** — Supervisor Bash calls count toward the named task's 90-call budget and will be killed once (auto-resets). Not an agent loop.
- ⚠️ **[`active_task` rejects a FUTURE timestamp as hard as a stale one](learnings.md)** — `age_s < 0` fails too. Always write it with `$(date -u '+%Y-%m-%dT%H:%M:%SZ')`, never a hand-guessed clock time, or the trace silently goes nowhere.
- ⚠️ **[The merge gate's own error hint is dead advice](learnings.md)** — it tells you to prefix `CLAUDE_ACTIVE_TASK=Txxx`, but that channel cannot work from inside a Bash call (hooks are siblings, not children). Use the state file.

- ⚠️ **[Target-repo globs are untrusted input — never compile them into a backtracking regex](learnings.md)** (T026 Stage 4 P1, 2026-09-26) — validate shape + segment-wise memoized matcher.
- ⚠️ **[Supervisor tooling gotchas, T026 session](learnings.md)** — built-in `security-review` needs `origin/HEAD` (absent here → manual pass); merge gate scans the whole command, so Kanban-move and merge must be separate Bash calls; worktree tests need `PYTHONPATH=src <main>/.venv/bin/python`; `docs/ddr` is gitignored → give agents the main checkout's absolute path.

- ⚠️ **[Every target-file read re-checks containment; `contained_only=False` is list-only](learnings.md)** (T027 Stage 4 P1, 2026-09-26) — symlink leaked a host file's heading; also group `needs_input` candidates, measure bytes on real repos.

- ⚠️ **[Zero-width band ≠ borderline; cap caller-sized lists; compose build retags 0.1.0](learnings.md)** (T028 Stage 4, 2026-09-26).

- ⚠️ **[T041: re-ask unrecorded HITL sign-offs; `**/License*` globs match source code; rebase via cherry-pick under merge gate; task-tagged container image](learnings.md)** (2026-10-07). Decisions: supply-chain floor 0.40, weights 20/15/20/20/25, CI `image:` counts for pin rule ([decisions.md](decisions.md)).

- 🔒 **[T100: aliases only in tracked files](learnings.md)** (2026-10-14) — real repo names/paths live in git-ignored `.local/real-repos.md`; a guard test fails on any reappearance.

### Learning Records

_None yet._
- ▶ **[Wave 19 merged (T094–T096), 2026-10-13](learnings.md)**. T095: `WCAG22`-style redaction exemption. T096: change-column tables are not architecture descriptions, and `##` architecture prose sections count. T094: k8s … (full: [decisions.md](decisions.md#archived-index-detail-2026-10-16))
