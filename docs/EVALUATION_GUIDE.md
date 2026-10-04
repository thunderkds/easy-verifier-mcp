# Evaluation guide: reading a score or report

Read this when you receive a `score` result (CLI or MCP) or an HTML report from `write_report`. It
answers four questions: what each part means, when to trust a number, what to add when a number is
missing, and what to fix first.

Every number here is rule arithmetic over measured facts: a rule compares one metric with a
threshold. The engine does not judge quality and calls no LLM. A number says how many declared
rules a repository meets, weighted, and nothing more. The rules, thresholds and weights are in
[`SCORING_RULES.md`](SCORING_RULES.md); the round-by-round flow is in
[`SCORING_FLOW.md`](SCORING_FLOW.md). This guide does not repeat them.

Code: `src/easy_verifier/core/score.py`, `core/judge.py`, `core/improve.py`, `core/batches.py`,
`core/report.py`.

## What you received

| Key in the `score` payload | What it holds |
|---|---|
| `ratings` | One entry per dimension (seven): a number with its rule inputs, or an abstention with a `reason_code` |
| `overall` | The overall `value`, its `contributors`, `rated_by` and `abstentions`, and a one-line `disclosure` |
| `warnings` | One entry per dimension that got no number for lack of evidence |
| `samples` | Present only for large repositories: which batches of source files were read |
| `improvement_plan` | Every unmet or unmeasured rule of every rated dimension, grouped and ranked by gain |
| `assessments`, `divergences` | Present only if you sent findings; never blended into a rating |

