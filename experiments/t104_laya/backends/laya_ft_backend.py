"""Laya fine-tuned through its documented path, ``laya.train.finetune``.

``fit`` writes the training questions as Laya ``{state, questions, expected}``
rows, fine-tunes the shipped English checkpoint, and loads the result. The
temperature refit happens inside ``finetune`` on a calibration slice of the
*training* rows only (``calib_frac``); the held-out repository never reaches
``fit``. Knobs are module constants so every fold trains the same way; the
run directory is keyed by a hash of the training file, so a fold is never
re-trained by accident and never shares weights with another fold.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from .laya_backend import HEAD_MAX_LEN, MODEL, LayaBackend, laya_question, load_agent

RUNS_DIR = Path(os.environ.get("T104_FT_DIR", ".local/t104/ft"))
EPOCHS = int(os.environ.get("T104_FT_EPOCHS", "4"))
MICRO_BATCH = 4
GRAD_ACCUM = 2
CALIB_FRAC = 0.25  # >= MIN_TYPE_N (10) calibration items at 40+ train items
MAX_ITEMS = int(os.environ.get("T104_FT_MAX_ITEMS", "0"))  # 0 = all; >0 only to time
FREEZE_ENCODER = os.environ.get("T104_FT_FREEZE_ENCODER") == "1"


class LayaFineTunedBackend(LayaBackend):
    def __init__(self) -> None:
        from laya.train import resolve_checkpoint_dir

        self.base_dir = resolve_checkpoint_dir(MODEL)
        self.agent = None

    def fit(self, train_questions: list[dict]) -> None:
        from laya.train import TrainConfig, finetune

        if MAX_ITEMS:
            train_questions = train_questions[:MAX_ITEMS]
        rows = []
        for question in train_questions:
            state, questions = laya_question(question)
            key = next(iter(questions))
            rows.append({"state": state, "questions": questions,
                         "expected": {key: question["label"]}})
        payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        settings = f"{EPOCHS}|{MICRO_BATCH}|{GRAD_ACCUM}|{CALIB_FRAC}|{FREEZE_ENCODER}"
        digest = hashlib.sha256((payload + settings).encode()).hexdigest()[:16]
        run_dir = RUNS_DIR / digest
        out_dir = run_dir / "checkpoint"
        if not (out_dir / "rl_agent_config.json").exists():
            run_dir.mkdir(parents=True, exist_ok=True)
            data = run_dir / "train.jsonl"
            data.write_text(payload, encoding="utf-8")
            config = TrainConfig(
                epochs=EPOCHS,
                micro_batch=MICRO_BATCH,
                grad_accum=GRAD_ACCUM,
                calib_frac=CALIB_FRAC,
                head_max_len=HEAD_MAX_LEN,
                freeze_encoder=FREEZE_ENCODER,
                log_every=10,
            )
            started = time.perf_counter()
            summary = finetune(str(data), self.base_dir, str(out_dir), config,
                               device="cpu")
            elapsed = time.perf_counter() - started
            record = {"train_s": elapsed, "n_train": len(rows), "summary": summary}
            (run_dir / "summary.json").write_text(
                json.dumps(record, default=str, indent=2), encoding="utf-8"
            )
            print(f"laya-ft train_s={elapsed:.1f} n_train={len(rows)} "
                  f"run={run_dir}", file=sys.stderr)
        self.agent = load_agent(str(out_dir))

    def answer(self, question: dict) -> dict:
        if self.agent is None:
            raise RuntimeError("laya-ft needs --train (fit) before answering")
        return super().answer(question)
