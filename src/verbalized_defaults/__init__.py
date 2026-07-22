"""Verbalized Defaults -- typed convention-spec verifier suite."""
from __future__ import annotations

from .schema import (
    ASSUMED,
    GIVEN,
    Keyword,
    LengthConstraint,
    Spec,
    SpecValidationError,
    Structure,
    Wrapper,
    validate_spec,
)
from .verifiers import verify_spec
from .verifiers.base import SlotResult, SpecReport

__all__ = [
    "Spec",
    "LengthConstraint",
    "Structure",
    "Keyword",
    "Wrapper",
    "validate_spec",
    "SpecValidationError",
    "verify_spec",
    "SlotResult",
    "SpecReport",
    "GIVEN",
    "ASSUMED",
]


def main() -> None:
    print("verbalized-defaults verifier suite -- import verify_spec / Spec from this package.")
