"""Response-options verifier: the answer must be one of a fixed option set.

Matches IFEval's constrained_response semantics -- the response must *contain*
one of the allowed option strings exactly (not merely paraphrase it).
"""
from __future__ import annotations

from .base import SlotResult


def check_response_options(text: str, options: list[str]) -> SlotResult:
    hit = next((o for o in options if o in text), None)
    return SlotResult(
        "response_options", hit is not None, f"one of {options}",
        hit if hit is not None else "no option present",
    )
