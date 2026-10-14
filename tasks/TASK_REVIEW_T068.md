# TASK_REVIEW — T068: Priority batches

> Sibling of `tasks/TASK_GUIDE_T068.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t068_priority_batches.py` (43 tests: purpose → churn → path order, no-git fallback, batch slicing, oracle batches 1–2 == direct over 400 files, batches=N vs all byte-equal, under-cap snapshot `tests/snapshots/t068_under_cap_score.json` from pre-change `2bf07ff`, needs_input.continue_batches, out-of-range/malformed → error, truncation no longer abstains sampled metrics). Updated: test_t050, test_t031, test_t009 (old all-or-none cap reversed by DDR-0010), test_t055 legacy dict. Sabotage (agent): zero churn / drop sampled metrics turn tests red — pass |
| Verification command run | ☑ pass | Supervisor 2026-10-04 03:03 UTC node-monorepo CLI: `--batches 1` → samples 200/1178 (1 of 6) for architecture, code-quality, test-strategy; code-quality 67, architecture 70, test-strategy 75, overall 66; stderr "continue with --batches 2, or --all". `--batches 2` → 400/1178 (2 of 6), same ratings — pass |
| Negative cases hold | ☑ pass | MCP (agent, in-process tool fn): `batches: 7` → "out of range; this scope has 6 batches"; malformed → validation error; fullstack-ts (under cap) unchanged — pass |
| verify | ☑ pass | Supervisor drove CLI on node-monorepo batches 1 and 2 (above); agent drove MCP continue_batches round {1,6,200,1178} → batches 2 → {2,6,400,1178}; fullstack-ts before/after identical (under cap) — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed new core/batches.py (purpose classes as data, ordering, parse/resolve, churn via run_git_text), metrics.compute_sampled_metrics + EvidencePack.sample, _code_extract/code_quality/architecture/test_strategy batching, roles/score/adapters input + needs_input, report disclosure. Agent input carries only `batches` (no numbers) — FR-062 holds. code-review: P0 0, P1 0, P2 2 → follow-ups: (a) score payload grows ~550 KB per batch (476 KB → 1.08 MB → 1.64 MB) from existing per-file citation lists, against the token-saving goal; (b) under-cap repos still compute code metrics over budgeted excerpts and abstain on truncation (fullstack-ts) while above-cap repos use whole files. Security (manual): git via hardened run_git_text; sample facts redacted like ReachFacts; secret-bearing files still refused — pass |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor re-run: 1740 passed, 2 skipped, 2 failed (the 2 known stale-Docker container tests); ruff All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | `<scratchpad>/t068_panel_1280.png` — LLM-vision verdict (Supervisor): sample disclosure line on each sampled dimension card — pass |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | reuses existing `rating-method` class, no new CSS tokens — pass |
| **UI: Responsiveness at target viewports** | ☑ pass | `<scratchpad>/t068_panel_400.png` true 400px iframe: disclosure wraps, no horizontal page scroll in the panel — pass |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured on the task branch at `2bf07ff` (T067 merged, no T068 code), before any
implementation commit. Pasted verbatim; the score run's stdout was saved to a scratchpad file.

```
$ date -u
Sat Oct  3 03:11:31 PM UTC 2026
$ PYTHONPATH=src .../.venv/bin/python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope project </dev/null | <ratings>
architecture 50
blast-radius all_metrics_abstained
code-quality insufficient_measured_weight 0.20
requirement-fidelity below_coverage_floor
security 50
solution-fit no_static_rule
test-strategy 100
# overall (same command re-run at 03:11:56, stdout saved): 67

$ date -u
Sat Oct  3 03:19:37 PM UTC 2026
$ git log --oneline -1
2bf07ff merge(T067): evidence floor — no number below 50% measured weight; evidence-lack is a warning
$ for d in code-quality architecture test-strategy; do PYTHONPATH=src .../python -m easy_verifier.adapters.cli $d --repo <real-repos>/node-monorepo --scope project </dev/null 2>&1 >/dev/null | grep -i "cap\|were not read"; done
warning [standalone]: 1178 in-scope source files exceed the cap of 200 for function excerpts; none were read, so metrics over function excerpts abstain rather than describe an arbitrary subset
warning [standalone]: 1178 in-scope source files exceed the cap of 200 for import excerpts; none were read, so metrics over import excerpts abstain rather than describe an arbitrary subset
warning [standalone]: 1178 source file(s) in the resolved scope were not read, because together with the test evidence they exceed the 200-file read cap. The pack therefore holds no source file, so source-to-test figures computed over it cannot describe this scope's sources.
```
(The grep also matched a few excerpt-text JSON lines that happen to contain "Capital"/"cap"; omitted.)
The score payload carries no pack warning, so the cap message is only visible per dimension: the
code tiers read **zero** of node-monorepo's 1,178 source files and code-quality abstains at 20% measured
weight (lint + format config only).

