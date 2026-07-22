"""The `other` slot: stated constraints on dimensions with no latent default.

The load-bearing invariant: a typed slot exists iff its dimension carries a
latent default, so a typed slot may be [given] OR [assumed]; `other` holds
constraints that exist only because the prompt said so, and can therefore only
ever be [given]. An [assumed] entry in `other` is a category error.
"""
import pytest

from verbalized_defaults import (
    ASSUMED,
    GIVEN,
    Spec,
    SpecValidationError,
    parse_spec,
    format_spec,
    validate_spec,
    verify_spec,
)
from verbalized_defaults.ifeval_adapter import spec_from_ifeval


def test_other_cannot_be_assumed_validator():
    spec = Spec(other=["every word must be a palindrome"], provenance={"other": ASSUMED})
    with pytest.raises(SpecValidationError):
        validate_spec(spec)


def test_other_can_be_given():
    spec = Spec(other=["every word must be a palindrome"], provenance={"other": GIVEN})
    validate_spec(spec)  # must not raise


def test_parser_rejects_assumed_other():
    res = parse_spec('<spec>\nother: "words must be palindromes" [assumed]\n</spec>')
    assert any("can only be [given]" in e for e in res.errors)
    # it is still recovered, tagged given, so downstream code sees the constraint
    assert res.spec.other == ["words must be palindromes"]
    assert res.spec.provenance["other"] == GIVEN


def test_other_round_trips():
    spec = Spec(other=["no consecutive repeated letters", "answer must be a palindrome"],
                provenance={"other": GIVEN})
    reparsed = parse_spec(format_spec(spec))
    assert reparsed.ok, reparsed.errors
    assert reparsed.spec.other == spec.other


def test_other_is_excluded_from_rexec_scoring():
    """Carried for binding, but it must not inflate or deflate the exec reward."""
    spec = Spec(case="lower", other=["must be a palindrome"], provenance={"other": GIVEN})
    report = verify_spec("all lowercase text here", spec)
    assert report.ok and report.score == 1.0
    other_result = next(r for r in report.results if r.slot == "other")
    assert other_result.skipped
    assert other_result not in report.hard_results


def test_adapter_carries_untyped_constraints_into_other():
    """Binding must not silently lose a constraint just because it has no slot."""
    res = spec_from_ifeval(
        ["keywords:letter_frequency", "change_case:english_lowercase"],
        [{"letter": "a", "let_frequency": 5, "let_relation": "at least"}, {}],
    )
    assert res.spec.case == "lower"
    assert res.spec.other and "letter_frequency" in res.spec.other[0]
    assert res.spec.provenance["other"] == GIVEN


def test_adapter_carries_unknown_ifbench_families_into_other():
    res = spec_from_ifeval(
        ["words:palindrome", "length_constraints:number_words"],
        [{}, {"num_words": 40, "relation": "at least"}],
    )
    # typed where a default exists (word count is a default-bearing dimension)...
    assert res.spec.length_words is not None
    # ...carried in `other` where it does not (palindromicity has no prior)
    assert res.spec.other == ["words:palindrome"]
    assert [iid for iid, _ in res.unmapped] == ["words:palindrome"]


def test_ifbench_ids_are_not_yet_recognised():
    """Known gap: the adapter speaks IFEval's id vocabulary only.

    IFBench's count:word_count_range IS a default-bearing dimension (word count)
    and should occupy the typed length_words slot, but the adapter does not know
    the IFBench id, so it falls through to `other`. Binding still sees it, but it
    gets no verifier. Fixing this needs an IFBench id map -- it adds no new slot
    and no expressive power, only vocabulary. Documented in activity/0009.
    """
    res = spec_from_ifeval(["count:word_count_range"], [{"min_words": 30, "max_words": 40}])
    assert res.spec.length_words is None
    assert res.spec.other and "word_count_range" in res.spec.other[0]
