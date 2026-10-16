# T104 — Laya vs LLM on detect-gate pick questions

A measurement harness, not an integration: nothing in `src/` calls it, and the engine still
makes no model call (NFR-001, FR-040). Guide: `tasks/TASK_GUIDE_T104.md`.

## What a question is

For every doc- or config-shaped role the rules **did** fill, the builder hides the rule's answer
and asks "which candidate fills role X?" over the candidates `detect_pick_gates` would offer for
that shape (files owned by no other role, eligible, secret-bearing excluded). The rule-resolved
file is the label (the shallowest one when the rules found several; the role's other files are
left out so there is one correct answer). Cap 20 with the label always kept; order shuffled with a
fixed seed. Every exclusion is counted in `stats.jsonl`: label outside the shape's extensions,
trivial (one candidate), skipped over the 512-token budget, candidates dropped for the budget
(furthest from the label in sorted-path order), non-Latin text.

## Reproduce

Two virtual environments (the project `.venv` is not used; system Python is 3.14):

```bash
# tests: no torch, no laya
uv venv -p /usr/bin/python3.12 .local/t104/testvenv
VIRTUAL_ENV=.local/t104/testvenv uv pip install -e '.[dev]'
.local/t104/testvenv/bin/python -m pytest -q tests/test_t104_experiment_harness.py

# experiment: CPU torch + laya, never in pyproject.toml
uv venv -p /usr/bin/python3.12 .local/t104/venv
VIRTUAL_ENV=.local/t104/venv uv pip install torch --index-url https://download.pytorch.org/whl/cpu
VIRTUAL_ENV=.local/t104/venv uv pip install laya
VIRTUAL_ENV=.local/t104/venv uv pip install -e .
```

Build the questions (`ALIAS=PATH`, aliases only — real paths live in `.local/real-repos.md`):

```bash
PY=.local/t104/venv/bin/python
$PY experiments/t104_laya/build_dataset.py --out-dir .local/t104 \
    --tokenizer convaiinnovations/laya --repo easy-verifier-mcp=$PWD --repo ALIAS=PATH ...
```

Answer and score, any model (`random`, `heuristic`, `laya`, `laya-ft`, `jev`, `kev`):

```bash
$PY experiments/t104_laya/run.py --model laya --questions .local/t104/questions.jsonl \
    --out .local/t104/answers/laya.jsonl
$PY experiments/t104_laya/evaluate.py --questions .local/t104/questions.jsonl \
    --answers .local/t104/answers/laya.jsonl
```

`laya-ft` is leave-one-repo-out: the builder also writes `loro/train_<alias>.jsonl` /
`loro/test_<alias>.jsonl` (identical questions across repos removed from train), then `run.py --model laya-ft --train ...`
per held-out repo. Temperature is refit on the training side only.

`jev` needs `TYPESAFE_API_KEY` and `TYPESAFE_BASE_URL` and refuses to start unless every
question's repo is on its public allow-list (`easy-verifier-mcp` only).

## Kev (self-hosted)

[Kev](https://github.com/jaredpalmer/kev) (Apache-2.0) is an open-weight Jev-style model that speaks
the same `POST /v1/systemone` protocol. The server is **ours** (this machine or a host we run), so
there is no repo allow-list; the backend prints the target URL to stderr and exits non-zero naming
it if the server is unreachable. Not on PyPI: install from source, outside this repo's environment
(`.local/` is git-ignored; Python 3.12/3.13).

```bash
git clone https://github.com/jaredpalmer/kev.git .local/t106/kev && cd .local/t106/kev
uv sync --extra serve
# local, CPU (binds 127.0.0.1 only)
uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.8b --port 8009 --device cpu
# on a host we own: add --host 0.0.0.0 ONLY on a trusted network, then point KEV_BASE_URL at it
```

`KEV_DTYPE=bf16` halves CPU weight memory. Then, from the repo root, with one model server at a time:

```bash
export KEV_BASE_URL=http://127.0.0.1:8009   # default; KEV_MODEL=kev-0.8b (default); KEV_API_KEY optional
$PY experiments/t104_laya/run.py --model kev --questions .local/t104/questions_only.jsonl \
    --out .local/t106/answers/kev08.jsonl
$PY experiments/t104_laya/evaluate.py --questions .local/t104/questions.jsonl \
    --answers .local/t106/answers/kev08.jsonl
```

`latency_ms` is the server's own `latency_ms` (inference time, comparable to Laya's) when present.

## LLM baseline (AC5)

`questions_only.jsonl` is the same file without labels. A separate agent answers it, one JSON
line per question, in the shared answer format, and the Supervisor scores it with `evaluate.py`:

```json
{"id": "<question id>", "model": "llm", "choice": "<one candidate path>", "confidence": 0.0, "latency_ms": null}
```

`confidence` is the answerer's probability (0–1) that `choice` is correct. `latency_ms` may be
`null`; the evaluator then reports latency as N/A rather than inventing it.

## Adding a model

One backend file under `backends/` (a class with `answer(question)` returning `choice` and
`confidence`, optionally `fit(train_questions)` and `ALLOWED_REPOS`) plus one line in
`backends/__init__.py:REGISTRY`. `evaluate.py` never changes.
