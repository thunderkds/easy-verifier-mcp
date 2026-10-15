"""T104 — answer pick questions with any registered model (AC10).

    python experiments/t104_laya/run.py --model NAME --questions Q.jsonl \
        --out ANSWERS.jsonl [--train TRAIN.jsonl]

Every backend writes the same answer record ``{id, model, choice, confidence,
latency_ms}``, so ``evaluate.py`` never changes per model. A backend class may
declare ``ALLOWED_REPOS``: the runner then refuses to start unless every
question's repo is on it (a hosted model never sees a private repo).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from backends import BackendError, load_backend
from evaluate import load_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--train", help="labelled questions for backends with fit()")
    args = parser.parse_args(argv)

    try:
        backend_class = load_backend(args.model)
        questions = load_jsonl(args.questions)
        allowed = getattr(backend_class, "ALLOWED_REPOS", None)
        if allowed is not None:
            refused = sorted({q["repo"] for q in questions} - allowed)
            if refused:
                raise BackendError(
                    f"model {args.model!r} refuses repos not on its public allow-list "
                    f"{sorted(allowed)}: {', '.join(refused)}"
                )
        backend = backend_class()
        if args.train:
            if not hasattr(backend, "fit"):
                raise BackendError(f"model {args.model!r} has no fit(); drop --train")
            backend.fit(load_jsonl(args.train))
        records = []
        for question in questions:
            started = time.perf_counter()
            result = backend.answer(question)
            measured = (time.perf_counter() - started) * 1000
            records.append(
                {
                    "id": question["id"],
                    "model": args.model,
                    "choice": result["choice"],
                    "confidence": float(result["confidence"]),
                    "latency_ms": result.get("latency_ms", measured),
                }
            )
    except BackendError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
