"""Tests for the IFEval metadata -> Spec adapter."""
import pytest

from verbalized_defaults import (
    GIVEN,
    Keyword,
    LengthConstraint,
    Positional,
    Structure,
    Wrapper,
    verify_spec,
)
from verbalized_defaults.ifeval_adapter import CONSTRAINED_RESPONSE_OPTIONS, spec_from_ifeval


def test_length_relations_translate_exactly():
    # 'at least' is inclusive; 'less than' is strict, so the inclusive form is v-1.
    at_least = spec_from_ifeval(
        ["length_constraints:number_words"], [{"num_words": 300, "relation": "at least"}])
    assert at_least.spec.length_words == LengthConstraint.at_least(300, "words")

    less_than = spec_from_ifeval(
        ["length_constraints:number_sentences"], [{"num_sentences": 5, "relation": "less than"}])
    assert less_than.spec.length_sentences == LengthConstraint.at_most(4, "sentences")


def test_unknown_relation_raises():
    with pytest.raises(ValueError):
        spec_from_ifeval(["length_constraints:number_words"],
                         [{"num_words": 10, "relation": "roughly"}])


def test_case_structure_language_wrappers():
    res = spec_from_ifeval(
        ["change_case:english_lowercase", "detectable_format:number_bullet_lists",
         "language:response_language", "startend:quotation", "startend:end_checker"],
        [{}, {"num_bullets": 3}, {"language": "fr"}, {}, {"end_phrase": "THE END"}],
    )
    s = res.spec
    assert s.case == "lower"
    assert s.structure == Structure("bullets", 3)
    assert s.language == "fr"
    assert s.wrappers == Wrapper(quotes=True, end="THE END")
    assert not res.unmapped


def test_keywords_and_no_comma_accumulate():
    res = spec_from_ifeval(
        ["keywords:existence", "keywords:forbidden_words", "punctuation:no_comma",
         "keywords:frequency"],
        [{"keywords": ["alpha", "beta"]}, {"forbidden_words": ["bad"]}, {},
         {"keyword": "gamma", "frequency": 3, "relation": "at least"}],
    )
    s = res.spec
    assert s.must_include == [Keyword("alpha"), Keyword("beta"), Keyword("gamma", 3)]
    assert s.forbidden == ["bad", ","]


def test_postscript_marker_is_verifiable_end_to_end():
    """The P.S. marker must survive adapter -> verifier (regression: word boundaries)."""
    res = spec_from_ifeval(["detectable_content:postscript"], [{"postscript_marker": "P.S."}])
    assert res.spec.must_include == [Keyword("P.S.")]
    assert verify_spec("Here is the answer.\n\nP.S. one more thing", res.spec).ok
    assert not verify_spec("Here is the answer with no postscript", res.spec).ok


def test_repeat_prompt_maps_to_response_boundary():
    res = spec_from_ifeval(["combination:repeat_prompt"], [{"prompt_to_repeat": "Write a poem."}])
    assert res.spec.response_boundary == "Write a poem."
    assert verify_spec("Write a poem. Roses are red...", res.spec).ok


def test_everything_is_tagged_given():
    res = spec_from_ifeval(
        ["change_case:english_capital", "length_constraints:number_paragraphs"],
        [{}, {"num_paragraphs": 4}],
    )
    assert set(res.spec.provenance.values()) == {GIVEN}


def test_only_letter_arithmetic_is_unmapped():
    """Schema v2 covers every IFEval family except Bucket-C letter arithmetic."""
    res = spec_from_ifeval(
        ["keywords:letter_frequency", "detectable_format:title", "change_case:english_lowercase"],
        [{"letter": "a", "let_frequency": 5, "let_relation": "at least"}, {}, {}],
    )
    assert res.spec.case == "lower"
    assert res.spec.wrappers == Wrapper(title=True)
    assert {iid for iid, _ in res.unmapped} == {"keywords:letter_frequency"}
    assert res.total == 3


def test_multiple_sections_maps_fully_with_splitter():
    res = spec_from_ifeval(
        ["detectable_format:multiple_sections"],
        [{"num_sections": 3, "section_spliter": "SECTION"}],
    )
    assert res.spec.structure == Structure("sections", 3, "SECTION")
    assert res.spec.delimiters == ["SECTION"]
    assert not res.partial and not res.unmapped
    body = "intro SECTION 1 alpha SECTION 2 beta SECTION 3 gamma"
    assert verify_spec(body, res.spec).ok


def test_structure_slot_conflict_is_reported_as_partial():
    """Only one structure slot exists; a second claim on it is a real limit."""
    res = spec_from_ifeval(
        ["detectable_format:number_bullet_lists", "combination:two_responses"],
        [{"num_bullets": 3}, {}],
    )
    assert res.spec.structure == Structure("bullets", 3)
    assert [iid for iid, _ in res.partial] == ["combination:two_responses"]


def test_markup_dimensions_map_and_verify():
    res = spec_from_ifeval(
        ["detectable_format:number_highlighted_sections",
         "detectable_content:number_placeholders",
         "change_case:capital_word_frequency"],
        [{"num_highlights": 2}, {"num_placeholders": 1},
         {"capital_frequency": 2, "capital_relation": "at least"}],
    )
    m = res.spec.markup
    assert m.highlights == LengthConstraint.at_least(2, "highlights")
    assert m.placeholders == LengthConstraint.at_least(1, "placeholders")
    assert m.caps_words == LengthConstraint.at_least(2, "caps_words")
    good = "*one* and *two* with [a placeholder] plus NASA and FBI"
    assert verify_spec(good, res.spec).ok
    assert not verify_spec("plain text with nothing special", res.spec).ok


def test_two_responses_maps_to_structure_responses():
    res = spec_from_ifeval(["combination:two_responses"], [{}])
    assert res.spec.structure == Structure("responses", 2, "******")
    assert verify_spec("first answer\n******\nsecond answer", res.spec).ok
    assert not verify_spec("only one answer", res.spec).ok
    # IFEval requires the two responses to differ
    assert not verify_spec("same\n******\nsame", res.spec).ok


def test_constrained_response_maps_to_options():
    res = spec_from_ifeval(["detectable_format:constrained_response"], [{}])
    assert res.spec.response_options == CONSTRAINED_RESPONSE_OPTIONS
    assert verify_spec("My answer is maybe.", res.spec).ok
    assert not verify_spec("Perhaps.", res.spec).ok


def test_nth_paragraph_first_word_maps_fully():
    res = spec_from_ifeval(
        ["length_constraints:nth_paragraph_first_word"],
        [{"num_paragraphs": 2, "nth_paragraph": 2, "first_word": "However"}],
    )
    assert res.spec.positional == Positional(2, "However")
    assert not res.partial
    assert verify_spec("First para.\n\nHowever, the second.", res.spec).ok
    assert not verify_spec("First para.\n\nTherefore, the second.", res.spec).ok


def test_keyword_frequency_upper_bound_maps():
    res = spec_from_ifeval(
        ["keywords:frequency"],
        [{"keyword": "very", "frequency": 3, "relation": "less than"}],
    )
    # strict "less than 3" -> inclusive ceiling of 2
    assert res.spec.must_include == [Keyword("very", 0, 2)]
    assert verify_spec("very very good", res.spec).ok
    assert not verify_spec("very very very good", res.spec).ok
