"""Kev (Jared Palmer, Apache-2.0), self-hosted: our own ``kev.serve``.

Speaks the same ``POST /v1/systemone`` protocol as Jev. No repo allow-list: the
server is ours (this machine or a host we run), so private content stays on it.
Environment: ``KEV_BASE_URL`` (default ``http://127.0.0.1:8009``), ``KEV_MODEL``
(default ``kev-0.8b``, sent as the request's ``model``), optional ``KEV_API_KEY``
(bearer header only when set). Refuses to start when the server is unreachable.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from . import BackendError
from .jev_backend import QUESTION_KEY, choice_body

DEFAULT_BASE_URL = "http://127.0.0.1:8009"
DEFAULT_MODEL = "kev-0.8b"
TIMEOUT_S = 600  # CPU inference on a 20-option question can be slow


class KevBackend:
    def __init__(self) -> None:
        base = os.environ.get("KEV_BASE_URL") or DEFAULT_BASE_URL
        self.base = base.rstrip("/")
        self.model = os.environ.get("KEV_MODEL") or DEFAULT_MODEL
        self.headers = {"content-type": "application/json"}
        if os.environ.get("KEV_API_KEY"):
            self.headers["authorization"] = f"Bearer {os.environ['KEV_API_KEY']}"
        print(f"kev server: {self.base} (model {self.model})", file=sys.stderr)
        try:
            urllib.request.urlopen(
                urllib.request.Request(self.base, headers=self.headers), timeout=10
            ).close()
        except urllib.error.HTTPError:
            pass  # the server answered; any HTTP status proves it is up
        except (urllib.error.URLError, OSError) as error:
            raise BackendError(
                f"kev server unreachable at {self.base}: {error}"
            ) from error

    def answer(self, question: dict) -> dict:
        body = {**choice_body(question), "model": self.model}
        request = urllib.request.Request(
            self.base + "/v1/systemone",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self.headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                payload = json.load(response)
            answer = payload["answers"][QUESTION_KEY]
            choice = answer["choice"]
        except (OSError, ValueError, KeyError) as error:
            raise BackendError(
                f"kev request failed for question {question['id']} at {self.base}: "
                f"{type(error).__name__}: {error}"
            ) from error
        probabilities = answer.get("probabilities") or {}
        result = {
            "choice": choice,
            "confidence": probabilities.get(choice, answer.get("confidence", 0.0)),
        }
        if payload.get("latency_ms") is not None:
            result["latency_ms"] = float(payload["latency_ms"])
        return result
