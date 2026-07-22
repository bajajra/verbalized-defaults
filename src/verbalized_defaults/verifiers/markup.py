"""Markup verifier: emphasis spans, placeholders, and ALL-CAPS words.

Counting logic mirrors IFEval's checkers exactly:

* highlights   -- ``*single*`` and ``**double**`` spans with non-empty content
                  (IFEval's HighlightSectionChecker counts both forms).
* placeholders -- ``[bracketed]`` spans (non-greedy).
* caps_words   -- word-tokenised tokens where ``token.isupper()``.

Like ``wrappers``, this is one slot bundling several dimensions: it passes only
if every declared dimension passes, and names the ones that failed.
"""
from __future__ import annotations

import re

import nltk

from ..metrics import _ensure_punkt
from ..schema import Markup
from .base import SlotResult

_HIGHLIGHT_RE = re.compile(r"\*[^\n\*]*\*")
_DOUBLE_HIGHLIGHT_RE = re.compile(r"\*\*[^\n\*]*\*\*")
_PLACEHOLDER_RE = re.compile(r"\[.*?\]")


def count_highlights(text: str) -> int:
    n = 0
    for span in _HIGHLIGHT_RE.findall(text):
        if span.strip("*"):
            n += 1
    for span in _DOUBLE_HIGHLIGHT_RE.findall(text):
        if span.removeprefix("**").removesuffix("**"):
            n += 1
    return n


def count_placeholders(text: str) -> int:
    return len(_PLACEHOLDER_RE.findall(text))


def count_caps_words(text: str) -> int:
    _ensure_punkt()
    return sum(1 for tok in nltk.word_tokenize(text) if tok.isupper())


_COUNTERS = {
    "highlights": count_highlights,
    "placeholders": count_placeholders,
    "caps_words": count_caps_words,
}


def check_markup(text: str, m: Markup) -> SlotResult:
    observed: dict[str, int] = {}
    failures: list[str] = []
    for name, constraint in m.dimensions():
        n = _COUNTERS[name](text)
        observed[name] = n
        if not constraint.satisfied_by(n):
            failures.append(f"{name}={n} (want {constraint.describe()})")
    ok = not failures
    return SlotResult(
        "markup", ok, m.describe(), observed,
        detail="" if ok else "; ".join(failures),
    )