fullstack-ts at the same commit (second real repo, `Sat Oct  3 03:19:27 PM UTC 2026`): overall 58;
architecture 100; code-quality insufficient_measured_weight 0.45; test-strategy
insufficient_measured_weight 0.30; requirement-fidelity 15; security 59.

**AFTER**: same repos, implementation commit `36ed737` (+ this evidence commit), by the implementing agent.

```
$ date -u
Sun Oct  4 02:57:55 AM UTC 2026
$ PYTHONPATH=src .../python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope project --batches 1 </dev/null
stderr: warning [batches]: read batches 1 of 6 (200 of 1178 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
overall 66
architecture 70 | blast-radius all_metrics_abstained | code-quality 67 | requirement-fidelity below_coverage_floor
security 50 | solution-fit no_static_rule | test-strategy 75
samples: architecture / code-quality / test-strategy  1 of 6, 200 of 1178
  functions_over_ccn_10_share 0.01571890892279242 | ...sample: batches 1 of 6, 200 of 1178 files -- computed over the whole text of those files, not only the excerpts quoted in this pack
  max_function_ccn 43
  type_escapes_per_kloc 0.0
  todo_without_ticket_share 1.0

$ date -u
Sun Oct  4 02:58:07 AM UTC 2026
$ ... score ... --batches 2
stderr: warning [batches]: read batches 2 of 6 (400 of 1178 in-scope source files, most important and most-changed first); continue with --batches 3, or --all
overall 66; code-quality 67; architecture 70; test-strategy 75
samples: all three 2 of 6, 400 of 1178
  functions_over_ccn_10_share 0.013095749248604552 | ...sample: batches 2 of 6, 400 of 1178 files -- ...
  max_function_ccn 53
  type_escapes_per_kloc 0.0
  todo_without_ticket_share 1.0

MCP round (in-process tool function mcp_server.score), Sun Oct  4 02:58:38 AM UTC 2026:
round1 needs_input keys: ['continue_batches', 'picks', 'reference']
round1 continue_batches: {"batches_done": 1, "batches_total": 6, "files_read": 200, "files_in_scope": 1178,
  "question": "Only 200 of 1178 in-scope source files were read (batches 1 of 6, most important and most-changed first), ... call score again with the same agent_input plus \"batches\": 2 (or \"all\" ...); never send a file count or a metric."}
round2 (agent_input {"batches": 2}) continue_batches: {'batches_done': 2, 'batches_total': 6, 'files_read': 400, 'files_in_scope': 1178}
batches=7 -> BatchInputError batches: 7 is out of range; this scope has 6 batches of source files

fullstack-ts, Sun Oct  4 02:59:11 AM UTC 2026 (under the code cap, so unchanged by design): overall 58;
architecture 100; code-quality insufficient_measured_weight 0.45; test-strategy
insufficient_measured_weight 0.30; requirement-fidelity 15; security 59; no `samples` key.
```

Report (node-monorepo scratch clone, `write-report --batches 2`): each sampled card shows "Sample: batches
2 of 6 — 400 of 1,178 in-scope source files read, ordered by …". Screenshots (score panel extracted
with the report's own `<head>` styles): `<scratchpad>/t068_panel_1280.png`,
`.../t068_panel_400.png` (400px iframe). The disclosure is visible and there is no horizontal page scroll; only the existing `rating-method` class is used.

Payload size (node-monorepo score JSON): 476 KB before → 1.08 MB at batch 1 → 1.64 MB at batch 2. The
growth is in metrics that already existed and already cite every file read
(e.g. `source_files_without_covering_test` lists all 200/400 paths). Excerpts stay within the budget (AC9).

**DELTA**: On a repository with more sources than the cap, code-quality, architecture and
test-strategy now read the highest-priority, most-changed 200 files instead of none (node-monorepo
code-quality goes from abstained at 20% weight to rated 67 over a disclosed sample), and the user can
continue batch by batch (`--batches N`/`--all`, or MCP `continue_batches` → `agent_input.batches`) or stop.

**WITNESS**: Supervisor (main session), 2026-10-04 03:03 UTC — independent node-monorepo CLI runs (batches 1, 2) and full-suite re-run; not the implementing agent alone.

---

## Design

> Written by the implementing agent before any implementation code (C3 gate). DDR-0010 §3–§5 and
> the guide were checked against the code; no conflict found that needs a stop. Interpretations
> are listed at the end for the Supervisor.

**1. Where batching applies.** Only where a dimension today hits its all-or-none cap:
`_code_extract.source_candidates` (code-quality functions, architecture imports; cap
`MAX_CODE_SOURCES`) and test-strategy's source reads (cap `MAX_TEST_SOURCES`). Candidates are
unchanged: in-scope files whose suffix has registry syntax and that classify as source (not test).
At or under the cap nothing changes — same reads, same excerpts, no new pack or payload key (AC7).