Over MCP, a `needs_input` block may ride along (`picks`, `gate_evaluations`, `reference`, `review`,
`continue_batches`); see [`SCORING_FLOW.md`](SCORING_FLOW.md#the-rounds).

## The overall number

- The overall is the mean of the dimensions that produced a number, rounded once (ties to even).
  Abstaining dimensions are left out, not counted as zero.
- So abstention can raise the overall: a repository rated on 2 of 7 dimensions can score higher than
  one rated on all 7. Always read the overall together with its `disclosure`, which names how many
  dimensions contributed, how each was rated (`rules`, `blended (w …)`, `agent-rated`) and which
  abstained and why.
- Two overalls are comparable only when the same dimensions contributed.
- A dimension speaks only for the evaluation areas its rules cover. Today 11 of the 32 areas have
  rules and 21 have none; see [AREA_COVERAGE.md](AREA_COVERAGE.md) for the area-by-area map.

## When to trust a number

A dimension number is as good as the evidence under it. Check these, in order:

1. **Coverage floor.** Each dimension declares the share of its checklist sources that must be found
   (`COVERAGE_FLOORS`). Below it, the dimension abstains `below_coverage_floor`; it is never rated on
   too few sources.
2. **Measured-weight floor.** A dimension is rated only when its measured rules carry at least 50%
   of its declared rule weight (`MEASURED_WEIGHT_FLOOR`). Below it, it abstains
   `insufficient_measured_weight`. Above it, the unmeasured rules are listed as P2 in the
   improvement plan; the report's Summary names the lowest measured share.
3. **Sample label.** On a large repository, code-quality, architecture and test-strategy may be
   computed over a sample. The derivation says `sample: batches N of M, X of Y files` and the
   Summary says `(sample: X of Y files)`. A sample number describes the files read, not the whole
   repository (see [Large repositories](#large-repositories-batches)).
4. **Gated and agent-rated parts.** Over MCP, the calling agent may add a score only at a gate:
   solution-fit (`no_static_rule`) and any dimension with a rule input within ±10% of its threshold
   (`BORDERLINE_BAND`). A blended number is shown with its parts, for example
   `74 = rules 68 + agent 88 (w 0.30)` (illustrative). An `agent-rated` number is the agent's alone:
   no rule supports it. Treat it as the agent's view, not a measurement.
5. **Known false positives.** A rule counts what a scanner matched, not what a human confirmed. Read
   the cited files before acting on a security count (see the coffee-shop-api example below).

## Warnings: what could not be measured

A dimension that lacks evidence gets no number and one entry in `warnings` (the report's "What we
couldn't measure" section). The reasons are the evidence-lack set (`EVIDENCE_LACK_REASONS`):
`insufficient_measured_weight`, `below_coverage_floor`, `coverage_not_applicable`,
`all_metrics_abstained`, `dimension_failed`.

- A warning is never gated and never agent-rated: an evaluation sent for it is rejected. The only
  way to get a number is to supply the evidence.
- Each warning lists `unmeasured_rules` (metric and why it was not measured) and `sources_missing`
  (source and why it was not found); `measured_share` is present when known. Add what they name, then
  score again.
- Some rules cannot be measured at every scope. blast-radius reads a change: at `project` scope the
  Summary says to run with `--scope changes`. The requirement-fidelity traceability metrics always
  abstain from a read-only pack (see [`SCORING_RULES.md`](SCORING_RULES.md)).

## Large repositories: batches

Above 200 source files, code-quality, architecture and test-strategy read the sources in batches of
200, most important and most-changed first. One batch is read by default.

- CLI: `--batches N` or `--all`; stderr says how many batches remain.
- MCP: while batches remain, `needs_input.continue_batches` asks whether to read the next batch.
  Ask the user; to continue, call `score` again with the same `agent_input` plus `"batches": N+1` or
  `"all"`. Stopping keeps a result that is honest about the files it read.
- `samples` gives, per sampled dimension, `batches_done`, `batches_total`, `files_read` and
  `files_in_scope`. Details: [`SCORING_FLOW.md`](SCORING_FLOW.md#large-repositories-priority-batches).

## Improvement plan

Every unmet or unmeasured rule of every rated dimension, in three groups:

| Group | Meaning | How to act |
|---|---|---|
| P0 | near miss: unmet, within ±10% of the threshold | Smallest change for the gain; fix first |
| P1 | clear failure | Larger change; ranked by gain |
| P2 | not measurable yet: the metric abstained | Supply what the metric needs; the gain is a range |

- `overall_gain` and `dimension_gain` are **recomputed** with the rating arithmetic as if that one
  rule passed, not read off the rule's weight. Gains do not add up: fixing two rules is a new
  computation.
- A P2 gain is `[if it fails, if it passes]`; the low end can be negative, because measuring a rule
  that then fails lowers the number.
- A gated dimension's gain uses its rules part (`gain_basis` `rules`); the agent half of a blend is
  never predicted.
- A dimension without a rules rating gets one `abstained` line with its reason, and its
  `unmeasured` rules when known, instead of items.
- Each item cites the files the metric was computed from. Open them before changing anything.

Full grouping and ordering rules: [`SCORING_FLOW.md`](SCORING_FLOW.md#improvement-plan).

## Engine text and agent text

- Every number, the Summary's templated sentences and each plan item's fix line come from the engine
  (`fix.source` `engine`).
- Text from the calling agent is labelled `agent` in the report: a one-paragraph `summary` and
  per-item `improvements` suggestions passed to `write_report`. They are redacted and escaped, change
  no number, and an `improvements` entry must name an item in the report's own plan or the write
  fails.
- `score` accepts `improvements` and ignores them; only `write_report` shows them.

## The report, top to bottom

1. **Before you share this report**: one line; the full notice is folded.
2. **Summary**: the overall and which dimensions were rated (with sample and agent labels), an
   Evidence line (dimensions rated, lowest measured rule weight, warning count), the top 3 P0/P1
   fixes with their gain and first cited standard, plain lines for what could not be evaluated, then
   the agent's paragraph if sent.
3. **Improvement plan**: P0 and P1 as cards, the Summary's top 3 highlighted; P2 folded; dimensions
   without a rules rating last.
4. **What we couldn't measure**: context warnings and evidence warnings merged, one line each, full
   text folded.
5. **Quality score**: the overall with its disclosure and one row per dimension; rule inputs,
   citations and cited files folded.
6. **Checklist coverage** and **Dimensions**: folded; every source sought, found or missed, and the
   evidence packs.

## Act on it

1. Read the overall's disclosure: how many of 7 dimensions contributed, and how each was rated.
2. Read the warnings. For each, add what `unmeasured_rules` and `sources_missing` name, or accept
   that dimension is not rated.
3. On a sampled result, decide whether to read more batches before acting on code-quality,
   architecture or test-strategy.
4. Open the cited files of the top P0/P1 items and confirm each finding is real.
5. Fix P0 first, then P1, by `overall_gain`. Then supply what P2 rules need.
6. Score again with the same scope and batch count, and compare like with like.

## Worked examples

From Supervisor runs on 2026-10-04 with the develop code, `score` at `project` scope.

**coffee-shop-api** — overall 65; 2 of 7 dimensions rated (code-quality 71, security 59), so 65 is
the mean of those two only. Top fixes by `overall_gain`: security `redaction_hits_observed` +21,
code-quality `max_function_ccn` +9, `strict_type_config_missing` +5. Warnings: architecture,
blast-radius, requirement-fidelity, and test-strategy (30% of its rule weight measured, below the
50% floor). The security number is lowered by known scanner false positives (long spec filenames
and `${VAR}` references matched as secrets): read the cited files before treating the +21 as a real
finding.

**bryony** — overall 66; 4 of 7 rated: architecture 70, code-quality 67, test-strategy 75, security
50. Architecture, code-quality and test-strategy are a sample of 200 of 1,178 files (batch 1 of 6);
reading more batches can change them.
