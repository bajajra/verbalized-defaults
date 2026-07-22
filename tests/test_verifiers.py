"""Verifier tests, anchored to the failure taxonomy's named failure modes."""
import pytest

from verbalized_defaults import (
    ASSUMED,
    Keyword,
    LengthConstraint,
    Spec,
    SpecValidationError,
    Structure,
    Wrapper,
    validate_spec,
    verify_spec,
)
from verbalized_defaults.verifiers.case import check_case
from verbalized_defaults.verifiers.keywords import check_forbidden, check_must_include
from verbalized_defaults.verifiers.length import check_length
from verbalized_defaults.verifiers.structure import check_delimiters, check_structure
from verbalized_defaults.verifiers.wrappers import check_response_boundary, check_wrappers


# --- length ---------------------------------------------------------------
def test_length_words_range():
    assert check_length("length_words", "one two three four five", LengthConstraint.between(4, 6)).ok
    assert not check_length("length_words", "one two three", LengthConstraint.between(4, 6)).ok


def test_length_sentences_floor():
    # Real sentences: Punkt (like IFEval) splits these into 4, but would merge
    # "A. B. C." as abbreviations -- so we use full sentences on purpose.
    text = "The sky is blue. Grass is green. Water is wet. Fire is hot."
    assert check_length("length_sentences", text, LengthConstraint.at_least(4)).ok
    assert not check_length("length_sentences", text, LengthConstraint.at_least(5)).ok


# --- case: the A2 taxonomy cases -----------------------------------------
def test_case_lower_flags_ps_prefix():
    # "P.S." must be recased in a lowercase response (taxonomy A2).
    assert check_case("thanks for reading.\n\np.s. see you soon.", "lower").ok
    assert not check_case("thanks for reading.\n\nP.S. see you soon.", "lower").ok


def test_case_lower_flags_proper_noun():
    assert not check_case("we visited Paris in may.", "lower").ok
    assert check_case("we visited paris in may.", "lower").ok


def test_case_upper():
    assert check_case("STOP RIGHT THERE", "upper").ok
    assert not check_case("STOP right THERE", "upper").ok


def test_case_standard_is_noop():
    assert check_case("Whatever Casing Here", "standard").ok


# --- structure: the A3 global-vs-per-unit case ---------------------------
def test_structure_bullets_global_count():
    three_total = "- a\n- b\n- c"
    nine_per_stanza = "\n".join("- x" for _ in range(9))
    assert check_structure(three_total, Structure("bullets", 3)).ok
    # 3-per-stanza across 3 stanzas = 9 bullets, must fail an "exactly 3" spec.
    assert not check_structure(nine_per_stanza, Structure("bullets", 3)).ok


def test_structure_prose_rejects_bullets():
    assert check_structure("just a sentence.", Structure("prose")).ok
    assert not check_structure("- a bullet", Structure("prose")).ok


def test_structure_json():
    assert check_structure('```json\n{"a": 1}\n```', Structure("json")).ok
    assert not check_structure("not json", Structure("json")).ok


def test_delimiter_off_by_one():
    # need six stars, response has five -> must fail (A3 delimiter miscount).
    assert check_delimiters("block1\n******\nblock2", ["******"]).ok
    assert not check_delimiters("block1\n*****\nblock2", ["******"]).ok


# --- keywords: the A4 inflection / leakage cases -------------------------
def test_must_include_inflection_does_not_count():
    assert not check_must_include("the correlation is strong", [Keyword("correlated")]).ok
    assert check_must_include("the variables are correlated", [Keyword("correlated")]).ok


def test_forbidden_catches_morphological_leakage():
    # banning "engage" fires on "engages" (substring policy).
    assert not check_forbidden("she engages fully", ["engage"]).ok
    assert check_forbidden("she participates fully", ["engage"]).ok
    # word-boundary policy would let "engages" through.
    assert check_forbidden("she engages fully", ["engage"], substring=False).ok


# --- wrappers / boundary -------------------------------------------------
def test_wrappers_quotes_and_end():
    assert check_wrappers('"hello there"', Wrapper(quotes=True)).ok
    assert not check_wrappers("hello there", Wrapper(quotes=True)).ok
    assert check_wrappers("... and that is the end", Wrapper(end="the end")).ok


def test_response_boundary_prefix():
    assert check_response_boundary("Answer: 42 and so on", "Answer:").ok
    assert not check_response_boundary("Sure! Answer: 42", "Answer:").ok


# --- anti-gaming schema validation ---------------------------------------
def test_assumed_length_rejects_vacuous_range():
    spec = Spec(length_words=LengthConstraint.between(10, 10000),
                provenance={"length_words": ASSUMED})
    with pytest.raises(SpecValidationError):
        validate_spec(spec)


def test_assumed_length_allows_point_and_tight_range():
    validate_spec(Spec(length_words=LengthConstraint.eq(300),
                       provenance={"length_words": ASSUMED}))
    validate_spec(Spec(length_words=LengthConstraint.between(100, 110),
                       provenance={"length_words": ASSUMED}))


def test_structure_requires_count():
    with pytest.raises(SpecValidationError):
        validate_spec(Spec(structure=Structure("bullets")))


# --- aggregate report: hard gate + dense score ---------------------------
def test_verify_spec_report_ok_and_score():
    spec = Spec(
        case="lower",
        structure=Structure("bullets", 2),
        must_include=[Keyword("banana")],
        register="playful",  # soft slot, excluded from score
    )
    good = "- i like banana bread\n- bananas are great"
    report = verify_spec(good, spec)
    assert report.ok
    assert report.score == 1.0
    # register is reported but skipped (does not inflate the hard-slot count).
    assert any(r.slot == "register" and r.skipped for r in report.results)

    bad = "- I Like Cake\n- and more cake\n- extra bullet"
    rep2 = verify_spec(bad, spec)
    assert not rep2.ok
    assert rep2.score < 1.0
    failed = {r.slot for r in rep2.failures()}
    assert "case" in failed and "structure" in failed and "must_include" in failed