**2. Purpose classes — declared data** in a new `core/batches.py` (`PURPOSE_CLASSES`, each
`{name, rank, directories, names, basis}`). Matched on lower-cased path segments / basename
patterns, checked most-specific first (generated/vendored, then scripts/tooling, then
application/server, else other application); ranked:

| rank | class | match | basis |
|---|---|---|---|
| 0 | application/server source | a directory segment `server(s)`, `backend`, `api`, `service(s)`, `internal`, `cmd`, `handlers`, `controllers`, `routes` | project-default |
| 1 | other application source | everything else (catch-all) | project-default |
| 2 | scripts/tooling | a segment `scripts`, `script`, `tools`, `tooling`, `bin`, `bench(marks)`, `example(s)`, `fixtures`; or a build file name (`gruntfile.js`, `gulpfile.js`, `*.config.{js,ts,mjs,cjs}`, `setup.py`, `noxfile.py`, `fabfile.py`) | project-default |
| 3 | generated/vendored | a segment `vendor(s)`, `third_party`, `third-party`, `thirdparty`, `node_modules`, `bower_components`, `dist`, `generated`, `__generated__`; or a generated name (`*.min.js`, `*-min.js`, `*.pb.go`, `*_pb2.py`, `*_pb2_grpc.py`, `*.generated.*`, `*_generated.go`, `*.g.cs`, `*.designer.cs`) | GitHub Linguist `vendor.yml` / `generated.rb` at the commit the registry already pins (`d0921d10…`), a subset |

Generated/vendored files are ordered **last, never dropped**.

**3. Ordering key** (deterministic): `(class rank, -churn, path)`. Churn = number of the last
`CHURN_COMMITS = 400` non-merge local commits naming the file
(`git log -z --no-merges --relative --name-only --format= -n 400` through `core.git.run_git_text`,
the one hardened git entry point; `--relative` keeps paths repo-relative when the target is a
subdirectory; `-z` avoids path quoting). No git / git failure → churn 0 for every file, so the order
falls back to class → path, and the disclosed order text says why. Computed once per dimension
context (the budget may call `collect` up to 3×).

**4. Batches.** `batches_total = ceil(candidates / cap)`; batches `1…N` = the first `N × cap`
files of the ordered list. The engine always re-derives the order and reads batches 1…N afresh
(stateless, FR-062). `N` is `1` by default, an int `1 ≤ N ≤ total`, or `"all"` (= total).
Shape errors (`0`, `-1`, `"x"`, `true`, `1.5`) are rejected in agent-input validation before any
dimension runs; out-of-range (`N > total`, including `N > 1` on a repo at/under the cap) is
rejected by the first dimension that computes the total, as a `ValidationError` subclass whose
constructor survives `pipeline._redacting_exceptions` (so `combined_pack` re-raises it instead of
turning it into a failed slot) → CLI exit 2 / MCP tool error. Never clamped.

