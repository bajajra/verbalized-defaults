"""Metric parity tests -- these pin our counts to IFEval's tokenization."""
from verbalized_defaults.metrics import count_paragraphs, count_sentences, count_words


def test_count_words_is_regexp_w_tokens_not_whitespace():
    # \w+ tokenization, NOT whitespace split.
    assert count_words("don't") == 2               # don, t
    assert count_words("state-of-the-art") == 4    # state, of, the, art
    assert count_words("Hello, world!") == 2
    assert count_words("one two three") == 3


def test_count_sentences_punkt():
    assert count_sentences("Hello world. How are you? I am fine!") == 3
    # Punkt does not split on the abbreviation dot.
    assert count_sentences("Dr. Smith went home.") == 1


def test_count_paragraphs_blank_line_only():
    assert count_paragraphs("a\n\nb\n\nc") == 3
    assert count_paragraphs("a\nb\nc") == 1          # single newlines != new paragraph
    assert count_paragraphs("  \n\n one \n\n two \n\n") == 2
