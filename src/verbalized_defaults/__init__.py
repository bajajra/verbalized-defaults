"""Verbalized Defaults -- typed convention-spec verifier suite."""
from __future__ import annotations

from .schema import (
    ASSUMED,
    GIVEN,
    ContentPolicy,
    Keyword,
    LengthConstraint,
    Markup,
    Positional,
    Spec,
    SpecValidationError,
    Structure,
    Wrapper,
    validate_spec,
)
from .spec_text import ParseResult, extract_spec_block, format_spec, parse_spec
from .verifiers import verify_spec
from .verifiers.base import SlotResult, SpecReport

__all__ = [
    "Spec",
    "LengthConstraint",
    "Structure",
    "Keyword",
    "Wrapper",
    "Markup",
    "Positional",
    "ContentPolicy",
    "validate_spec",
    "SpecValidationError",
    "verify_spec",
    "SlotResult",
    "SpecReport",
    "parse_spec",
    "format_spec",
    "extract_spec_block",
    "ParseResult",
    "GIVEN",
    "ASSUMED",
]


def main() -> None:
    print("verbalized-defaults verifier suite -- import verify_spec / Spec from this package.")
