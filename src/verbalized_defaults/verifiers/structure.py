"""Structure and delimiter verifiers.

Structure counts are *global* by design -- this is the taxonomy's A3 failure,
where "exactly 3 bullets total" gets applied per-stanza (9 bullets). So
``bullets`` counts every bullet line across the whole response and requires the
exact total.
"""
from __future__ import annotations

import json
import re

from ..schema import Structure
from .base import SlotResult

_BULLET_RE = re.compile(r"^[ \t]*[-*+•‣⁃▪▫◦●○◉⚫◆◇]\s+\S", re.MULTILINE)
_HEADER_RE = re.compile(r"^[ \t]*#{1,6}\s+\S", re.MULTILINE)
_TABLE_RE = re.compile(r"^[ \t]*\|.+\|[ \t]*\n[ \t]*\|[ \t:|-]+\|[ \t]*$", re.MULTILINE)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def count_bullets(text: str) -> int:
    return len(_BULLET_RE.findall(text))


def count_headers(text: str) -> int:
    return len(_HEADER_RE.findall(text))


def count_splitter_sections(text: str, splitter: str) -> int:
    """Count sections the way IFEval's multiple_sections checker does.

    IFEval splits on the pattern ``\\s?<splitter>\\s?\\d+\\s?`` -- i.e. the
    splitter followed by a section number ("SECTION 1", "SECTION 2") -- and takes
    the number of sections as ``len(parts) - 1``, since text before the first
    splitter is not a section.
    """
    pattern = r"\s?" + re.escape(splitter) + r"\s?\d+\s?"
    return len(re.split(pattern, text)) - 1


def _is_json(text: str) -> bool:
    t = _FENCE_RE.sub("", text.strip()).strip()
    try:
        json.loads(t)
        return True
    except (ValueError, TypeError):
        return False


def check_structure(text: str, s: Structure) -> SlotResult:
    if s.kind == "prose":
        b, h = count_bullets(text), count_headers(text)
        ok = b == 0 and h == 0
        return SlotResult("structure", ok, "prose (no bullets/headers)", f"{b} bullets, {h} headers")
    if s.kind == "bullets":
        b = count_bullets(text)
        return SlotResult(
            "structure", b == s.count, f"exactly {s.count} bullets (global)", b,
            detail="counts bullet lines across the whole response, not per section",
        )
    if s.kind == "sections":
        if s.splitter:
            n = count_splitter_sections(text, s.splitter)
            return SlotResult(
                "structure", n == s.count, f"exactly {s.count} '{s.splitter} N' sections", n,
                detail="counted by IFEval splitter semantics: <splitter> followed by a number",
            )
        h = count_headers(text)
        return SlotResult("structure", h == s.count, f"exactly {s.count} sections", h,
                          detail="counted as markdown headers (no splitter declared)")
    if s.kind == "responses":
        sep = s.splitter or "******"
        parts = [p for p in text.split(sep) if p.strip()]
        distinct = len({p.strip() for p in parts}) == len(parts)
        ok = len(parts) == s.count and distinct
        detail = "" if ok else (
            f"{len(parts)} non-empty parts split on {sep!r}"
            + ("" if distinct else "; parts are not distinct"))
        return SlotResult(
            "structure", ok, f"exactly {s.count} distinct responses separated by {sep!r}",
            len(parts), detail=detail,
        )
    if s.kind == "json":
        ok = _is_json(text)
        return SlotResult("structure", ok, "valid JSON", "parses" if ok else "does not parse")
    if s.kind == "table":
        ok = _TABLE_RE.search(text) is not None
        return SlotResult("structure", ok, "markdown table", "present" if ok else "absent")
    raise ValueError(f"unknown structure kind {s.kind!r}")


def check_delimiters(text: str, seps: list[str]) -> SlotResult:
    """Each exact separator string must appear at least once.

    Exact-substring match catches the A3 off-by-one (need '******' (6), got
    '*****' (5)): the 6-char string is not a substring of the 5-char run.
    """
    missing = [s for s in seps if s not in text]
    ok = not missing
    return SlotResult(
        "delimiters", ok, f"contains {seps}",
        "all present" if ok else f"missing {missing}",
    )
