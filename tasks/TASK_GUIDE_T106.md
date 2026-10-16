# TASK_GUIDE — T106: Add Kev (self-hosted, Jev-compatible) alongside Laya in the T104 harness and measure it on the pick questions
**Date**: 2026-10-16
**Complexity Level**: C1
**Risk Level**: Medium (private repository content is sent to a model server — our own, local or on a host we run; results must not leak private names)
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
5. Apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `tasks/TASK_GUIDE_T104.md` (the harness contract and the pre-registered bar this task reuses),
   `experiments/t104_laya/README.md`, `experiments/t104_laya/backends/__init__.py` and
   `experiments/t104_laya/backends/jev_backend.py` (Kev speaks the same protocol)
7. Read the 2026-10-16 "T104 verdict" entry at the end of `memory/decisions.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16: "hey, how about using kev" → "add kev alongside with laya, my idea is that, run the
model from local or the host and we can use it by our own".

**Restated intent**:
> Add **Kev** (Jared Palmer, Apache-2.0, open-weight Jev-style decision model, `github.com/jaredpalmer/kev`)
> as one more `--model` in the T104 harness, next to `laya`. Kev runs on a server **we** run —
> `python -m kev.serve` on this machine or on a host we own — and the backend talks to it over
> `POST /v1/systemone` at a configurable base URL. Then measure it on the same 56 pick questions with
> the same evaluator and the same pre-registered bar as T104, and say adopt / not yet / reject.

**Facts checked 2026-10-16 (README of `jaredpalmer/kev`)**: not on PyPI (`pip install kev` is an
unrelated package) — install from source with `uv sync --extra serve`, Python 3.12/3.13; serve with
`uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.8b --port 8009 --device cpu`
(binds 127.0.0.1 by default); HF ids `jaredpalmer/kev-{0.8b,4b,9b,27b}` (tag `v1.0`); request
`{state, model, questions:{id:{type:"choice", instructions, criteria:{option: description|null}}}}`;
choice answer `{choice, probabilities, confidence}`, response top-level `latency_ms`. CPU fp32 by
default, `KEV_DTYPE=bf16` halves memory. **This machine has no GPU** (no `nvidia-smi`).

**Out of scope**:
- Any change to `src/`, the engine, the MCP server, the container, `pyproject.toml` (NFR-001, FR-040).
- Kev fine-tuning (`kev.train`) — zero-shot first; fine-tune only in a follow-up if zero-shot is promising
  (user 2026-10-16: a sample is enough for experiments).
- Kev on OpenRouter or any third-party host — "our own" server only.
- Kev-9B / 27B (no GPU). Kev-4B only as a small sample, if 0.8B finishes and RAM allows.
- Vendoring weights or Kev's source into this repo.

**Requirement Refs**: NFR-001 and FR-040 (constraint to preserve), FR-034 (detect picks), FR-037
(confidence), FR-022 (replay — noted in the report, not built).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md` (role, pick, detect gate, agent input)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T104
**Entry point**: `Standalone — N/A: experiment harness under experiments/t104_laya/, run by hand; nothing in src/ calls it`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | `--model kev` is registered: one new backend file `experiments/t104_laya/backends/kev_backend.py` + one `REGISTRY` line. `evaluate.py`, `run.py` and the other backends are unchanged except for sharing the `/v1/systemone` request code with `jev` if that removes duplication (behaviour of `jev` byte-identical, its tests unchanged and green) |
| 2 | The backend reads `KEV_BASE_URL` (default `http://127.0.0.1:8009`), `KEV_MODEL` (default `kev-0.8b`, sent as the request's `model`), optional `KEV_API_KEY` (bearer header only if set). Same request shape as `jev` (`choice`, criteria = candidate path → heading or `null`); answer `confidence` = `probabilities[choice]`, falling back to `confidence`; `latency_ms` = the server's `latency_ms` when present (inference time, comparable to Laya's), else the runner's measured time |
| 3 | Local **or** host: no repo allow-list (it is our server), but the backend prints the target base URL to stderr once at start, and refuses (non-zero exit naming the URL) when the server is unreachable at construction (a `GET`/`POST` probe) — never a silent all-wrong answer file |
| 4 | Tests in `tests/test_t104_experiment_harness.py` (extend, do not fork) run **without** Kev, torch or network: a stub `/v1/systemone` server on `127.0.0.1` (stdlib `http.server`, ephemeral port) proves the request shape, the `KEV_MODEL`/`KEV_API_KEY` handling, the shared answer format, the server-latency pickup, and the unreachable-URL refusal. T100 guard still green |
| 5 | Kev is installed only under `.local/t106/` (git-ignored: source clone + its own uv env); `pyproject.toml` unchanged. Network check (GitHub + Hugging Face reachable) before installing; on failure stop and report |
| 6 | Real run: `kev.serve` with `jaredpalmer/kev-0.8b` on CPU, answering all 56 questions in `.local/t104/questions.jsonl` (reuse the T104 worktree's `.local/t104/` data — copy, don't rebuild), scored by `evaluate.py`. Kev-4B on a sample of ≤ 15 questions only if 0.8B completed and free RAM allows (bf16). Server load time and peak RSS recorded |
| 7 | Report: append a "Kev" section to the local report `docs/experiments/T104_laya_picks.md` (git-ignored): Kev rows in the same baseline × metric table (top-1, ECE, p50/p95 server latency, coverage ≥ 0.8), per-repo comparison against LLM/Laya/heuristic, failures by alias only, and a verdict against the **unchanged** T104 bar (top-1 ≥ LLM − 0.02 and ≥ 0.85; ECE ≤ 0.10; CPU p50 ≤ 200 ms). Zero-shot Kev is judged against the bar directly — the bar is not moved |
| 8 | `experiments/t104_laya/README.md` gains a "Kev (self-hosted)" section: install from source, the exact `kev.serve` command for local and for a host (`--host 0.0.0.0` only on a trusted network; point `KEV_BASE_URL` at it), and the run/evaluate commands |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- `run.py --model kev` against a real `kev.serve` produces 56 answers with 0 missing / 0 invalid.
- The report has every Kev cell filled (N/A justified).
- New tests pass without Kev installed; full suite and ruff stay green.

### Verification Command (exact, runnable)

Use the T104 test venv (py3.12, project installed, no torch): `.local/t104/testvenv` in the T104
worktree, or create one with `uv venv -p /usr/bin/python3.12 <dir> && VIRTUAL_ENV=<dir> uv pip install -e '.[dev]'`.

```bash
<py312> -m pytest -q tests/test_t104_experiment_harness.py
<py312> -m pytest -q          # long: run in the background
<py312> -m ruff check src tests experiments
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T106.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T106.md`. BEFORE = `run.py --model kev` failing with
> `error: unknown model 'kev'; known: random, heuristic, laya, laya-ft, jev` (exit 2).

---

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `experiments/t104_laya/backends/jev_backend.py` — same protocol; Kev is the
self-hosted twin, so share the request/parse code rather than copying it.

1. Capture BEFORE (`--model kev` unknown, exit 2).
2. Test-first with a stdlib stub server (AC4), then the backend + registry line (AC1–3).
3. Network check; clone Kev into `.local/t106/kev`, `uv sync --extra serve` (AC5).
4. Start `kev.serve --run jaredpalmer/kev-0.8b --device cpu --port 8009` **in the background**, wait
   for it to answer, run the 56 questions, stop the server. Never two model servers at once.
5. Optional Kev-4B sample (AC6). 6. README + report (AC7–8).

---

## Edge Case Checklist

- [ ] Server returns a `choice` that is not one of the candidate paths → recorded as-is; `evaluate.py` counts it invalid (do not "fix" it in the backend)
- [ ] `probabilities` missing → fall back to `confidence`, then 0.0
- [ ] Server unreachable at start → non-zero exit naming the URL (AC3)
- [ ] Server error mid-run (HTTP 5xx / timeout) → non-zero exit naming the question id; no partial answer file written as if complete
- [ ] Candidate paths with spaces / non-ASCII (`Alternative Dispute Resolution.json` exists in node-monorepo) survive the JSON round-trip
- [ ] `KEV_API_KEY` unset → no `authorization` header at all

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `experiments/t104_laya/backends/kev_backend.py` | new |
| `experiments/t104_laya/backends/__init__.py` | one `REGISTRY` line |
| `experiments/t104_laya/backends/jev_backend.py` | only if sharing the `/v1/systemone` code; behaviour unchanged |
| `experiments/t104_laya/README.md` | Kev section |
| `tests/test_t104_experiment_harness.py` | Kev tests with a stub server |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/` | NFR-001: no model in the engine |
| `pyproject.toml` | model deps stay out of the product |
| `experiments/t104_laya/evaluate.py`, `run.py` | "adding a model = one backend file + one registry line" (T104 AC10) |
| `compose.yaml`, `Dockerfile`, `scripts/` | out of scope |

---

## Test Plan

Stub `/v1/systemone` server in a thread on an ephemeral `127.0.0.1` port; drive `run.py --model kev`
end to end against it with `KEV_BASE_URL` set. Real Kev runs are evidence in the report, not tests.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T106-kev-backend`
- [ ] AC4 tests pass; output pasted into `tasks/TASK_REVIEW_T106.md`
- [ ] Real Kev-0.8B run on all 56 questions scored; report section written
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
