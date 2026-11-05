"""Word error rate for the speech spike: (substitutions + deletions + insertions) / words
in the reference, after normalising case and punctuation."""

from __future__ import annotations

import re
import unicodedata

_KEEP = re.compile(r"[^a-z0-9' ]+")


def normalise(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    text = text.replace("-", " ")
    return [w.strip("'") for w in _KEEP.sub(" ", text).split() if w.strip("'")]


def word_errors(reference: str, hypothesis: str) -> tuple[int, int]:
    """Returns (edit distance in words, number of reference words)."""
    ref, hyp = normalise(reference), normalise(hypothesis)
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        current = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            current[j] = min(
                previous[j] + 1,  # deletion
                current[j - 1] + 1,  # insertion
                previous[j - 1] + (r != h),  # substitution or match
            )
        previous = current
    return previous[-1], len(ref)


def wer(reference: str, hypothesis: str) -> float:
    errors, words = word_errors(reference, hypothesis)
    return errors / words if words else float(errors > 0)
