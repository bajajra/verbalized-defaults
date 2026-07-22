"""Tests for the NL -> typed Spec extractor (the hybrid's core).

The most important test is the round trip: render a Spec as English, extract it
back, and check the constraints survive. If that fails the hybrid design does not
work, because the verifier would be checking something different from what the
model declared.
"""
from verbalized_defaults import Keyword, LengthConstraint, Spec, Structure, verify_spec
from verbalized_defaults.spec_extract import extract_spec
from verbalized_defaults.spec_nl import format_spec_natural


def test_round_trip_through_english():
    original = Spec(
        length_words=LengthConstraint.at_least(300, "words"),
        case="lower",
        structure=Structure("bullets", 3),
        forbidden=[","],
    )
    got = extract_spec(format_spec_natural(original)).spec
    assert got.length_words == LengthConstraint.at_least(300, "words")
    assert got.case == "lower"
    assert got.structure == Structure("bullets", 3)
    assert got.forbidden == [","]


def test_length_phrasings():
    cases = [
        ("Write at least 300 words.", LengthConstraint.at_least(300, "words")),
        ("Keep it under 150 words.", LengthConstraint.at_most(150, "words")),
        ("Aim for 200-250 words.", LengthConstraint.between(200, 250, "words")),
        # hedged -> +/-10% window, not a point value
        ("About 400 words.", LengthConstraint.between(360, 440, "words")),
        ("Exactly 400 words.", LengthConstraint.eq(400, "words")),
        ("300+ words.", LengthConstraint.at_least(300, "words")),
    ]
    for line, expected in cases:
        assert extract_spec(line).spec.length_words == expected, line


def test_units_are_distinguished():
    s = extract_spec("Write at least 5 sentences.\nUse exactly 3 paragraphs.").spec
    assert s.length_sentences == LengthConstraint.at_least(5, "sentences")
    assert s.length_paragraphs == LengthConstraint.eq(3, "paragraphs")
    assert s.length_words is None


def test_case_variants():
    assert extract_spec("Write entirely in lowercase.").spec.case == "lower"
    assert extract_spec("Use ALL CAPS throughout.").spec.case == "upper"
    assert extract_spec("Use Title Case for the heading.").spec.case == "title"
    assert extract_spec("Standard capitalization.").spec.case == "standard"


def test_structure_and_forbidden():
    s = extract_spec("Use 5 bullet points.\nDo not use any commas.").spec
    assert s.structure == Structure("bullets", 5)
    assert s.forbidden == [","]
    assert extract_spec("Output valid JSON only.").spec.structure == Structure("json")


def test_keywords_quoted():
    s = extract_spec('Include the word "photosynthesis".\nAvoid the word "utilize".').spec
    assert s.must_include == [Keyword("photosynthesis")]
    assert s.forbidden == ["utilize"]


def test_language_and_markup():
    assert extract_spec("Write the response in French.").spec.language == "fr"
    s = extract_spec("Include at least 3 highlighted sections.").spec
    assert s.markup is not None and s.markup.highlights is not None


def test_unextracted_lines_are_reported_not_dropped():
    """Coverage must be measurable, never silently assumed."""
    ex = extract_spec("Write at least 100 words.\nBe warm and encouraging in tone.")
    assert len(ex.extracted) == 1
    assert len(ex.unextracted) == 1
    assert 0.0 < ex.coverage < 1.0


def test_extracted_spec_is_actually_verifiable():
    """End to end: English -> Spec -> verifier verdict."""
    spec = extract_spec("Write in lowercase.\nUse exactly 2 bullet points.").spec
    assert verify_spec("- one item here\n- two items here", spec).ok
    assert not verify_spec("- One Item\n- Two\n- Three", spec).ok


def test_empty_declaration_is_harmless():
    ex = extract_spec("")
    assert ex.coverage == 0.0
    assert ex.spec.provenance == {}
