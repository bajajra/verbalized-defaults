"""Keyword verifiers: must_include and forbidden.

Two deliberately *different* matching policies, from the taxonomy's A4 analysis:

* must_include -- word-boundary, case-insensitive (IFEval's keywords:existence).
  Inflections do NOT count: requiring "correlated" is not satisfied by
  "correlation". This is the required-token direction.

* forbidden -- substring, case-insensitive. Morphological containment DOES
  count: banning "engage" also fires on "engages". This is the strict choice
  that catches derived-form leakage (a real A4 failure). NOTE: it can also
  produce cross-lingual false positives ("heute" inside German "heutige" -- a
  Bucket-B artifact). Kept configurable via ``substring=False`` for the
  word-boundary policy when that risk matters.
"""
from __future__ import annotations

import re

from ..schema import Keyword
from .base import SlotResult


def _wb_count(text: str, needle: str) -> int:
    return len(re.findall(r"\b" + re.escape(needle) + r"\b", text, flags=re.IGNORECASE))


def check_must_include(text: str, keywords: list[Keyword]) -> SlotResult:
    shortfalls = []
    for kw in keywords:
        n = _wb_count(text, kw.text)
        if n < kw.min_count:
            shortfalls.append(f"{kw.text!r} ({n}/{kw.min_count})")
    ok = not shortfalls
    return SlotResult(
        "must_include", ok,
        [f"{k.text}>={k.min_count}" for k in keywords],
        "all present" if ok else f"short: {shortfalls}",
    )


def check_forbidden(text: str, words: list[str], substring: bool = True) -> SlotResult:
    low = text.lower()
    if substring:
        hits = [w for w in words if w.lower() in low]
    else:
        hits = [w for w in words if _wb_count(text, w) > 0]
    ok = not hits
    return SlotResult(
        "forbidden", ok, f"none of {words}",
        "clean" if ok else f"present: {hits}",
    )
