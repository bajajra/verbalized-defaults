"""Tests for the IFEval metadata -> Spec adapter."""
import pytest

from verbalized_defaults import GIVEN, Keyword, LengthConstraint, Structure, Wrapper, verify_spec
from verbalized_defaults.ifeval_adapter import spec_from_ifeval


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


def test_unmappable_ids_are_reported_not_silently_dropped():
    res = spec_from_ifeval(
        ["keywords:letter_frequency", "detectable_format:title", "change_case:english_lowercase"],
        [{"letter": "a", "let_frequency": 5, "let_relation": "at least"}, {}, {}],
    )
    assert res.spec.case == "lower"
    assert {iid for iid, _ in res.unmapped} == {"keywords:letter_frequency", "detectable_format:title"}
    assert res.total == 3


def test_partial_mappings_are_flagged():
    res = spec_from_ifeval(
        ["detectable_format:multiple_sections"],
        [{"num_sections": 3, "section_spliter": "SECTION"}],
    )
    assert res.spec.delimiters == ["SECTION"]
    assert [iid for iid, _ in res.partial] == ["detectable_format:multiple_sections"]
