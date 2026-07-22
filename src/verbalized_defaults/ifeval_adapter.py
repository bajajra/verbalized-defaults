"""Map IFEval / IFBench instruction metadata into our typed ``Spec``.

This adapter does double duty:

1. **E0.1 oracle prefill** -- it builds the ground-truth spec to prefill into the
   model's thinking, from benchmark metadata rather than from a model.
2. **R_bind ground truth** -- it is the reference the model's own declared
   ``[given]`` slots are scored against.

Every slot it produces is tagged ``[given]``: by construction these constraints
came from the prompt.

It also reports what it *could not* express. That is not a defect to hide -- the
mapped / partial / unmapped split is a direct measurement of how much of a
benchmark our frozen 12-slot schema can represent, and it tells us which gaps
would justify a new slot. See scripts/measure_schema_coverage.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .schema import GIVEN, Keyword, LengthConstraint, Spec, Structure, Wrapper

# Instruction ids that our 12-slot schema deliberately cannot express.
# Two different reasons, kept distinct because they have different implications:
#   'schema gap'  -- a real convention we do not model (candidate for a new slot)
#   'out of scope'-- character/word arithmetic; Bucket C in the taxonomy
UNMAPPABLE: dict[str, str] = {
    "detectable_format:title": "schema gap: <<title>> wrapper not modelled",
    "detectable_format:number_highlighted_sections": "schema gap: *highlight* count not modelled",
    "detectable_format:constrained_response": "schema gap: fixed answer-option set not modelled",
    "detectable_content:number_placeholders": "schema gap: [placeholder] count not modelled",
    "combination:two_responses": "schema gap: multi-slot response decomposition not modelled",
    "change_case:capital_word_frequency": "out of scope: capital-word arithmetic (Bucket C)",
    "keywords:letter_frequency": "out of scope: letter arithmetic (Bucket C)",
}


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
    quotes, end_phrase = False, None

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
            res.partial.append((iid, "paragraph count mapped; nth-paragraph first-word not modelled"))

        elif iid == "change_case:english_lowercase":
            spec.case = "lower"
            _mark(spec, "case")
            res.mapped.append(iid)

        elif iid == "change_case:english_capital":
            spec.case = "upper"
            _mark(spec, "case")
            res.mapped.append(iid)

        elif iid == "detectable_format:number_bullet_lists":
            spec.structure = Structure("bullets", int(kw["num_bullets"]))
            _mark(spec, "structure")
            res.mapped.append(iid)

        elif iid == "detectable_format:json_format":
            spec.structure = Structure("json")
            _mark(spec, "structure")
            res.mapped.append(iid)

        elif iid == "detectable_format:multiple_sections":
            # The exact splitter string is checkable; the section *count* uses
            # IFEval's splitter semantics, which our markdown-header based
            # sections check does not reproduce -- so only the delimiter is claimed.
            spec.delimiters = (spec.delimiters or []) + [str(kw["section_spliter"])]
            _mark(spec, "delimiters")
            res.partial.append((iid, "splitter mapped; section count uses IFEval splitter semantics"))

        elif iid == "detectable_content:postscript":
            must.append(Keyword(str(kw["postscript_marker"])))
            res.mapped.append(iid)

        elif iid == "keywords:existence":
            must.extend(Keyword(str(k)) for k in kw.get("keywords", []))
            res.mapped.append(iid)

        elif iid == "keywords:forbidden_words":
            forbid.extend(str(w) for w in kw.get("forbidden_words", []))
            res.mapped.append(iid)

        elif iid == "keywords:frequency":
            relation = (kw.get("relation") or "").strip().lower()
            if relation == "at least":
                must.append(Keyword(str(kw["keyword"]), int(kw["frequency"])))
                res.mapped.append(iid)
            else:
                res.partial.append((iid, "upper-bound occurrence count not expressible as must_include"))

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

        elif iid == "combination:repeat_prompt":
            spec.response_boundary = str(kw["prompt_to_repeat"])
            _mark(spec, "response_boundary")
            res.mapped.append(iid)

        else:
            res.unmapped.append((iid, "unrecognised instruction id"))

    if must:
        spec.must_include = must
        _mark(spec, "must_include")
    if forbid:
        spec.forbidden = forbid
        _mark(spec, "forbidden")
    if quotes or end_phrase:
        spec.wrappers = Wrapper(quotes=quotes, end=end_phrase)
        _mark(spec, "wrappers")

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
