"""Spec block parsing / serialisation tests."""
from verbalized_defaults import ASSUMED, GIVEN, Keyword, LengthConstraint, Spec, Structure, Wrapper
from verbalized_defaults.spec_text import extract_spec_block, format_spec, parse_spec

CANONICAL = """<spec>
length_words: 300 [assumed]
length_sentences: >=5 [given]
case: lower [given]
structure: bullets=3 [given]
delimiters: "******" [given]
must_include: "banana"x2, "apple" [given]
forbidden: "utilize" [given]
wrappers: quotes, end="THE END" [given]
language: en [assumed]
register: playful [assumed]
response_boundary: "Answer:" [given]
</spec>"""


def test_parse_canonical_block():
    res = parse_spec(CANONICAL)
    assert res.ok, res.errors
    s = res.spec
    assert s.length_words == LengthConstraint.eq(300, "words")
    assert s.length_sentences == LengthConstraint.at_least(5, "sentences")
    assert s.case == "lower"
    assert s.structure == Structure("bullets", 3)
    assert s.delimiters == ["******"]
    assert s.must_include == [Keyword("banana", 2), Keyword("apple", 1)]
    assert s.forbidden == ["utilize"]
    assert s.wrappers == Wrapper(quotes=True, end="THE END")
    assert s.language == "en"
    assert s.register == "playful"
    assert s.response_boundary == "Answer:"
    assert s.provenance["length_words"] == ASSUMED
    assert s.provenance["case"] == GIVEN


def test_round_trip():
    original = Spec(
        length_words=LengthConstraint.between(280, 320, "words"),
        length_paragraphs=LengthConstraint.eq(3, "paragraphs"),
        case="standard",
        structure=Structure("sections", 4),
        must_include=[Keyword("photosynthesis")],
        wrappers=Wrapper(start="Dear reader"),
        language="en",
        provenance={"length_words": ASSUMED, "case": ASSUMED, "structure": GIVEN,
                    "must_include": GIVEN, "wrappers": GIVEN, "language": ASSUMED,
                    "length_paragraphs": GIVEN},
    )
    reparsed = parse_spec(format_spec(original))
    assert reparsed.ok, reparsed.errors
    got = reparsed.spec
    assert got.length_words == original.length_words
    assert got.length_paragraphs == original.length_paragraphs
    assert got.structure == original.structure
    assert got.must_include == original.must_include
    assert got.wrappers == original.wrappers
    assert got.provenance == original.provenance


def test_extract_block_from_surrounding_text():
    text = "Some reasoning first.\n" + CANONICAL + "\nThen the answer."
    body = extract_spec_block(text)
    assert body is not None and "length_words" in body


def test_errors_are_collected_not_raised():
    res = parse_spec("""<spec>
length_words: 300
bogus_slot: 5 [given]
case: lower [given]
case: upper [given]
length_sentences: many [given]
</spec>""")
    joined = " | ".join(res.errors)
    assert "missing a [given]/[assumed] tag" in joined   # length_words untagged
    assert "unknown slot" in joined                       # bogus_slot
    assert "duplicate slot" in joined                     # case twice
    assert "cannot parse length" in joined                # "many"
    # despite the errors, the recoverable slots still parsed
    assert res.spec.case == "lower"
    assert res.spec.length_words == LengthConstraint.eq(300, "words")


def test_none_markers_leave_slot_unset():
    res = parse_spec("""<spec>
must_include: — [assumed]
forbidden: none [assumed]
case: standard [assumed]
</spec>""")
    assert res.ok, res.errors
    assert res.spec.must_include is None
    assert res.spec.forbidden is None
    assert res.spec.case == "standard"


def test_proposal_style_aliases():
    # the illustrative format in the proposal: 'length: ~300 words' and 'audience:'
    res = parse_spec("""<spec>
length: ~300 words [assumed]
audience: middle school [given]
</spec>""")
    assert res.ok, res.errors
    assert res.spec.length_words == LengthConstraint.eq(300, "words")
    assert res.spec.register == "middle school"
    assert res.spec.provenance["register"] == GIVEN
