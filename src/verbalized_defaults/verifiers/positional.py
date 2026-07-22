"""Positional verifier: paragraph N must start with a given word.

Mirrors IFEval's nth_paragraph_first_word normalisation: take the first
whitespace token of the target paragraph, lowercase it, drop leading quotes, and
truncate at the first punctuation character, then compare.
"""
from __future__ import annotations

from ..metrics import split_paragraphs
from ..schema import Positional
from .base import SlotResult

_PUNCTUATION = {".", ",", "?", "!", "'", '"'}


def _normalise_first_word(paragraph: str) -> str:
    tokens = paragraph.split()
    if not tokens:
        return ""
    word = tokens[0].strip().lower().lstrip("'").lstrip('"')
    out = []
    for ch in word:
        if ch in _PUNCTUATION:
            break
        out.append(ch)
    return "".join(out)


def check_positional(text: str, p: Positional) -> SlotResult:
    paragraphs = split_paragraphs(text)
    if len(paragraphs) < p.paragraph:
        return SlotResult(
            "positional", False, p.describe(),
            f"only {len(paragraphs)} paragraphs",
            detail=f"paragraph {p.paragraph} does not exist",
        )
    got = _normalise_first_word(paragraphs[p.paragraph - 1])
    want = _normalise_first_word(p.first_word)
    ok = got == want
    return SlotResult("positional", ok, p.describe(), got or "(empty)")
