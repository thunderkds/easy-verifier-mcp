"""Filename-similarity baseline: role-name stems found in the path.

Each hyphen-separated word of the role contributes its first four letters
(words shorter than four letters are skipped as too ambiguous, e.g. ``ci``);
the score is how many stems occur in the lower-cased path. Ties go to the
shallowest, then alphabetically first path. Confidence = 1 / number of
candidates tied at the top score (1/k when no stem matches anything).
"""

from __future__ import annotations

from pathlib import PurePosixPath


class HeuristicBackend:
    def answer(self, question: dict) -> dict:
        stems = [word[:4] for word in question["role"].split("-") if len(word) >= 4]
        paths = [c["path"] for c in question["candidates"]]
        scores = {p: sum(stem in p.lower() for stem in stems) for p in paths}
        best = max(scores.values())
        top = sorted((p for p in paths if scores[p] == best),
                     key=lambda p: (len(PurePosixPath(p).parts), p))
        return {"choice": top[0], "confidence": 1 / len(top)}
