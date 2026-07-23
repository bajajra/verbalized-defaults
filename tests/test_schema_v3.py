"""Schema v3: the decomposed `register` and the content-policy slot.

The point of the decomposition is that two things move from *unscoreable prose*
to *programmatic predicates* -- grammatical person, and the surface-checkable
content rules. These tests pin that, and pin the separation between scored and
judge-only halves.
"""
import pytest

from verbalized_defaults import ContentPolicy, Spec, SpecValidationError, validate_spec, verify_spec
from verbalized_defaults.spec_extract import extract_spec
from verbalized_defaults.verifiers.persona import check_content_policy, check_person


def test_person_is_programmatic():
    assert check_person("The author argues that it matters.", "third").ok
    # a single "I" breaks third person even if third-person pronouns dominate
    assert not check_person("They argue it matters. I agree with them.", "third").ok
    assert check_person("I think this is right.", "first").ok
    assert check_person("You should try this.", "second").ok


def test_person_validated_against_enum():
    validate_spec(Spec(person="third"))
    with pytest.raises(SpecValidationError):
        validate_spec(Spec(person="fourth"))


def test_content_policy_programmatic_checks():
    p = ContentPolicy(no_urls=True, no_emoji=True, no_profanity=True, no_first_person=True)
    assert check_content_policy("A clean sentence about bees.", p).ok
    assert not check_content_policy("See https://example.com for more.", p).ok
    assert not check_content_policy("Bees are great 🐝", p).ok
    assert not check_content_policy("That is a damn shame.", p).ok
    assert not check_content_policy("I really like bees.", p).ok


def test_scored_and_judge_halves_are_separated():
    """content_policy scores; content_rules never does."""
    spec = Spec(content_policy=ContentPolicy(no_urls=True),
                content_rules=["No political statements."],
                tone="objective", audience="general public")
    rep = verify_spec("Bees pollinate most flowering plants.", spec)
    hard = {r.slot for r in rep.hard_results}
    soft = {r.slot for r in rep.results if r.skipped}
    assert "content_policy" in hard
    assert {"content_rules", "tone", "audience"} <= soft
    assert rep.ok


def test_extractor_pulls_the_decomposed_slots_from_english():
    ex = extract_spec(
        "Write in the third person.\n"
        "Keep the tone objective.\n"
        "Use plain language with no jargon.\n"
        "No external links or URLs.\n"
        "No political statements.\n"
    )
    s = ex.spec
    assert s.person == "third"
    assert s.tone == "objective"
    assert s.jargon_level == "simple"
    assert s.content_policy is not None and s.content_policy.no_urls
    assert s.content_rules and "political" in s.content_rules[0].lower()


def test_decomposition_raises_extraction_coverage():
    """These lines used to be 100% unextractable; now they type."""
    text = ("Write in the third person.\nKeep the tone objective.\n"
            "No external links.\nAvoid jargon.\n")
    assert extract_spec(text).coverage == 1.0
