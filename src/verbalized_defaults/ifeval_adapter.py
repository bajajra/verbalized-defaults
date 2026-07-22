"""Map IFEval / IFBench instruction metadata into our typed ``Spec``.

This adapter does double duty:

1. **E0.1 oracle prefill** -- it builds the ground-truth spec to prefill into the
   model's thinking, from benchmark metadata rather than from a model.
2. **R_bind ground truth** -- it is the reference the model's own declared
   ``[given]`` slots are scored against.

Every slot it produces is tagged ``[given]``: by construction these constraints
came from the prompt.

It also reports what it could not express, as mapped / partial / unmapped. Under
schema v2 the only deliberately unmapped family is letter-level arithmetic,
which the taxonomy classifies as Bucket C (a gimmick no user wants). See
scripts/measure_schema_coverage.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .schema import (
    GIVEN,
    Keyword,
    LengthConstraint,
    Markup,
    Positional,
    Spec,
    Structure,
    Wrapper,
)

# Deliberately not modelled: character arithmetic, Bucket C in the taxonomy.
UNMAPPABLE: dict[str, str] = {
    "keywords:letter_frequency": "out of scope: letter arithmetic (Bucket C)",
}

# IFEval's constrained_response uses a fixed option set.
CONSTRAINED_RESPONSE_OPTIONS = [
    "My answer is yes.",
    "My answer is no.",
    "My answer is maybe.",
]


@dataclass
class AdapterResult:
    spec: Spec
    mapped: list[str] = field(default_factory=list)
    partial: list[tuple[str, str]] = field(default_factory=list)
    unmapped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.mapped) + len(self.partial) + len(self.unmapped)


def _mark(spec: Spec, slot: str) -> None:
    spec.provenance[slot] = GIVEN


def spec_from_ifeval(
    instruction_id_list: list[str],
    kwargs_list: Optional[list[Optional[dict[str, Any]]]] = None,
) -> AdapterResult:
    """Build a Spec from an IFEval row's instruction ids + kwargs."""
    spec = Spec()
    res = AdapterResult(spec=spec)
    kwargs_list = kwargs_list or [{} for _ in instruction_id_list]

    must: list[Keyword] = []
    forbid: list[str] = []
    quotes = title = False
    end_phrase = None
    markup: dict[str, LengthConstraint] = {}

    def set_structure(iid: str, s: Structure) -> None:
        """One structure slot; a second claim on it is a real expressiveness limit."""
        if spec.structure is not None:
            res.partial.append((iid, f"structure slot already held by {spec.structure.kind}"))
            return
        spec.structure = s
        _mark(spec, "structure")
        res.mapped.append(iid)

    for iid, raw in zip(instruction_id_list, kwargs_list):
        kw = {k: v for k, v in (raw or {}).items() if v is not None}

        if iid in UNMAPPABLE:
            res.unmapped.append((iid, UNMAPPABLE[iid]))
            continue

        if iid == "length_constraints:number_words":
            spec.length_words = _relational(kw.get("relation"), int(kw["num_words"]), "words")
            _mark(spec, "length_words")
            res.mapped.append(iid)

        elif iid == "length_constraints:number_sentences":
            spec.length_sentences = _relational(
                kw.get("relation"), int(kw["num_sentences"]), "sentences")
            _mark(spec, "length_sentences")
            res.mapped.append(iid)

        elif iid == "length_constraints:number_paragraphs":
            spec.length_paragraphs = LengthConstraint.eq(int(kw["num_paragraphs"]), "paragraphs")
            _mark(spec, "length_paragraphs")
            res.mapped.append(iid)

        elif iid == "length_constraints:nth_paragraph_first_word":
            spec.length_paragraphs = LengthConstraint.eq(int(kw["num_paragraphs"]), "paragraphs")
            _mark(spec, "length_paragraphs")
            spec.positional = Positional(int(kw["nth_paragraph"]), str(kw["first_word"]))
            _mark(spec, "positional")
            res.mapped.append(iid)

        elif iid == "change_case:english_lowercase":
            spec.case = "lower"
            _mark(spec, "case")
            res.mapped.append(iid)

        elif iid == "change_case:english_capital":
            spec.case = "upper"
            _mark(spec, "case")
            res.mapped.append(iid)

        elif iid == "change_case:capital_word_frequency":
            markup["caps_words"] = _relational(
                kw.get("capital_relation"), int(kw["capital_frequency"]), "caps_words")
            res.mapped.append(iid)

        elif iid == "detectable_format:number_bullet_lists":
            set_structure(iid, Structure("bullets", int(kw["num_bullets"])))

        elif iid == "detectable_format:json_format":
            set_structure(iid, Structure("json"))

        elif iid == "detectable_format:multiple_sections":
            splitter = str(kw["section_spliter"])
            set_structure(iid, Structure("sections", int(kw["num_sections"]), splitter))
            spec.delimiters = (spec.delimiters or []) + [splitter]
            _mark(spec, "delimiters")

        elif iid == "detectable_format:title":
            title = True
            res.mapped.append(iid)

        elif iid == "detectable_format:number_highlighted_sections":
            markup["highlights"] = LengthConstraint.at_least(
                int(kw["num_highlights"]), "highlights")
            res.mapped.append(iid)

        elif iid == "detectable_format:constrained_response":
            spec.response_options = list(CONSTRAINED_RESPONSE_OPTIONS)
            _mark(spec, "response_options")
            res.mapped.append(iid)

        elif iid == "detectable_content:number_placeholders":
            markup["placeholders"] = LengthConstraint.at_least(
                int(kw["num_placeholders"]), "placeholders")
            res.mapped.append(iid)

        elif iid == "detectable_content:postscript":
            must.append(Keyword(str(kw["postscript_marker"])))
            res.mapped.append(iid)

        elif iid == "combination:two_responses":
            set_structure(iid, Structure("responses", 2, "******"))

        elif iid == "combination:repeat_prompt":
            spec.response_boundary = str(kw["prompt_to_repeat"])
            _mark(spec, "response_boundary")
            res.mapped.append(iid)

        elif iid == "keywords:existence":
            must.extend(Keyword(str(k)) for k in kw.get("keywords", []))
            res.mapped.append(iid)

        elif iid == "keywords:forbidden_words":
            forbid.extend(str(w) for w in kw.get("forbidden_words", []))
            res.mapped.append(iid)

        elif iid == "keywords:frequency":
            relation = (kw.get("relation") or "").strip().lower()
            freq, word = int(kw["frequency"]), str(kw["keyword"])
            if relation == "at least":
                must.append(Keyword(word, freq))
            elif relation == "less than":
                # strict: count < freq, so the inclusive ceiling is freq - 1
                must.append(Keyword(word, 0, freq - 1))
            else:
                raise ValueError(f"unknown IFEval relation {kw.get('relation')!r}")
            res.mapped.append(iid)

        elif iid == "punctuation:no_comma":
            forbid.append(",")
            res.mapped.append(iid)

        elif iid == "language:response_language":
            spec.language = str(kw["language"]).lower()
            _mark(spec, "language")
            res.mapped.append(iid)

        elif iid == "startend:end_checker":
            end_phrase = str(kw["end_phrase"])
            res.mapped.append(iid)

        elif iid == "startend:quotation":
            quotes = True
            res.mapped.append(iid)

        else:
            res.unmapped.append((iid, "unrecognised instruction id"))

    if must:
        spec.must_include = must
        _mark(spec, "must_include")
    if forbid:
        spec.forbidden = forbid
        _mark(spec, "forbidden")
    if quotes or title or end_phrase:
        spec.wrappers = Wrapper(quotes=quotes, end=end_phrase, title=title)
        _mark(spec, "wrappers")
    if markup:
        spec.markup = Markup(**markup)
        _mark(spec, "markup")

    return res


def _relational(relation: Optional[str], value: int, unit: str) -> LengthConstraint:
    """Translate IFEval's relation vocabulary exactly.

    IFEval's 'less than' is strict (count < value), so the inclusive form is
    value - 1. Getting this off by one is precisely how a verifier drifts out of
    parity with the benchmark.
    """
    rel = (relation or "at least").strip().lower()
    if rel == "at least":
        return LengthConstraint.at_least(value, unit)
    if rel == "less than":
        return LengthConstraint.at_most(value - 1, unit)
    raise ValueError(f"unknown IFEval relation {relation!r}")
