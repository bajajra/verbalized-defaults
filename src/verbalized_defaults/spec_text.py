"""Parse and serialise the ``<spec>`` block that the model emits.

The proposal shows an illustrative, prose-y spec block. This module defines the
**canonical machine-readable form**: one slot per line, ``slot: value
[provenance]``, with a strict grammar per slot so the spec is unambiguous to
verify and to score.

    <spec>
    length_words: 300 [assumed]
    length_sentences: >=5 [given]
    case: lower [given]
    structure: sections=3, splitter="SECTION" [given]
    delimiters: "******" [given]
    must_include: "banana"x2, "apple" [given]
    forbidden: "utilize" [given]
    wrappers: quotes, title, end="THE END" [given]
    markup: highlights>=3, placeholders>=2 [given]
    positional: paragraph=2, first_word="however" [given]
    response_options: "My answer is yes." [given]
    language: en [assumed]
    register: playful [assumed]
    response_boundary: "Answer:" [given]
    </spec>

Parsing is **lenient by construction**: it returns a ``ParseResult`` carrying both
the recovered ``Spec`` and a list of errors, rather than raising. A malformed or
hallucinated slot is a *binding* failure that ``R_bind`` must be able to measure
and penalise -- crashing on it would throw away the signal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import (
    ASSUMED,
    GIVEN,
    Keyword,
    LengthConstraint,
    Markup,
    Positional,
    Spec,
    Structure,
    Wrapper,
)

_SPEC_BLOCK_RE = re.compile(r"<spec>(.*?)</spec>", re.DOTALL | re.IGNORECASE)
_LINE_RE = re.compile(
    r"^\s*(?P<slot>[A-Za-z_]+)\s*:\s*(?P<value>.*?)\s*"
    r"(?:\[\s*(?P<prov>given|assumed)\b[^\]]*\])?\s*$",
    re.IGNORECASE,
)
# "text"  |  "text"x3  |  "text"x0..2
_QUOTED_RE = re.compile(r'"([^"]*)"(?:\s*[xX]\s*(\d+)(?:\s*\.\.\s*(\d+))?)?')
_MARKUP_DIM_RE = re.compile(r"(highlights|placeholders|caps_words)\s*(>=|<=|=)\s*(\d+)")
_NONE_TOKENS = {"", "-", "--", "—", "none", "null", "n/a", "na"}

_LENGTH_SLOTS = {"length_words": "words", "length_sentences": "sentences",
                 "length_paragraphs": "paragraphs"}
_UNIT_TO_SLOT = {"words": "length_words", "word": "length_words",
                 "sentences": "length_sentences", "sentence": "length_sentences",
                 "paragraphs": "length_paragraphs", "paragraph": "length_paragraphs"}

CANONICAL_SLOTS = (
    "length_words", "length_sentences", "length_paragraphs", "case", "structure",
    "delimiters", "must_include", "forbidden", "wrappers", "language", "register",
    "response_boundary", "markup", "positional", "response_options",
)


@dataclass
class ParseResult:
    spec: Spec
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def extract_spec_block(text: str) -> str | None:
    """Return the inner text of the first <spec>...</spec> block, if any."""
    m = _SPEC_BLOCK_RE.search(text)
    return m.group(1) if m else None


def _is_none(raw: str) -> bool:
    return raw.strip().lower() in _NONE_TOKENS


def _parse_length(raw: str, unit: str) -> LengthConstraint:
    v = raw.strip().lstrip("~").strip()
    for word in ("words", "word", "sentences", "sentence", "paragraphs", "paragraph"):
        if v.lower().endswith(word):
            v = v[: -len(word)].strip()
            break
    if m := re.fullmatch(r">=\s*(\d+)", v):
        return LengthConstraint.at_least(int(m.group(1)), unit)
    if m := re.fullmatch(r"<=\s*(\d+)", v):
        return LengthConstraint.at_most(int(m.group(1)), unit)
    if m := re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", v):
        return LengthConstraint.between(int(m.group(1)), int(m.group(2)), unit)
    if m := re.fullmatch(r"(\d+)", v):
        return LengthConstraint.eq(int(m.group(1)), unit)
    raise ValueError(f"cannot parse length {raw!r}")


def _parse_structure(raw: str) -> Structure:
    v = raw.strip()
    splitter = None
    if m := re.search(r'\bsplitter\s*=\s*"([^"]*)"', v, re.IGNORECASE):
        splitter = m.group(1)
        v = (v[: m.start()] + v[m.end():]).strip().strip(",").strip()
    v = v.lower()
    if v in {"prose", "json", "table"}:
        return Structure(v)
    if m := re.fullmatch(r"(bullets|sections|responses)\s*=\s*(\d+)", v):
        return Structure(m.group(1), int(m.group(2)), splitter)
    if m := re.fullmatch(r"(\d+)\s+(bullets?|sections?|responses?)", v):
        kind = {"bullet": "bullets", "section": "sections", "response": "responses"}[
            m.group(2).rstrip("s")]
        return Structure(kind, int(m.group(1)), splitter)
    raise ValueError(f"cannot parse structure {raw!r}")


def _parse_quoted_list(raw: str) -> list[tuple[str, int, int | None]]:
    hits = _QUOTED_RE.findall(raw)
    if not hits:
        raise ValueError(f"expected quoted strings, got {raw!r}")
    return [(text, int(lo) if lo else 1, int(hi) if hi else None) for text, lo, hi in hits]


def _parse_wrappers(raw: str) -> Wrapper:
    quotes = bool(re.search(r"\bquotes?\b", raw, re.IGNORECASE))
    title = bool(re.search(r"\btitle\b", raw, re.IGNORECASE))
    start = m.group(1) if (m := re.search(r'\bstart\s*=\s*"([^"]*)"', raw, re.IGNORECASE)) else None
    end = m.group(1) if (m := re.search(r'\bend\s*=\s*"([^"]*)"', raw, re.IGNORECASE)) else None
    if not (quotes or title or start or end):
        raise ValueError(f"cannot parse wrappers {raw!r}")
    return Wrapper(quotes=quotes, start=start, end=end, title=title)


def _parse_markup(raw: str) -> Markup:
    dims: dict[str, LengthConstraint] = {}
    for name, op, num in _MARKUP_DIM_RE.findall(raw):
        n = int(num)
        dims[name] = {"=": LengthConstraint.eq, ">=": LengthConstraint.at_least,
                      "<=": LengthConstraint.at_most}[op](n, name)
    if not dims:
        raise ValueError(f"cannot parse markup {raw!r}")
    return Markup(**dims)


def _parse_positional(raw: str) -> Positional:
    para = re.search(r"\bparagraph\s*=\s*(\d+)", raw, re.IGNORECASE)
    word = re.search(r'\bfirst_word\s*=\s*"([^"]*)"', raw, re.IGNORECASE)
    if not (para and word):
        raise ValueError(f"cannot parse positional {raw!r}; need paragraph=N, first_word=\"W\"")
    return Positional(paragraph=int(para.group(1)), first_word=word.group(1))


def parse_spec(text: str) -> ParseResult:
    """Parse a <spec> block (or a bare set of slot lines) into a Spec.

    Errors are collected, never raised: an unparseable or unknown slot is signal
    for R_bind, not a crash.
    """
    spec = Spec()
    errors: list[str] = []

    body = extract_spec_block(text)
    if body is None:
        body = text
        if "<spec>" in text.lower():
            errors.append("unterminated <spec> block")

    seen: set[str] = set()
    for lineno, line in enumerate(body.splitlines(), start=1):
        if not line.strip():
            continue
        m = _LINE_RE.match(line)
        if not m:
            errors.append(f"line {lineno}: unparseable {line.strip()!r}")
            continue

        slot = m.group("slot").lower()
        raw = m.group("value").strip()
        prov = (m.group("prov") or "").lower() or None

        # aliases from the proposal's illustrative format
        if slot == "audience":
            slot = "register"
        elif slot == "length":
            unit_match = re.search(r"(words?|sentences?|paragraphs?)", raw, re.IGNORECASE)
            if not unit_match:
                errors.append(f"line {lineno}: 'length' needs a unit (words/sentences/paragraphs)")
                continue
            slot = _UNIT_TO_SLOT[unit_match.group(1).lower()]

        if slot not in CANONICAL_SLOTS:
            errors.append(f"line {lineno}: unknown slot {slot!r}")
            continue
        if slot in seen:
            errors.append(f"line {lineno}: duplicate slot {slot!r}")
            continue
        seen.add(slot)

        if _is_none(raw):
            continue  # explicitly declared as unconstrained

        try:
            if slot in _LENGTH_SLOTS:
                setattr(spec, slot, _parse_length(raw, _LENGTH_SLOTS[slot]))
            elif slot == "case":
                spec.case = raw.strip().lower()
            elif slot == "structure":
                spec.structure = _parse_structure(raw)
            elif slot == "delimiters":
                spec.delimiters = [t for t, _, _ in _parse_quoted_list(raw)]
            elif slot == "must_include":
                spec.must_include = [Keyword(t, lo, hi) for t, lo, hi in _parse_quoted_list(raw)]
            elif slot == "forbidden":
                spec.forbidden = [t for t, _, _ in _parse_quoted_list(raw)]
            elif slot == "wrappers":
                spec.wrappers = _parse_wrappers(raw)
            elif slot == "markup":
                spec.markup = _parse_markup(raw)
            elif slot == "positional":
                spec.positional = _parse_positional(raw)
            elif slot == "response_options":
                spec.response_options = [t for t, _, _ in _parse_quoted_list(raw)]
            elif slot == "language":
                spec.language = raw.strip().lower()
            elif slot == "register":
                spec.register = raw.strip()
            elif slot == "response_boundary":
                quoted = _QUOTED_RE.findall(raw)
                spec.response_boundary = quoted[0][0] if quoted else raw.strip()
        except ValueError as exc:
            errors.append(f"line {lineno}: {exc}")
            continue

        if prov:
            spec.provenance[slot] = GIVEN if prov == "given" else ASSUMED
        else:
            errors.append(f"line {lineno}: slot {slot!r} is missing a [given]/[assumed] tag")

    return ParseResult(spec=spec, errors=errors)


def _format_length(c: LengthConstraint) -> str:
    if c.op == "eq":
        return str(c.value)
    if c.op == "min":
        return f">={c.value}"
    if c.op == "max":
        return f"<={c.value}"
    return f"{c.lo}-{c.hi}"


def _format_keyword(k: Keyword) -> str:
    out = f'"{k.text}"'
    if k.max_count is not None:
        return out + f"x{k.min_count}..{k.max_count}"
    if k.min_count > 1:
        return out + f"x{k.min_count}"
    return out


def format_spec(spec: Spec, wrap: bool = True) -> str:
    """Serialise a Spec back into the canonical <spec> block."""
    lines: list[str] = []

    def emit(slot: str, value: str) -> None:
        tag = spec.provenance.get(slot)
        lines.append(f"{slot}: {value}" + (f" [{tag}]" if tag else ""))

    for slot in _LENGTH_SLOTS:
        if (c := getattr(spec, slot)) is not None:
            emit(slot, _format_length(c))
    if spec.case is not None:
        emit("case", spec.case)
    if spec.structure is not None:
        s = spec.structure
        val = f"{s.kind}={s.count}" if s.count is not None else s.kind
        if s.splitter:
            val += f', splitter="{s.splitter}"'
        emit("structure", val)
    if spec.delimiters:
        emit("delimiters", ", ".join(f'"{d}"' for d in spec.delimiters))
    if spec.must_include:
        emit("must_include", ", ".join(_format_keyword(k) for k in spec.must_include))
    if spec.forbidden:
        emit("forbidden", ", ".join(f'"{w}"' for w in spec.forbidden))
    if spec.wrappers is not None:
        w = spec.wrappers
        parts = []
        if w.quotes:
            parts.append("quotes")
        if w.title:
            parts.append("title")
        if w.start:
            parts.append(f'start="{w.start}"')
        if w.end:
            parts.append(f'end="{w.end}"')
        emit("wrappers", ", ".join(parts))
    if spec.markup is not None:
        ops = {"eq": "=", "min": ">=", "max": "<="}
        emit("markup", ", ".join(
            f"{name}{ops[c.op]}{c.value}" for name, c in spec.markup.dimensions()))
    if spec.positional is not None:
        p = spec.positional
        emit("positional", f'paragraph={p.paragraph}, first_word="{p.first_word}"')
    if spec.response_options:
        emit("response_options", ", ".join(f'"{o}"' for o in spec.response_options))
    if spec.language is not None:
        emit("language", spec.language)
    if spec.register is not None:
        emit("register", spec.register)
    if spec.response_boundary is not None:
        emit("response_boundary", f'"{spec.response_boundary}"')

    body = "\n".join(lines)
    return f"<spec>\n{body}\n</spec>" if wrap else body
