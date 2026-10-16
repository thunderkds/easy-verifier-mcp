"""T104 — score any answer file against labelled pick questions.

Pure Python, no torch. Metrics per repo and overall: top-1 accuracy, ECE
(10 equal-width bins over the answer's confidence), p50/p95 latency
(nearest rank; ``None`` when no answer carries a latency), coverage and
accuracy at confidence >= 0.8. A missing answer or a choice outside the
candidates counts as wrong at confidence 0.

    python experiments/t104_laya/evaluate.py --questions Q.jsonl --answers A.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BINS = 10
THRESHOLD = 0.8


def load_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def ece(confidences: list[float], correct: list[bool], bins: int = BINS) -> float:
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for conf, ok in zip(confidences, correct, strict=True):
        buckets[min(int(conf * bins), bins - 1)].append((conf, ok))
    total = len(confidences)
    error = 0.0
    for bucket in buckets:
        if bucket:
            accuracy = sum(ok for _, ok in bucket) / len(bucket)
            mean_conf = sum(conf for conf, _ in bucket) / len(bucket)
            error += len(bucket) / total * abs(accuracy - mean_conf)
    return error


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def _metrics(rows: list[dict]) -> dict:
    n = len(rows)
    confs = [r["confidence"] for r in rows]
    correct = [r["correct"] for r in rows]
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    covered = [r for r in rows if r["confidence"] >= THRESHOLD]
    return {
        "n": n,
        "missing": sum(r["missing"] for r in rows),
        "invalid": sum(r["invalid"] for r in rows),
        "accuracy": sum(correct) / n,
        "ece": ece(confs, correct),
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "coverage_at_0_8": len(covered) / n,
        "accuracy_at_0_8": (
            sum(r["correct"] for r in covered) / len(covered) if covered else None
        ),
    }


def score(questions: list[dict], answers: list[dict]) -> dict:
    by_id = {a["id"]: a for a in answers}
    rows = []
    for question in questions:
        answer = by_id.get(question["id"])
        paths = {c["path"] for c in question["candidates"]}
        missing = answer is None
        invalid = not missing and answer.get("choice") not in paths
        ok = not missing and not invalid
        rows.append(
            {
                "repo": question["repo"],
                "missing": missing,
                "invalid": invalid,
                "correct": ok and answer["choice"] == question["label"],
                "confidence": float(answer["confidence"]) if ok else 0.0,
                "latency_ms": None if missing else answer.get("latency_ms"),
            }
        )
    if not rows:
        return {"overall": None, "per_repo": {}}
    repos = sorted({r["repo"] for r in rows})
    return {
        "overall": _metrics(rows),
        "per_repo": {repo: _metrics([r for r in rows if r["repo"] == repo])
                     for repo in repos},
    }


def _fmt(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--json", action="store_true", help="print the raw report")
    args = parser.parse_args(argv)
    report = score(load_jsonl(args.questions), load_jsonl(args.answers))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    keys = ["n", "missing", "invalid", "accuracy", "ece", "p50_ms", "p95_ms",
            "coverage_at_0_8", "accuracy_at_0_8"]
    print("| scope | " + " | ".join(keys) + " |")
    print("|" + "---|" * (len(keys) + 1))
    for scope, metrics in [("overall", report["overall"]), *report["per_repo"].items()]:
        if metrics:
            print(f"| {scope} | " + " | ".join(_fmt(metrics[k]) for k in keys) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
