"""The frozen 12-slot convention spec (experiments doc, section 2).

A ``Spec`` is the typed, machine-checkable form of the model's ``<spec>`` block:
the resolved value of every convention-governed output dimension, each tagged
with provenance -- ``given`` (extracted from the prompt) or ``assumed`` (the
model's own default, now stated). Verification (``verifiers.verify_spec``)
consumes the *values*; provenance is what ``R_bind`` will score separately.

Slot 'register' is a soft slot: judge-scored only, excluded from R_exec.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

CASE_VALUES = {"standard", "lower", "upper", "title"}
STRUCTURE_KINDS = {"prose", "bullets", "sections", "json", "table"}
SOFT_SLOTS = {"register"}

GIVEN = "given"
ASSUMED = "assumed"


@dataclass(frozen=True)
class LengthConstraint:
    """A length target. ``op`` is one of eq | min | max | range."""

    op: str
    value: Optional[int] = None
    lo: Optional[int] = None
    hi: Optional[int] = None
    unit: str = ""  # informational: words / sentences / paragraphs

    @staticmethod
    def eq(v: int, unit: str = "") -> "LengthConstraint":
        return LengthConstraint("eq", value=v, unit=unit)

    @staticmethod
    def at_least(v: int, unit: str = "") -> "LengthConstraint":
        return LengthConstraint("min", value=v, unit=unit)

    @staticmethod
    def at_most(v: int, unit: str = "") -> "LengthConstraint":
        return LengthConstraint("max", value=v, unit=unit)

    @staticmethod
    def between(lo: int, hi: int, unit: str = "") -> "LengthConstraint":
        return LengthConstraint("range", lo=lo, hi=hi, unit=unit)


@dataclass(frozen=True)
class Structure:
    kind: str  # one of STRUCTURE_KINDS
    count: Optional[int] = None  # required for 'bullets' and 'sections'


@dataclass(frozen=True)
class Keyword:
    text: str
    min_count: int = 1


@dataclass(frozen=True)
class Wrapper:
    quotes: bool = False
    start: Optional[str] = None
    end: Optional[str] = None

    def describe(self) -> str:
        parts = []
        if self.quotes:
            parts.append("double-quoted")
        if self.start:
            parts.append(f"start={self.start!r}")
        if self.end:
            parts.append(f"end={self.end!r}")
        return ", ".join(parts) or "none"


@dataclass
class Spec:
    length_words: Optional[LengthConstraint] = None
    length_sentences: Optional[LengthConstraint] = None
    length_paragraphs: Optional[LengthConstraint] = None
    case: Optional[str] = None
    structure: Optional[Structure] = None
    delimiters: Optional[list[str]] = None
    must_include: Optional[list[Keyword]] = None
    forbidden: Optional[list[str]] = None
    wrappers: Optional[Wrapper] = None
    language: Optional[str] = None
    register: Optional[str] = None  # soft slot (judge-only)
    response_boundary: Optional[str] = None  # prefix the answer must start with
    provenance: dict = field(default_factory=dict)  # slot name -> given | assumed


class SpecValidationError(ValueError):
    pass


def validate_spec(spec: Spec) -> None:
    """Enforce the anti-gaming schema rules (experiments section 2).

    - case / structure kinds must be from the frozen enums.
    - 'bullets' and 'sections' must name an exact count.
    - an *assumed* length slot must be a point value or a range no wider than
      +/-10%, so the model cannot declare a vacuous window like 10-10000 words
      and satisfy it trivially. ``given`` slots may hold whatever the prompt
      literally asked for.
    """
    if spec.case is not None and spec.case not in CASE_VALUES:
        raise SpecValidationError(f"case {spec.case!r} not in {sorted(CASE_VALUES)}")

    if spec.structure is not None:
        if spec.structure.kind not in STRUCTURE_KINDS:
            raise SpecValidationError(
                f"structure kind {spec.structure.kind!r} not in {sorted(STRUCTURE_KINDS)}"
            )
        if spec.structure.kind in {"bullets", "sections"} and spec.structure.count is None:
            raise SpecValidationError(f"structure '{spec.structure.kind}' requires an exact count")

    for slot in ("length_words", "length_sentences", "length_paragraphs"):
        c: Optional[LengthConstraint] = getattr(spec, slot)
        if c is None:
            continue
        if spec.provenance.get(slot) == ASSUMED:
            _validate_assumed_length(slot, c)


def _validate_assumed_length(slot: str, c: LengthConstraint) -> None:
    if c.op == "eq":
        return
    if c.op == "range":
        if c.lo is None or c.hi is None or c.lo <= 0 or c.hi < c.lo:
            raise SpecValidationError(f"{slot}: malformed assumed range {c.lo}-{c.hi}")
        if c.hi > math.ceil(c.lo * 1.10):
            raise SpecValidationError(
                f"{slot}: assumed range {c.lo}-{c.hi} is wider than +/-10%; an assumed "
                "length must be a point value or a <=+/-10% window"
            )
        return
    raise SpecValidationError(
        f"{slot}: an assumed length must be a point value or a <=+/-10% range, got op={c.op!r}"
    )
