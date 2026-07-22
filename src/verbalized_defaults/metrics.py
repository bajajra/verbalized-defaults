"""IFEval-parity measurement primitives.

Every length metric here mirrors the exact tokenization the IFEval / IFBench
programmatic verifiers use, so our rewards score a response the same way the
benchmarks do. Divergence here re-introduces the taxonomy's "Bucket B"
evaluator-artifact failures (training against a checker that disagrees with the
benchmark), so treat these as frozen and pin them with tests.

Reference: google-research/instruction_following_eval/instructions_util.py
    count_words     -> nltk.tokenize.RegexpTokenizer(r"\\w+")   (NOT whitespace split)
    count_sentences -> nltk Punkt sentence tokenizer
Paragraphs follow the proposal's frozen rule: split on a blank line ("\\n\\n").
"""
from __future__ import annotations

import functools
import re

import nltk


@functools.lru_cache(maxsize=1)
def _word_tokenizer() -> "nltk.tokenize.RegexpTokenizer":
    return nltk.tokenize.RegexpTokenizer(r"\w+")


def count_words(text: str) -> int:
    """Word count matching IFEval: the number of r"\\w+" tokens.

    Note this differs from a naive whitespace split: "don't" -> 2 tokens,
    "state-of-the-art" -> 4 tokens. IFBench's count:word_count_range is scored
    this way, so this is the number our length_words verifier must agree with.
    """
    return len(_word_tokenizer().tokenize(text))


def _ensure_punkt() -> None:
    """Make the Punkt data available (nltk>=3.9 ships it as 'punkt_tab')."""
    for res in ("tokenizers/punkt_tab", "tokenizers/punkt"):
        try:
            nltk.data.find(res)
            return
        except LookupError:
            continue
    nltk.download("punkt_tab", quiet=True)
    nltk.download("punkt", quiet=True)


def count_sentences(text: str) -> int:
    """Sentence count matching IFEval's Punkt tokenizer."""
    _ensure_punkt()
    return len(nltk.sent_tokenize(text))


def split_paragraphs(text: str) -> list[str]:
    """Paragraphs = blocks separated by a blank line, empties dropped.

    Matches the IFEval convention flagged in the failure taxonomy (doc 435):
    a single "\\n" between blocks does NOT start a new paragraph; only "\\n\\n"
    (a blank line) does.
    """
    return [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def count_paragraphs(text: str) -> int:
    return len(split_paragraphs(text))
