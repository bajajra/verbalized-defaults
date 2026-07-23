"""The frozen convention spec — schema v2 (15 slots).

A ``Spec`` is the typed, machine-checkable form of the model's ``<spec>`` block:
the resolved value of every convention-governed output dimension, each tagged
with provenance — ``given`` (extracted from the prompt) or ``assumed`` (the
model's own default, now stated). Verification consumes the *values*; provenance
is what ``R_bind`` scores separately.

**v2 (2026-07-21)** grew the schema from 12 to 15 slots after measuring that v1
could express only 59.5% of IFEval prompts (activity/0006). Added ``markup``,
``positional`` and ``response_options``; extended ``wrappers`` with a title,
``must_include`` with an upper bound, and ``structure`` with splitter-delimited
``sections``/``responses``. Every non-gimmick IFEval constraint is now
expressible; only letter-level arithmetic (``keywords:letter_frequency``) is
deliberately excluded as Bucket C.

Slot 'register' is a soft slot: judge-scored only, excluded from R_exec.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

CASE_VALUES = {"standard", "lower", "upper", "title"}
PERSON_VALUES = {"first", "second", "third"}
STRUCTURE_KINDS = {"prose", "bullets", "sections", "json", "table", "responses"}
# Judge-scored only, excluded from R_exec. `person` is deliberately NOT here:
# decomposing `register` moved it from unscoreable prose to a programmatic
# pronoun scan, which is the point of the decomposition.
SOFT_SLOTS = {"register", "tone", "jargon_level", "audience", "content_rules"}

GIVEN = "given"
ASSUMED = "assumed"


@dataclass(frozen=True)
class LengthConstraint:
    """A count target. ``op`` is one of eq | min | max | range."""

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

    def satisfied_by(self, n: int) -> bool:
        if self.op == "eq":
            return n == self.value
        if self.op == "min":
            return n >= self.value
        if self.op == "max":
            return n <= self.value
        if self.op == "range":
            return self.lo <= n <= self.hi
        raise ValueError(f"unknown length op {self.op!r}")

    def describe(self) -> str:
        if self.op == "eq":
            return f"== {self.value}"
        if self.op == "min":
            return f">= {self.value}"
        if self.op == "max":
            return f"<= {self.value}"
        return f"{self.lo}..{self.hi}"


@dataclass(frozen=True)
class Structure:
    kind: str  # one of STRUCTURE_KINDS
    count: Optional[int] = None  # required for bullets / sections / responses
    splitter: Optional[str] = None  # section or response separator, when applicable


@dataclass(frozen=True)
class Keyword:
    text: str
    min_count: int = 1
    max_count: Optional[int] = None  # inclusive upper bound, when constrained


@dataclass(frozen=True)
class Wrapper:
    quotes: bool = False
    start: Optional[str] = None
    end: Optional[str] = None
    title: bool = False  # a <<wrapped title>> is present

    def describe(self) -> str:
        parts = []
        if self.quotes:
            parts.append("double-quoted")
        if self.title:
            parts.append("has <<title>>")
        if self.start:
            parts.append(f"start={self.start!r}")
        if self.end:
            parts.append(f"end={self.end!r}")
        return ", ".join(parts) or "none"


@dataclass(frozen=True)
class Markup:
    """Counts of typographic markup: emphasis, placeholders, shouted words."""

    highlights: Optional[LengthConstraint] = None     # *highlighted* spans
    placeholders: Optional[LengthConstraint] = None   # [placeholder] spans
    caps_words: Optional[LengthConstraint] = None     # ALL-CAPS words

    def dimensions(self) -> list[tuple[str, LengthConstraint]]:
        return [
            (name, c)
            for name, c in (
                ("highlights", self.highlights),
                ("placeholders", self.placeholders),
                ("caps_words", self.caps_words),
            )
            if c is not None
        ]

    def describe(self) -> str:
        return ", ".join(
            f"{name}{c.describe().replace(' ', '')}" for name, c in self.dimensions()
        ) or "none"


@dataclass(frozen=True)
class ContentPolicy:
    """Self-imposed editorial rules the model applies unasked.

    Measured empirically: models volunteer "no external links", "no advertising",
    "no political statements" on prompts that requested none of it. Only the
    surface-checkable half lives here -- semantic rules ("no controversial
    content") go to ``Spec.content_rules``, which is judge-scored. Mixing scored
    and unscored predicates in one slot is exactly the mistake `register` made.
    """

    no_urls: bool = False
    no_emoji: bool = False
    no_profanity: bool = False
    no_first_person: bool = False

    def describe(self) -> str:
        on = [n for n in ("no_urls", "no_emoji", "no_profanity", "no_first_person")
              if getattr(self, n)]
        return ", ".join(on) or "none"

    def active(self) -> list[str]:
        return [n for n in ("no_urls", "no_emoji", "no_profanity", "no_first_person")
                if getattr(self, n)]


@dataclass(frozen=True)
class Positional:
    """A positional constraint: paragraph N (1-indexed) must start with a word."""

    paragraph: int
    first_word: str

    def describe(self) -> str:
        return f"paragraph {self.paragraph} starts with {self.first_word!r}"


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
    # --- the decomposed `register` (schema v3) -------------------------------
    # One free-text soft slot could not carry this: the qualitative half of what
    # models declare is at least eight distinct dimensions, and "register:
    # playful" cannot express "third person, no jargon, no political content".
    person: Optional[str] = None        # first | second | third  -- PROGRAMMATIC
    tone: Optional[str] = None          # soft
    jargon_level: Optional[str] = None  # soft: simple | technical
    audience: Optional[str] = None      # soft
    register: Optional[str] = None      # soft: catch-all remainder, kept for
                                        # stylistic statements not yet decomposed
    response_boundary: Optional[str] = None  # prefix the answer must start with
    markup: Optional[Markup] = None
    positional: Optional[Positional] = None
    response_options: Optional[list[str]] = None
    # Stated constraints on dimensions that carry NO latent default (palindromes,
    # letter arithmetic, bespoke predicates). These exist only because the prompt
    # said so, therefore they can only ever be [given] -- never [assumed] -- and
    # they are excluded from R_exec because the suite has no verifier for them.
    other: Optional[list[str]] = None
    content_policy: Optional[ContentPolicy] = None   # programmatic half
    content_rules: Optional[list[str]] = None        # semantic half, judge-scored
    provenance: dict = field(default_factory=dict)  # slot name -> given | assumed


class SpecValidationError(ValueError):
    pass


def validate_spec(spec: Spec) -> None:
    """Enforce the anti-gaming schema rules.

    - case / structure kinds must come from the frozen enums.
    - bullets / sections / responses must name an exact count.
    - an *assumed* length slot must be a point value or a range no wider than
      ±10%, so the model cannot declare a vacuous window like 10-10000 words and
      satisfy it trivially. ``given`` slots may hold whatever the prompt asked for.
    """
    if spec.case is not None and spec.case not in CASE_VALUES:
        raise SpecValidationError(f"case {spec.case!r} not in {sorted(CASE_VALUES)}")

    if spec.person is not None and spec.person not in PERSON_VALUES:
        raise SpecValidationError(
            f"person {spec.person!r} not in {sorted(PERSON_VALUES)}")

    if spec.structure is not None:
        if spec.structure.kind not in STRUCTURE_KINDS:
            raise SpecValidationError(
                f"structure kind {spec.structure.kind!r} not in {sorted(STRUCTURE_KINDS)}"
            )
        if (spec.structure.kind in {"bullets", "sections", "responses"}
                and spec.structure.count is None):
            raise SpecValidationError(f"structure '{spec.structure.kind}' requires an exact count")

    if spec.positional is not None and spec.positional.paragraph < 1:
        raise SpecValidationError("positional.paragraph is 1-indexed and must be >= 1")

    # A slot exists in the typed schema iff its dimension carries a latent
    # default. 'other' holds constraints with no default, so nothing in it can
    # be assumed -- there is no prior to assume. This is the load-bearing
    # invariant separating the two kinds of slot.
    if spec.provenance.get("other") == ASSUMED:
        raise SpecValidationError(
            "'other' holds constraints on dimensions with no latent default, so it "
            "can only be [given]; an [assumed] entry there is a category error"
        )

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