**5. How metrics merge across batches (the guide's "if merging requires counts beyond the excerpt
budget" branch applies).** On node-monorepo, 200 files of whole functions far exceed the 120 KB budget,
so a pack-only metric would always see a truncated pack and every whole-set metric would abstain
(FR-027a) — AC3/AC8 could never hold. So, **only when batching is active**:

- The dimension reads every file of batches 1…N once through `read_source` (secret-bearing files
  refused there, as always) and hands the in-memory texts, as whole-file units, to a new pure
  function in `metrics.py` (`compute_sampled_metrics`) that runs the **existing** metric functions
  over them. Nothing in `metrics.py` reads a file; the dimension does, exactly as blast-radius
  builds `ReachFacts`. Raw text never leaves the dimension: only the result is kept.
- "Merging" is therefore recomputation over the union of batches 1…N: counts are summed over all
  files (functions, over-threshold functions, scanned lines, escapes, debt markers), the maximum is
  the max over all files, and import cycles are found over the union's graph. Same input → same
  value, and the SC3 oracle (batches 1–2 vs. the same 400 files computed directly) is equality by
  construction.
- Results ride on the pack as `EvidencePack.sample: SampleFacts | None` —
  `{batches_done, batches_total, files_read, files_in_scope, order, metrics}` where each metric is
  `{name, value | abstention, computed_from (paths), derivation}`; refs and derivation are
  redacted in the dimension (the `ReachFacts` pattern), and refs are paths that are in
  `files_read`, so `check_citations` still holds. `sample` joins `_OMITTED_WHEN_ABSENT`, so a pack
  without it serialises byte-for-byte as before.
- `compute_metrics` uses a stored sample result in place of computing from excerpts. The FR-027a
  truncation abstention does not apply to these, because they were not computed from the budgeted
  excerpts; that is stated in their derivation.
- Sampled metrics (declared data, `SAMPLE_METRICS` per dimension): code-quality
  `functions_over_ccn_10_share`, `max_function_ccn`, `type_escapes_per_kloc`,
  `todo_without_ticket_share`; architecture `top_level_import_cycles`; plus `source_file_share` on
  all three, and test-strategy `test_to_source_ratio`, `source_files_without_covering_test`,
  `source_files_without_covering_test_share` (test-strategy needs no precomputation: its sources
  are read without an excerpt, so `files_read` already is the sample). Every one of these gets
  `; sample: batches N of M, X of Y files` appended to its derivation (AC3), plus "computed over
  the whole text of those files, not only the excerpts quoted in this pack" where precomputed.
- Excerpts are unchanged in kind and still budgeted (AC9): function excerpts ranked by CCN and
  import lines in path order, drawn from the files of batches 1…N. (DDR §5 permits sending only
  the newest batch's excerpts; ranking over 1…N is the existing code path and keeps `--all` showing
  the most complex functions, not batch M's vendored ones. The budget bounds both.)
- test-strategy: tests keep their own 200-read cap; sources are batched separately with the same
  candidate list as the code tiers (so all three dimensions report the same totals), read
  **before** the ranked test sweep so a budget stop cannot silently skip them. When the old
  overflow fired but the candidates fit in one batch, they are now simply read (previously none).

**Interaction with the fullstack-ts byte-budget abstention (FYI in the spawn).** fullstack-ts is under the
code cap, so batching never activates there and its whole-set code metrics still abstain on
truncation — unchanged, as instructed (no budget change). The consequence is a deliberate
discontinuity: a repository just above the cap gets whole-file sampled metrics, one just below
keeps excerpt-only metrics. Extending whole-file computation below the cap would change payloads
of at-or-under-cap repos, which AC7/SC6 forbid; flagged for the Supervisor.

**6. Exact shapes.**

- Agent input: new key `batches`: `int ≥ 1` or `"all"`. Nothing else; never a count of files or a
  metric (FR-062). A replayed document with the same `batches` yields a byte-equal payload.
- Score payload (both adapters, so parity holds): new top-level key `samples`, present **only**
  when some dimension was sampled, in canonical dimension order:
  `[{"dimension", "batches_done", "batches_total", "files_read", "files_in_scope", "order"}]`
  (`files_read` = files in batches 1…N).
- MCP only, `needs_input.continue_batches` (rides along with any round, like `reference`/`review`,
  whenever a sampled dimension has `batches_done < batches_total`):
  `{"batches_done": N, "batches_total": M, "files_read": X, "files_in_scope": Y, "question": "..."}`
  where the question tells the agent to ask the user whether to read the next batch (more tokens,
  a larger sample) or stop, and to continue by calling `score` again with the same agent_input
  plus `"batches": N+1` (or `"all"`). The adapter adds it; `to_dict` never carries it.
- CLI `score` and `write-report`: `--batches N` | `--all` (mutually exclusive), default 1; passed
  to the core as `batches`. If `--agent-input` also names `batches` and they differ → validation
  error. When batches remain, stderr says
  `warning [batches]: read batches N of M (X of Y in-scope source files, …); continue with --batches N+1, or --all`.
- Pack warning (replaces the "none were read" warning):
  `"{Y} in-scope source files exceed the cap of {cap} for {what}; read in priority batches of {cap}: batches {N} of {M} ({X} of {Y} files), ordered by {order}. Metrics over {what} describe this sample."`
- Report: each sampled dimension's score card shows
  `Sample: batches 1 of 6 — 200 of 1,178 in-scope source files, ordered by …` in the existing
  `rating-method` style; no new CSS.

**Files.** new `core/batches.py`; `dimensions/_code_extract.py`, `code_quality.py`,
`architecture.py`, `test_strategy.py`; `core/models.py` (SampleFacts), `core/metrics.py`
(compute_sampled_metrics, SAMPLE_METRICS), `core/pipeline.py` (copy `sample`, pass `batches`),
`core/synthesis.py`, `core/roles.py` (agent-input key), `core/score.py`, `core/report.py`,
both adapters, `docs/SCORING_FLOW.md`, new `tests/test_t068_priority_batches.py`, and updates to
three existing tests that pin the reversed all-or-none behaviour (t050 above-cap, t031
all-or-none, t009 total-read bound).

**Interpretations to confirm (not blocking).** (a) The split between "application/server" and
"other application" source is by directory name (server/backend/api…), project-default. (b)
`files_read` in `samples`/`continue_batches` counts files selected in batches 1…N; a file
`read_source` refuses is still reported in `sources_missing` as before. (c) Churn window 400
non-merge commits, mirroring blast-radius's hotspot window.
