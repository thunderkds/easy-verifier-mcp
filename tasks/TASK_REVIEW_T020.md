# TASK_REVIEW — T020: declared ratings, coverage floors, and abstention

> Sibling of `tasks/TASK_GUIDE_T020.md`. Implementation evidence is recorded
> here for independent Stage 4/5 review.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria** | ☑ pass | `tests/test_judge.py` — **66** collected cases after four Stage 4 remediation rounds. Original AC map: #1/#3 hand-recomputable rating; #2 static rule table; #4 discovery-complete floor table, seven floor boundaries, below-floor provenance; #5 consumer-boundary abstention; #6 partial/all metric abstention; #7/#8 hostile 63→70 aggregate; #9 AST structural gate; #10 canonical serialization; #11 all-seven abstention. Stage 4 regressions additionally cover exact runtime result types, all public constructor invariants, aggregate 0–100 enforcement, empty miss-list contradiction, finite unit-interval coverage, finite metric outcomes, strict JSON, closed/coherent abstention reasons and revalidation, typed `SourceMiss` values, truthful arithmetic methods, canonical public-value ordering, exact declared abstention floors, single-dimension coverage consistency, rule key/payload drift, and malformed rule/floor declarations. |
| Verification command run | ☑ pass | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_judge.py -q` → **`66 passed in 0.15s`**, exit 0 after recovery and final compatibility remediation. |
| Negative cases hold | ☑ pass | Round 1 regressions produced **23 failed, 32 passed** against `b441b2d`; round 2 constructor regressions produced **5 failed, 55 passed** against `37dc017`; hostile-constructor regressions produced **3 failed, 60 passed**; final compatibility regressions produced **3 failed, 63 passed** before remediation. Existing sabotage still pins all seven floors and eleven thresholds. Direct mutations from the first submission: floor predicate always true → 10 failures; threshold predicate always true → 15; abstentions included as contributors → 2. Stage 4 tests also mutate rule/floor table entries at runtime; every malformed key, weight, threshold, comparison, boundary, and floor value is rejected. |
| verify | ☑ pass via documented substitution | The named `verify` skill is unavailable in this Codex session. Recovery verification on 2026-09-12 reran the exact focused command: **66 passed in 0.15s**; Ruff check and format check passed; the project `.venv` reproduced its pre-existing `mcp` collection limitation; the compatible provisioned interpreter passed the full suite: **539 passed, 1 upstream warning in 10.29s**. Earlier mutation sabotage and the live all-dimension witness remain recorded below. |
| Review scope bounded to blast radius | ☑ pass | Reviewed only `src/easy_verifier/core/judge.py`, `tests/test_judge.py`, and the T020 guide/review records. Existing metrics/models/synthesis/dimensions were consumed but not modified. Adapter/report wiring remains T022. |
| Full smoke suite still green | ☑ pass with environment note | The required main-checkout interpreter still cannot collect two pre-existing adapter suites because its environment lacks `mcp`; reproduced again on 2026-09-12. Supplemental full command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/hungnguyenhuu/workspace/training/phuongbui/ai-training/travel_chatbot/.venv/bin/python -m pytest -q` → **539 passed, 1 upstream warning in 10.29s**, exit 0. Focused Ruff: `All checks passed!`; format: `2 files already formatted`. |
| **UI: Visual regression** | ☑ N/A | Pure-backend arithmetic library; no rendered UI. |
| **UI: Design-system compliance** | ☑ N/A | No UI or design-system output. |
| **UI: Responsiveness** | ☑ N/A | No viewport-dependent output. |

---

## Self-review

The named `code-review` skill is unavailable in this Codex session. A bounded
manual P0–P3 review of the complete four-file diff was used as the documented
substitution.

**Initial self-review verdict before independent Stage 4:** P0 0 / P1 0 / P2 0 /
P3 2. Stage 4 subsequently found seven P1 and four related P2 boundary defects;
all are remediated below.

| Sev | Finding | Disposition |
|-----|---------|-------------|
| P3 | Partial metric abstention reduces the available-weight denominator and can raise a dimension rating, just as dimension abstention can raise the overall. | Required by the approved normalization semantics. `Rating.unavailable_metrics` carries every excluded metric and reason; a focused test pins the disclosure and normalization. |
| P3 | The calibrated floors are deliberately low for ecosystem-alternative checklists, especially code-quality 0.16. | Accepted initial calibration, documented in the guide and table comments; the live-pack witness demonstrates usability. Revisit after more repositories, per DDR-0003. |

### Direct security-review substitution (Risk: Medium)

Reviewed the only executable file in full. Its import set is restricted to
`__future__`, `json`, `math`, `collections.abc`, `dataclasses`, `.metrics`, and
`.models`. It has no filesystem, subprocess, socket, HTTP, environment, config,
dynamic import, or model-client path. The AST test asserts the import whitelist,
forbidden I/O/network attributes, and model-client tokens. Serialization can
only expose already-redacted metric citations/reasons and coverage misses; this
module reads no evidence text or raw secret value. No credential-shaped test
fixture was introduced.

---

## Stage 4 Remediation

The independent reviewer drove malformed public objects and IEEE non-finite
values at the consumer boundary. The first submission failed 23 of the 55-case
suite after those regressions were added.

