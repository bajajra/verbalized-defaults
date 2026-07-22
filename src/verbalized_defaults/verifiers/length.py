"""Length verifiers: words / sentences / paragraphs, at IFEval parity."""
from __future__ import annotations

from ..metrics import count_paragraphs, count_sentences, count_words
from ..schema import LengthConstraint
from .base import SlotResult

_COUNTERS = {
    "length_words": count_words,
    "length_sentences": count_sentences,
    "length_paragraphs": count_paragraphs,
}


def check_length(slot: str, text: str, c: LengthConstraint) -> SlotResult:
    n = _COUNTERS[slot](text)
    if c.op == "eq":
        ok, expected = n == c.value, f"== {c.value}"
    elif c.op == "min":
        ok, expected = n >= c.value, f">= {c.value}"
    elif c.op == "max":
        ok, expected = n <= c.value, f"<= {c.value}"
    elif c.op == "range":
        ok, expected = c.lo <= n <= c.hi, f"{c.lo}..{c.hi}"
    else:
        raise ValueError(f"unknown length op {c.op!r}")
    unit = slot.removeprefix("length_")
    return SlotResult(
        slot=slot,
        ok=ok,
        expected=expected,
        observed=n,
        detail=f"measured {n} {unit}, expected {expected}",
    )
