"""Result types shared by every slot verifier.

A ``SlotResult`` is deliberately rich (expected / observed / detail), not just a
bool: R_exec is a *dense* factorized reward and the interleaved-verify
application needs a per-slot patch signal, so each check reports why it failed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlotResult:
    slot: str
    ok: bool
    expected: Any = None
    observed: Any = None
    detail: str = ""
    skipped: bool = False  # soft slots (register): reported but excluded from scoring

    def as_dict(self) -> dict:
        return {
            "slot": self.slot,
            "ok": self.ok,
            "expected": self.expected,
            "observed": self.observed,
            "detail": self.detail,
            "skipped": self.skipped,
        }


@dataclass
class SpecReport:
    results: list[SlotResult] = field(default_factory=list)

    @property
    def hard_results(self) -> list[SlotResult]:
        """Slots that count toward the reward / hard gate (soft slots excluded)."""
        return [r for r in self.results if not r.skipped]

    @property
    def ok(self) -> bool:
        """Hard gate: every non-skipped slot passes. Gold data must satisfy this."""
        return all(r.ok for r in self.hard_results)

    @property
    def score(self) -> float:
        """Dense R_exec signal in [0, 1]: fraction of hard slots satisfied."""
        hard = self.hard_results
        if not hard:
            return 1.0
        return sum(r.ok for r in hard) / len(hard)

    def failures(self) -> list[SlotResult]:
        return [r for r in self.hard_results if not r.ok]

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "score": self.score,
            "results": [r.as_dict() for r in self.results],
        }