| Sev | Finding | Remediation |
|-----|---------|-------------|
| P1 | `rate_overall` accepted arbitrary duck-typed objects, and `Rating(999)` was constructible. Six forged objects plus the invalid rating produced a false 999 overall with "none abstained" disclosure. | `Rating.__post_init__` enforces an exact integer in 0–100; `rate_overall` independently enforces exact `Rating`/`RatingAbstention` types and rechecks rating values. Tests cover ordinary construction, forged constructor bypass, and unsupported objects. |
| P1 | Below-floor coverage with an empty `sources_missing` tuple returned a plausible abstention despite omitting AC #4's required named unreached source. | Coverage below 1.0 now requires a non-empty miss list (and 1.0 rejects a non-empty list). `RatingAbstention` independently requires misses for `below_coverage_floor`. |
| P2 | NaN/Infinity and out-of-range coverage or metric outcomes reached comparisons and non-standard JSON. | Coverage is now finite `[0,1]`; numeric metric inputs are finite; rating inputs validate at construction; JSON uses `allow_nan=False`. NaN, positive/negative infinity, and both range sides have regressions. |
| P2 | A `RATING_RULES` key could drift from `rule.metric_name`, leaving the inspectable table internally contradictory. | A pre-scoring declaration validator enforces key/name equality, positive integer weights, finite numeric thresholds, known comparisons, finite `[0,1]` floors, and the approved inclusive boundary. Runtime table mutations prove each guard. |
| P2 | An invented abstention reason entered aggregation and failed later during disclosure/serialization with `KeyError`. | `RatingAbstention` now has a closed reason-code set and validates the coherent required fields for each state at construction, including the seven nested abstentions for `no_dimension_rated`. |
| P1 | Public `RatingInput`, `Rating`, and `OverallRating` constructors still admitted values that contradicted their serialized arithmetic: empty inputs, unknown dimensions, mismatched weights/results/counts, and arbitrary overall values. | Constructors now validate their complete local contracts. `Rating` requires the input/unavailable partition of all declared rules and recomputes its value. `OverallRating` carries serialized `contributor_values`, validates the seven-dimension contributor/abstention partition and counts, and recomputes its value. `RatingInput` validates every field and pass/earned-weight coherence. |
| P2 | Exact-type `RatingAbstention` objects built via `object.__new__` could bypass construction checks; an invalid leaf could enter an overall or parent abstention and fail later. | `rate_overall` revalidates every rating and abstention before reading their fields. Parent `no_dimension_rated` construction revalidates each immediate leaf, rejects nested overall abstentions, and avoids recursive-cycle behavior. |
| P1 | `RatingAbstention` still accepted unknown leaf dimensions and fields contradictory to its `reason_code`; `sources_missing=(object(),)` constructed successfully and crashed later during serialization. | Every leaf reason now requires a known dimension and permits only its coherent field set. Miss lists must be tuples of exact `SourceMiss` values with non-empty string fields, including during aggregate revalidation. `no_dimension_rated` permits only its seven canonical leaf abstentions. |
| P1 | Caller-overridable `Rating.method` / `OverallRating.method` could lie about serialized arithmetic, and reordered rating inputs or abstentions produced different bytes for the same public value, violating audit truthfulness and AC #10 determinism. | Both method fields must equal their declared arithmetic text. Rating inputs, unavailable metrics, overall contributors, overall abstentions, and nested all-abstention values must follow the declared rule/dimension order; factory functions already emit that canonical order. |
| P1 | `rate()` used only the matching entries from `CoverageSummary`, silently ignoring extra dimensions and a `combined` value that contradicted the sole per-dimension value. | A single-dimension coverage gate now requires exactly one `per_dimension` entry and one miss-list entry, both naming the rated dimension, with `combined` exactly equal to that dimension's coverage. |
| P1 | Floor-bearing leaf abstentions could serialize a caller-supplied floor different from the current declared `COVERAGE_FLOORS` value, making provenance contradict the inspectable rule table. | Construction and aggregate revalidation now require `below_coverage_floor`, `coverage_not_applicable`, and `all_metrics_abstained` values to carry their dimension's exact current declared floor. |

Post-remediation bounded review: P0 0 / P1 0 / P2 0. The original two P3
trade-offs remain documented above. No filesystem/network/model capability was
added; `math.isfinite` is the only new primitive.

---

## Demonstration

**BEFORE** (captured 2026-09-03T08:45:40Z in isolated clone
`/tmp/easy-verifier-mcp-t020`, branch `feat/t020-judge`, before implementation):

```text
$ ls src/easy_verifier/core/judge.py tests/test_judge.py
ls: cannot access 'src/easy_verifier/core/judge.py': No such file or directory
ls: cannot access 'tests/test_judge.py': No such file or directory
$ PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_judge.py -q
ERROR: file or directory not found: tests/test_judge.py

no tests ran in 0.00s
exit=4
```

**AFTER** (same isolated clone and required interpreter):

```text
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_judge.py -q
..................................................................       [100%]
66 passed in 0.15s
exit=0
```

Live all-dimension witness over this repository:

```text
architecture 82
blast-radius 64
code-quality 64
requirement-fidelity 50
security 50
solution-fit 82
test-strategy 60
overall 65
contributors (architecture 82, solution-fit 82, requirement-fidelity 50, code-quality 64, security 50, test-strategy 60, blast-radius 64)
disclosure 7 of 7 dimensions contributed; ratings average contributors only, so abstention can raise the overall; none abstained
```

**DELTA**: callers can now turn a complete per-dimension `MetricSet` plus its
coverage summary into a hand-recomputable 0–100 rating, or a typed abstention
that cannot be consumed as a number. Exactly seven such outcomes produce a
deterministic contributor-only overall with its abstention boundary carried in
the same value. Before T020, neither operation or output type existed.
