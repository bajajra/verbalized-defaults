"""Language verifier (langdetect, seeded for determinism)."""
from __future__ import annotations

from langdetect import DetectorFactory, LangDetectException, detect

from .base import SlotResult

# langdetect is nondeterministic unless the factory seed is fixed.
DetectorFactory.seed = 0


def check_language(text: str, iso_code: str) -> SlotResult:
    try:
        got = detect(text)
    except LangDetectException:
        got = "unknown"
    ok = got == iso_code
    return SlotResult("language", ok, iso_code, got)
