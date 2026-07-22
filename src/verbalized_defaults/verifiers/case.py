"""Case verifier.

The taxonomy's A2 lesson: case must be checked across *every zone* -- prose,
headers, bullet labels, proper nouns, and the "P.S." prefix -- not just the
format-mandated bits. So 'lower' means literally no uppercase letter anywhere
(a single capitalized proper noun or a "P.S." fails), and 'upper' the reverse.
"""
from __future__ import annotations

from typing import Callable

from .base import SlotResult


def _first_offender(text: str, pred: Callable[[str], bool], width: int = 15) -> str:
    for i, ch in enumerate(text):
        if pred(ch):
            lo, hi = max(0, i - width), min(len(text), i + width + 1)
            return f"first at char {i} ({ch!r}): ...{text[lo:hi]!r}..."
    return ""


def _check_title(text: str) -> tuple[bool, list[str]]:
    bad = []
    for tok in text.split():
        alpha = [c for c in tok if c.isalpha()]
        if alpha and not alpha[0].isupper():
            bad.append(tok)
    return (not bad), bad


def check_case(text: str, mode: str) -> SlotResult:
    if mode == "standard":
        return SlotResult("case", True, "standard", "standard", detail="no case constraint")

    if mode == "lower":
        offenders = sum(1 for c in text if c.isupper())
        ok = offenders == 0
        return SlotResult(
            "case", ok, "all-lowercase",
            "clean" if ok else f"{offenders} uppercase char(s)",
            detail="" if ok else _first_offender(text, str.isupper),
        )

    if mode == "upper":
        offenders = sum(1 for c in text if c.islower())
        ok = offenders == 0
        return SlotResult(
            "case", ok, "all-uppercase",
            "clean" if ok else f"{offenders} lowercase char(s)",
            detail="" if ok else _first_offender(text, str.islower),
        )

    if mode == "title":
        ok, bad = _check_title(text)
        return SlotResult(
            "case", ok, "title-case",
            "clean" if ok else f"{len(bad)} non-title word(s)",
            detail="" if ok else f"e.g. {bad[:3]}",
        )

    raise ValueError(f"unknown case mode {mode!r}")
