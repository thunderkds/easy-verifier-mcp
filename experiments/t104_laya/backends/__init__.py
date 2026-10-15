"""Backend registry. Adding a model = one backend file + one line here.

A backend is a class with a no-argument constructor and
``answer(question) -> {"choice": path, "confidence": float[, "latency_ms"]}``,
plus an optional ``fit(train_questions)``. Targets are imported lazily so a
model's heavy dependencies (torch, laya) load only when that model runs.
"""

from __future__ import annotations

import importlib

REGISTRY = {
    "random": "backends.random_backend:RandomBackend",
    "heuristic": "backends.heuristic_backend:HeuristicBackend",
    "laya": "backends.laya_backend:LayaBackend",
    "laya-ft": "backends.laya_ft_backend:LayaFineTunedBackend",
    "jev": "backends.jev_backend:JevBackend",
}


class BackendError(Exception):
    """A refusal the runner reports and exits non-zero on."""


def load_backend(name: str):
    if name not in REGISTRY:
        raise BackendError(f"unknown model {name!r}; known: {', '.join(REGISTRY)}")
    module_name, _, class_name = REGISTRY[name].partition(":")
    return getattr(importlib.import_module(module_name), class_name)
