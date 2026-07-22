"""Measured parity against the official IFEval implementation.

The rest of the suite pins our metrics to IFEval by *inspection* of its source.
This module pins them by *measurement*: it runs our counters and IFEval's own
counters over real IFEval prompt text plus a set of adversarial strings, and
requires exact agreement on every sample.

The reference implementation is downloaded, not vendored:

    uv run python scripts/fetch_ifeval_reference.py

If reference/ is absent these tests skip, so the suite stays runnable offline.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

from verbalized_defaults.metrics import count_sentences, count_words

REFERENCE_DIR = pathlib.Path(__file__).resolve().parent.parent / "reference"
_UTIL_PATH = REFERENCE_DIR / "instructions_util.py"
_DATA_PATH = REFERENCE_DIR / "ifeval_input_data.jsonl"

# Strings chosen to break naive implementations: contractions, hyphenates,
# abbreviations, decimals, markdown, unicode punctuation.
ADVERSARIAL = [
    "don't stop believing",
    "a state-of-the-art system",
    "Dr. Smith met Mr. Jones at 3 p.m. yesterday.",
    "The value is 3.14159 and rising.",
    "**bold** and _italic_ and `code`",
    "Hello world. How are you? I am fine!",
    "One\n\nTwo\n\nThree",
    "e.g. this, i.e. that; plus more!",
    "It costs $1,234.56 (roughly).",
    "naïve café résumé — em-dash test",
    "",
    "single",
]


def _load_reference():
    if not _UTIL_PATH.exists():
        pytest.skip("reference/instructions_util.py missing -- run scripts/fetch_ifeval_reference.py")
    spec = importlib.util.spec_from_file_location("ifeval_instructions_util", _UTIL_PATH)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"could not import IFEval reference: {exc}")
    return module


def _prompt_corpus(limit: int = 400) -> list[str]:
    if not _DATA_PATH.exists():
        return []
    texts = []
    with _DATA_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if prompt := row.get("prompt"):
                texts.append(prompt)
            if len(texts) >= limit:
                break
    return texts


def _corpus() -> list[str]:
    return ADVERSARIAL + _prompt_corpus()


def test_count_words_matches_ifeval_exactly():
    ref = _load_reference()
    mismatches = [
        (t[:60], count_words(t), ref.count_words(t))
        for t in _corpus()
        if count_words(t) != ref.count_words(t)
    ]
    assert not mismatches, f"{len(mismatches)} word-count mismatches, e.g. {mismatches[:5]}"


def test_count_sentences_matches_ifeval_exactly():
    ref = _load_reference()
    if not hasattr(ref, "count_sentences"):
        pytest.skip("reference has no count_sentences")
    corpus = [t for t in _corpus() if t.strip()]
    mismatches = [
        (t[:60], count_sentences(t), ref.count_sentences(t))
        for t in corpus
        if count_sentences(t) != ref.count_sentences(t)
    ]
    assert not mismatches, f"{len(mismatches)} sentence-count mismatches, e.g. {mismatches[:5]}"


def test_corpus_is_actually_substantial():
    """Guard against the parity tests silently passing on 12 strings."""
    if not _DATA_PATH.exists():
        pytest.skip("reference/ifeval_input_data.jsonl missing")
    assert len(_prompt_corpus()) >= 100
