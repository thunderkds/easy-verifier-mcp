"""TypeSafe Jev (hosted). Public-fixture repos only; needs a key.

Speaks the ``POST /v1/systemone`` protocol (the one Laya's server mirrors).
``TYPESAFE_API_KEY`` and ``TYPESAFE_BASE_URL`` are both required; there is no
default endpoint. The runner enforces ``ALLOWED_REPOS`` before construction,
so a private repository's content never reaches the network.
"""

from __future__ import annotations

import json
import os
import urllib.request

from . import BackendError

QUESTION_KEY = "pick"


def choice_body(question: dict) -> dict:
    """The ``/v1/systemone`` request body shared by every Jev-protocol backend."""
    return {
        "state": {"role": question["role"]},
        "questions": {
            QUESTION_KEY: {
                "type": "choice",
                "instructions": "Which file in this repository fills the source "
                f"role \"{question['role']}\"?",
                "criteria": {
                    c["path"]: c["heading"] or c["path"]
                    for c in question["candidates"]
                },
            }
        },
    }


class JevBackend:
    ALLOWED_REPOS = frozenset({"easy-verifier-mcp"})

    def __init__(self) -> None:
        for name in ("TYPESAFE_API_KEY", "TYPESAFE_BASE_URL"):
            if not os.environ.get(name):
                raise BackendError(f"model 'jev' needs {name} in the environment")
        self.key = os.environ["TYPESAFE_API_KEY"]
        self.url = os.environ["TYPESAFE_BASE_URL"].rstrip("/") + "/v1/systemone"

    def answer(self, question: dict) -> dict:
        body = choice_body(question)
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json",
                     "authorization": f"Bearer {self.key}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            answer = json.load(response)["answers"][QUESTION_KEY]
        choice = answer["choice"]
        probabilities = answer.get("probabilities") or {}
        return {"choice": choice,
                "confidence": probabilities.get(choice, answer.get("confidence", 0.0))}
