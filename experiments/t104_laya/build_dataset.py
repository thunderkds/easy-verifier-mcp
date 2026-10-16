"""T104 — build detect-gate pick questions with free, objective labels.

For every role the rules *did* fill, hide the rule's answer and ask "which
candidate fills role X?" over the same shape group ``detect_pick_gates`` would
offer. The rule-resolved file is the label. Everything here reuses
``easy_verifier.core`` (``resolve``, the gate's walk, eligibility, shape
buckets and heading extraction) and edits none of it.

Usage (from the experiment venv; ``--tokenizer`` loads the model's tokenizer):

    python experiments/t104_laya/build_dataset.py --repo ALIAS=/abs/path ... \
        --out-dir .local/t104 --tokenizer convaiinnovations/laya
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from easy_verifier.core import gate
from easy_verifier.core.context import _is_secret_bearing, _resolved_repo, _walk
from easy_verifier.core.roles import GENERIC_PATTERNS, resolve, role

MAX_CANDIDATES = gate.MAX_CANDIDATES_PER_ROLE
TOKEN_BUDGET = 512
SEED = 104

SHAPES = (
    ("doc", gate._DOC_EXTENSIONS, gate._DOC_ROLES),
    ("config", gate._CONFIG_EXTENSIONS, gate._CONFIG_ROLES),
)


def render_question(question: dict) -> str:
    """The text a model reads; the token budget is counted over this."""
    lines = [
        f'Which file in this repository fills the source role "{question["role"]}"?',
        "Candidates:",
    ]
    for candidate in question["candidates"]:
        heading = candidate["heading"]
        lines.append(f"- {candidate['path']}" + (f" — {heading}" if heading else ""))
    return "\n".join(lines)


def _non_latin(text: str) -> bool:
    return any(ch.isalpha() and ord(ch) > 0x024F for ch in text)


def _label_order(path: str) -> tuple[int, str]:
    return (len(PurePosixPath(path).parts), path)


def build_questions(
    repo_path: str | Path,
    alias: str,
    *,
    count_tokens: Callable[[str], int],
    seed: int = SEED,
    budget: int = TOKEN_BUDGET,
) -> tuple[list[dict], dict]:
    """Questions for one repository plus counters for every exclusion."""
    root = _resolved_repo(repo_path)
    resolution = resolve(root, tuple(role(name) for name in sorted(GENERIC_PATTERNS)))
    owners: dict[str, set[str]] = {}
    for name, paths in resolution.files.items():
        for path in paths:
            owners.setdefault(path, set()).add(name)
    # The gate's own walk: contained only, eligible (secret-bearing excluded).
    walked = sorted(
        path
        for path in _walk(root, root, extensions=None, contained_only=True)
        if gate._eligible(root, path)
    )

    stats = {
        "repo": alias,
        "filled_roles": 0,
        "label_outside_shape": 0,
        "label_outside_shape_roles": [],
        "trivial": 0,
        "candidate_questions": 0,
        "skipped_over_budget": 0,
        "truncated_questions": 0,
        "dropped_candidates": 0,
        "non_latin": 0,
        "questions": 0,
    }
    questions: list[dict] = []
    for shape, extensions, bucket in SHAPES:
        shaped = [p for p in walked if Path(p).suffix.lower() in extensions]
        for name in sorted(bucket):
            filled = resolution.files.get(name) or ()
            if not filled:
                continue
            stats["filled_roles"] += 1
            # As if this role were unfilled: files owned by another role stay out.
            pool = [p for p in shaped if p in filled or not owners.get(p)]
            labels = sorted((p for p in filled if p in pool), key=_label_order)
            if not labels:
                stats["label_outside_shape"] += 1
                stats["label_outside_shape_roles"].append(name)
                continue
            label = labels[0]
            others = [p for p in pool if p not in filled]  # one correct answer
            if not others:
                stats["trivial"] += 1
                continue
            stats["candidate_questions"] += 1
            kept = sorted([label, *others[: MAX_CANDIDATES - 1]])
            question = _fit_budget(root, alias, name, shape, label, kept,
                                   count_tokens, budget, seed)
            if question is None:
                stats["skipped_over_budget"] += 1
                continue
            for candidate in question["candidates"]:
                assert not _is_secret_bearing(candidate["path"]), candidate
            if question["dropped_for_budget"]:
                stats["truncated_questions"] += 1
                stats["dropped_candidates"] += question["dropped_for_budget"]
            stats["non_latin"] += question["non_latin"]
            questions.append(question)
    stats["questions"] = len(questions)
    return questions, stats


def _fit_budget(root, alias, name, shape, label, kept, count_tokens, budget, seed):
    """Drop candidates furthest from the label (sorted-path order) until the
    rendered question fits; ``None`` if even label + one other does not."""
    headings = {path: gate._heading(root, path) for path in kept}
    at = kept.index(label)
    drop_order = sorted(
        (p for p in kept if p != label), key=lambda p: (-abs(kept.index(p) - at), p)
    )
    current = list(kept)
    order_rng = random.Random(f"{seed}|{alias}|{name}")
    shuffled = list(kept)
    order_rng.shuffle(shuffled)
    while True:
        present = set(current)
        question = {
            "id": f"{alias}:{name}",
            "repo": alias,
            "role": name,
            "shape": shape,
            "label": label,
            "candidates": [
                {"path": p, "heading": headings[p]} for p in shuffled if p in present
            ],
            "dropped_for_budget": len(kept) - len(current),
        }
        question["non_latin"] = _non_latin(render_question(question))
        if count_tokens(render_question(question)) <= budget:
            return question
        if len(current) <= 2:
            return None
        current.remove(drop_order[len(kept) - len(current)])


def questions_only(questions: Iterable[dict]) -> list[dict]:
    """The LLM-baseline input: everything but the label (AC5)."""
    return [{k: v for k, v in q.items() if k != "label"} for q in questions]


def _fingerprint(question: dict) -> tuple:
    return (
        question["role"],
        question["label"],
        tuple(sorted(c["path"] for c in question["candidates"])),
    )


def split_loro(questions: list[dict], held_out: str) -> tuple[list, list, int]:
    """Leave-one-repo-out: train on the others, minus any question identical
    to a test question (vendored files across repos would leak the label)."""
    test = [q for q in questions if q["repo"] == held_out]
    seen = {_fingerprint(q) for q in test}
    others = [q for q in questions if q["repo"] != held_out]
    train = [q for q in others if _fingerprint(q) not in seen]
    return train, test, len(others) - len(train)


def write_jsonl(path: str | Path, records: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def _tokenizer_counter(name: str) -> Callable[[str], int]:
    """Count with the checkpoint's own tokenizer (``<checkpoint>/tokenizer``)."""
    try:
        from laya.agent import _fix_tokenizer_config
        from laya.train import resolve_checkpoint_dir
        from transformers import AutoTokenizer
    except ImportError:
        sys.exit("--tokenizer needs laya + transformers: run from the experiment venv")
    model_dir = resolve_checkpoint_dir(name)
    _fix_tokenizer_config(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(str(Path(model_dir) / "tokenizer"))
    return lambda text: len(tokenizer(text)["input_ids"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", action="append", required=True,
                        metavar="ALIAS=PATH", help="repeatable")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--tokenizer", required=True,
                        help="Hugging Face id or local dir of the model tokenizer")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    count_tokens = _tokenizer_counter(args.tokenizer)
    out_dir = Path(args.out_dir)
    every: list[dict] = []
    all_stats = []
    for item in args.repo:
        alias, _, path = item.partition("=")
        if not alias or not path:
            parser.error(f"--repo needs ALIAS=PATH, got {item!r}")
        questions, stats = build_questions(path, alias, count_tokens=count_tokens,
                                           seed=args.seed)
        every.extend(questions)
        all_stats.append(stats)
        print(json.dumps(stats, sort_keys=True))
    write_jsonl(out_dir / "questions.jsonl", every)
    write_jsonl(out_dir / "questions_only.jsonl", questions_only(every))
    for stats in all_stats:
        train, test, stats["loro_train_deduped"] = split_loro(every, stats["repo"])
        write_jsonl(out_dir / "loro" / f"train_{stats['repo']}.jsonl", train)
        write_jsonl(out_dir / "loro" / f"test_{stats['repo']}.jsonl", test)
    write_jsonl(out_dir / "stats.jsonl", all_stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
