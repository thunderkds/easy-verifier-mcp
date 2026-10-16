"""Laya zero-shot: the shipped English checkpoint, CPU, one forward pass each.

The question is a Laya ``choice`` whose options are the candidate paths with
their headings as descriptions; the state is the role name. ``head_max_len``
is raised from the shipped 192 to :data:`HEAD_MAX_LEN` (a documented runtime
knob) so 20 options are not trimmed: the builder's 512-token budget is then
the only budget. Confidence is ``answer_confidence`` (the temperature-scaled
probability of the chosen option, the field Laya documents as calibrated).
Load time and peak RSS go to stderr for the report.
"""

from __future__ import annotations

import resource
import sys
import time

MODEL = "convaiinnovations/laya"
HEAD_MAX_LEN = 496
QUESTION_KEY = "pick"


def laya_question(question: dict) -> tuple[dict, dict]:
    """``(state, questions)`` in Laya's request shape."""
    return (
        {"source role": question["role"]},
        {
            QUESTION_KEY: {
                "type": "choice",
                "instructions": "Which file in this repository fills the source "
                f"role \"{question['role']}\"?",
                "criteria": {
                    c["path"]: c["heading"] or c["path"] for c in question["candidates"]
                },
            }
        },
    )


def load_agent(model_dir: str):
    import laya
    import torch

    torch.manual_seed(0)
    started = time.perf_counter()
    agent = laya.load(model_dir, device="cpu")
    agent.cfg["head_max_len"] = HEAD_MAX_LEN
    print(
        f"laya load_s={time.perf_counter() - started:.2f} "
        f"maxrss_MB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024}",
        file=sys.stderr,
    )
    return agent


class LayaBackend:
    def __init__(self) -> None:
        from laya.train import resolve_checkpoint_dir

        self.base_dir = resolve_checkpoint_dir(MODEL)
        self.agent = load_agent(self.base_dir)

    def answer(self, question: dict) -> dict:
        state, questions = laya_question(question)
        answer = self.agent.predict(state, questions)["answers"][QUESTION_KEY]
        return {"choice": answer["choice"],
                "confidence": float(answer["answer_confidence"])}
