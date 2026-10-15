# TASK_GUIDE — T104: Experiment — can a local decision model (Laya) answer the detect-gate picks as well as the LLM?
**Date**: 2026-10-15
**Complexity Level**: C2
**Risk Level**: Medium (private repository content is fed to a third-party model, locally; results must not leak private names)
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`, then `src/easy_verifier/core/gate.py` (`detect_pick_gates`) and
   `src/easy_verifier/core/roles.py` (`resolve`)
7. Read the 2026-10-15 "Jev / Laya revisit" entry at the end of `memory/decisions.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-15: "for scoring, let investigate the way to integrate something like jev, laya, or some
model to evaluate the point to scoring" → after the investigation: "yes, plan T104".

**Restated intent**:
> Measure, on our own repositories, whether Laya (local, offline, Apache-2.0 decision model) can answer
> the engine's **detect-gate pick questions** ("which candidate file fills role X?") accurately, with
> calibrated confidence and low latency, compared with the LLM and simple baselines. The output is
> numbers and an adopt/reject recommendation — **not** an integration.

**Why picks first**: they are the only gate question with an **objective label available for free**.
For every role the rules *did* fill, hide the rule's answer and ask the model to pick from the same
candidate shape group; the rule-resolved file is the label. That gives a labelled set with no human
labelling and no LLM-as-truth. They also fit Laya's sweet spot (`choice`, < 20 options, short text).

**Out of scope**:
- Any change to `src/`, the engine, the MCP server, the container, or `pyproject.toml` dependencies
  (NFR-001 / FR-040: the engine makes no model call — this task does not touch that).
- `gate_evaluations`, reference/review gates, citation pre-screening (no objective label; follow-up only
  if picks clearly win).
- Jev: hosted, so repository content would leave the machine. Run Jev **only** if the user supplies an
  early-access key **and** only on the public fixture repos; otherwise mark it N/A. Never send a
  private repo's content to any network service.
- Shipping or vendoring model weights.

