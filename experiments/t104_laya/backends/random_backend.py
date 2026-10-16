"""Chance baseline: a seeded uniform pick at confidence 1/k."""

from __future__ import annotations

import random


class RandomBackend:
    def __init__(self, seed: int = 104) -> None:
        self.seed = seed

    def answer(self, question: dict) -> dict:
        candidates = question["candidates"]
        rng = random.Random(f"{self.seed}|{question['id']}")
        return {"choice": rng.choice(candidates)["path"],
                "confidence": 1 / len(candidates)}
