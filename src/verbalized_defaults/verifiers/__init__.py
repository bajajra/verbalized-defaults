"""Verifier registry and the top-level ``verify_spec`` entry point.

``verify_spec`` runs every *set* slot of a Spec against a response and returns a
``SpecReport``. That report is the substrate for:

* the hard gate on gold data      -> ``report.ok``
* the dense R_exec reward          -> ``report.score``
* interleaved verify / patching    -> ``report.failures()``
"""
from __future__ import annotations

from ..schema import Spec
from .base import SlotResult, SpecReport
from .case import check_case
from .keywords import check_forbidden, check_must_include
from .language import check_language
from .length import check_length
from .markup import check_markup
from .persona import check_content_policy, check_person
from .positional import check_positional
from .response_options import check_response_options
from .structure import check_delimiters, check_structure
from .wrappers import check_response_boundary, check_wrappers

__all__ = ["verify_spec", "SlotResult", "SpecReport"]


def verify_spec(text: str, spec: Spec) -> SpecReport:
    results: list[SlotResult] = []

    if spec.length_words is not None:
        results.append(check_length("length_words", text, spec.length_words))
    if spec.length_sentences is not None:
        results.append(check_length("length_sentences", text, spec.length_sentences))
    if spec.length_paragraphs is not None:
        results.append(check_length("length_paragraphs", text, spec.length_paragraphs))
    if spec.case is not None:
        results.append(check_case(text, spec.case))
    if spec.structure is not None:
        results.append(check_structure(text, spec.structure))
    if spec.delimiters:
        results.append(check_delimiters(text, spec.delimiters))
    if spec.must_include:
        results.append(check_must_include(text, spec.must_include))
    if spec.forbidden:
        results.append(check_forbidden(text, spec.forbidden))
    if spec.wrappers is not None:
        results.append(check_wrappers(text, spec.wrappers))
    if spec.language is not None:
        results.append(check_language(text, spec.language))
    if spec.response_boundary is not None:
        results.append(check_response_boundary(text, spec.response_boundary))
    if spec.markup is not None:
        results.append(check_markup(text, spec.markup))
    if spec.positional is not None:
        results.append(check_positional(text, spec.positional))
    if spec.response_options:
        results.append(check_response_options(text, spec.response_options))
    if spec.person is not None:
        results.append(check_person(text, spec.person))
    if spec.content_policy is not None and spec.content_policy.active():
        results.append(check_content_policy(text, spec.content_policy))
    # Judge-scored halves of the decomposed register. Reported so they are never
    # silently dropped, skipped so they never enter R_exec.
    for slot in ("tone", "jargon_level", "audience", "register"):
        val = getattr(spec, slot)
        if val is not None:
            results.append(SlotResult(
                slot, True, val, val,
                detail="soft slot: judge-scored, excluded from R_exec", skipped=True))
    if spec.content_rules:
        results.append(SlotResult(
            "content_rules", True, spec.content_rules, spec.content_rules,
            detail="semantic content rules: judge-scored, excluded from R_exec",
            skipped=True))
    if spec.other:
        results.append(
            SlotResult(
                "other", True, spec.other, spec.other,
                detail=("carried for binding only: no latent default and no literal "
                        "verifier, so excluded from R_exec"),
                skipped=True,
            )
        )

    return SpecReport(results=results)