**Requirement Refs**: NFR-001 and FR-040 (constraint to preserve), FR-034 (detect picks), FR-037
(confidence), FR-022 (replay — the adoption design must keep it; noted in the report, not built).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-15)
- [x] Domain terms align with `PROJECT_SPEC.md` (role, pick, detect gate, agent input)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `Standalone — N/A: experiment harness under experiments/t104_laya/, run by hand; nothing in src/ calls it`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | `experiments/t104_laya/build_dataset.py` builds a pick-question set from a list of repo paths by calling `easy_verifier.core` functions directly (no edits to them): for each role the rules filled, one question = role + candidate list of that role's shape group (cap 20, label always included, order shuffled with a fixed seed), label = rule-resolved path. Writes JSONL to a git-ignored directory (`.local/t104/`). Deterministic: the same repos give byte-identical output |
| 2 | Each question's text fits Laya's 512-token budget (count with the model's tokenizer); over-budget questions are truncated by dropping candidates furthest from the label **only in a counted, reported way** — or skipped and counted. No silent drop |
| 3 | `experiments/t104_laya/evaluate.py` scores any answer file against labels: top-1 accuracy, ECE (10 bins), p50/p95 latency, coverage-at-confidence ≥ 0.8, per repo and overall. Pure Python, no torch import |
| 4 | Baselines in the same report: random (1/k), filename-similarity heuristic (role name vs path tokens), Laya zero-shot, Laya fine-tuned **leave-one-repo-out** (train on all other repos, test on the held-out one; temperature refit on the training side only — never on the test repo) |
| 5 | LLM baseline: the harness writes a **questions-only** file (no labels). The Supervisor has a separate agent answer it at Stage 4 and scores it with `evaluate.py`. The implementing agent must not produce LLM answers |
| 6 | Repos: the public fixtures plus the real repos listed in `.local/real-repos.md` (aliases only in any tracked file). Report the question count per repo |
| 7 | Results report at `docs/experiments/T104_laya_picks.md` (git-ignored, local): table of all baselines × metrics, CPU p50 latency, model load time and RAM, failure examples **by alias only**, and an adopt/reject recommendation against the pre-registered bar below |
| 8 | Tests `tests/test_t104_experiment_harness.py` cover AC1 (determinism, label always in candidates, cap 20), AC2 (over-budget handling counted), AC3 (accuracy/ECE on a hand-computed toy file), AC10 (unknown model and missing key exit non-zero naming it; `jev` refuses a non-allow-listed repo; `random`/`heuristic` produce the shared answer format). They must run **without** torch/laya installed. The T100 identifier guard still passes |
| 9 | Laya, torch and transformers are installed only into a separate experiment venv (`.local/t104/venv`); `pyproject.toml` is unchanged. Network check (PyPI reachable) before installing; on failure stop and report |

| 10 | **The model is a parameter.** One runner, `experiments/t104_laya/run.py --model <name> --questions <jsonl> --out <answers.jsonl> [--train <jsonl>]`, behind one small backend interface: `answer(question) -> {choice, confidence, latency_ms}`, plus optional `fit(train_questions)`. Backends: `random`, `heuristic`, `laya` (zero-shot), `laya-ft` (fine-tuned via `fit`), `jev` (needs `TYPESAFE_API_KEY`; refuses to start unless every question's repo is on a public-fixture allow-list — test this refusal). An unknown `--model` or a missing key exits non-zero naming it. Adding a model = one new backend file + one registry line; `evaluate.py` never changes per model. Every backend writes the same answer format, so the LLM baseline (AC5) uses it too |

### Pre-registered adoption bar (decided now, before any number is seen)

Recommend "adopt as an optional agent-side judge" only if **all** hold on the leave-one-repo-out test:
- fine-tuned top-1 accuracy ≥ the LLM baseline − 0.02, and ≥ 0.85 absolute;
- ECE ≤ 0.10;
- CPU p50 ≤ 200 ms per question.
Otherwise "reject" or "not yet" with the deciding metric named. Do not move the bar after seeing results.

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- The report exists with every cell of the baseline × metric table filled (N/A cells justified).
- Tests in AC8 pass without the experiment venv; full suite and ruff stay green.

### Verification Command (exact, runnable)

`.venv` is broken (system Python 3.14). Use a py3.12 venv with the project installed, e.g.
`uv venv -p /usr/bin/python3.12 <dir> && VIRTUAL_ENV=<dir> uv pip install -e '.[dev]'`, then:

```bash
<py312> -m pytest -q tests/test_t104_experiment_harness.py
<py312> -m pytest -q          # long: run in the background
<py312> -m ruff check src tests experiments
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T104.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T104.md`. BEFORE = `ls experiments/` failing (no harness) and the
> 2026-10-15 decisions.md entry stating the bar is unmeasured.

---

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/gate.py:detect_pick_gates` — reuse its role/shape
grouping and candidate selection exactly; the dataset must mirror what the gate would really ask.

1. Dataset builder (AC1–2) and evaluator (AC3) first, test-first, with no ML dependency.
2. Simple baselines (random, filename heuristic) through the evaluator — proves the pipeline end to end.
3. The backend interface + registry and `run.py --model` (AC10), proven with `random` and
   `heuristic` before any ML backend exists.
4. Experiment venv, `laya` zero-shot, then `laya-ft` leave-one-repo-out (use Laya's documented
   fine-tune path; if none is documented, stop and report rather than inventing one). `jev` only if
   the user supplies a key; otherwise its row is N/A.
5. Write the questions-only file for the LLM baseline; hand back to the Supervisor.
6. Report.

Real-repo runs are long: run them in the background and never two at once.

---

## Edge Case Checklist

- [ ] A role with exactly one candidate: not a question (trivial) — count and exclude
- [ ] Label not in the shape group's candidates (rule filled it by a path the generic pattern misses) — count and exclude, report the count
- [ ] Repo with zero filled roles → zero questions, reported, not an error
- [ ] Same file is the label for two roles — both questions kept
- [ ] Leakage: identical questions across repos (vendored files) — dedupe across the train/test split
- [ ] Non-Latin paths — the English checkpoint collapses on non-Latin scripts; count them
- [ ] Secret-bearing files never appear as candidates (`detect_pick_gates` excludes `credential-file`; assert it)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `experiments/t104_laya/build_dataset.py` | new — question set builder |
| `experiments/t104_laya/evaluate.py` | new — metrics |
| `experiments/t104_laya/run.py` | new — `--model` runner + backend registry |
| `experiments/t104_laya/backends/` | new — `random`, `heuristic`, `laya`, `laya_ft`, `jev` (ML imports inside the backend only) |
| `experiments/t104_laya/README.md` | new — how to reproduce |
| `tests/test_t104_experiment_harness.py` | new |
| `.gitignore` | add `/.local/t104/` only if `.local/` is not already ignored |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/` | NFR-001: no model in the engine; this is measurement only |
| `pyproject.toml` | ML dependencies stay out of the product |
| `compose.yaml`, `Dockerfile`, `scripts/` | out of scope |

---

## Test Plan

Unit tests on a tiny synthetic repo built in `tmp_path` for the builder; a hand-computed toy answer
file for accuracy/ECE. Real-repo and model runs are evidence in the report, not tests.

---

## Completion Checklist

- [ ] Implementation done, committed on the branch
- [ ] AC8 tests pass and their output is pasted into `tasks/TASK_REVIEW_T104.md`
- [ ] Report written with every table cell filled
- [ ] Questions-only file handed to the Supervisor for the LLM baseline (AC5)
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
