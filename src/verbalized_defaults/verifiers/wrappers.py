"""Wrapper and response-boundary verifiers.

wrappers: whole-response envelope constraints (double-quoted, start phrase, end
phrase) -- IFEval's startend:* family.

response_boundary: the anti-inline-pollution slot. The answer must begin
immediately with the declared prefix, with no reasoning preamble leaking into
the scored output (the Gemma inline-CoT artifact; less relevant for a model
with a separate reasoning channel, but still the place to encode "no preamble").
"""
from __future__ import annotations

from ..schema import Wrapper
from .base import SlotResult


def check_wrappers(text: str, w: Wrapper) -> SlotResult:
    t = text.strip()
    problems = []
    if w.quotes and not (len(t) >= 2 and t.startswith('"') and t.endswith('"')):
        problems.append("not wrapped in double quotes")
    if w.start is not None and not t.startswith(w.start):
        problems.append(f"missing start phrase {w.start!r}")
    if w.end is not None and not t.endswith(w.end):
        problems.append(f"missing end phrase {w.end!r}")
    ok = not problems
    return SlotResult("wrappers", ok, w.describe(), "ok" if ok else "; ".join(problems))


def check_response_boundary(text: str, prefix: str) -> SlotResult:
    lead = text.lstrip()
    ok = lead.startswith(prefix)
    return SlotResult(
        "response_boundary", ok, f"starts with {prefix!r}",
        "ok" if ok else f"starts with {lead[:24]!r}",
    )
