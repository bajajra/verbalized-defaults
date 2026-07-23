"""Extract a typed ``Spec`` from free-form natural-language convention statements.

This is the hybrid's load-bearing piece: **the model writes plain English, we
derive the typed spec for verification.** It keeps `R_exec` mechanical without
forcing the model to parse or emit a DSL — which the E0.1 results showed costs
4-6 points of accuracy on models that have never been trained on the format.

Deliberately rule-based rather than LLM-based, for three reasons: it is
deterministic (an LLM extractor would add its own sampling noise to every
measurement), it is free at RL-reward time, and its failures are inspectable.
Lines it cannot type are returned separately as ``unextracted`` so extraction
coverage is always measurable rather than silently assumed.

Coverage is the metric that decides whether the hybrid is viable at all.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import (ASSUMED, ContentPolicy, Keyword, LengthConstraint, Markup,
                     Spec, Structure, Wrapper)

_LANGS = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es",
    "italian": "it", "portuguese": "pt", "russian": "ru", "japanese": "ja",
    "korean": "ko", "chinese": "zh", "hindi": "hi", "arabic": "ar",
    "dutch": "nl", "polish": "pl", "turkish": "tr", "vietnamese": "vi",
    "thai": "th", "bengali": "bn", "urdu": "ur", "persian": "fa",
    "punjabi": "pa", "telugu": "te", "tamil": "ta", "marathi": "mr",
    "gujarati": "gu", "kannada": "kn", "nepali": "ne", "swahili": "sw",
    "finnish": "fi", "hebrew": "he",
}

_MIN = r"(?:at least|minimum of|no fewer than|no less than|more than|over)"
_MAX = r"(?:no more than|at most|fewer than|less than|under|up to|maximum of)"
# key = singular stem used in the regex; value = (slot, plural unit label).
# The label must be plural to match what the adapter and NL renderer produce,
# otherwise otherwise-identical constraints compare unequal on a cosmetic field.
_UNITS = {"word": ("length_words", "words"),
          "sentence": ("length_sentences", "sentences"),
          "paragraph": ("length_paragraphs", "paragraphs")}


@dataclass
class Extraction:
    spec: Spec = field(default_factory=Spec)
    extracted: list[str] = field(default_factory=list)
    unextracted: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        total = len(self.extracted) + len(self.unextracted)
        return len(self.extracted) / total if total else 0.0


def _lines(text: str) -> list[str]:
    """Split a declaration block into individual convention statements."""
    out = []
    for raw in text.splitlines():
        s = raw.strip().lstrip("-*•").strip()
        s = re.sub(r"^\d+[.)]\s*", "", s)          # numbered lists
        s = re.sub(r"^\*\*(.+?)\*\*:?\s*", r"\1: ", s)  # **Length**: ...
        if len(s) < 3:
            continue
        out.append(s)
    return out


def _length(line: str) -> tuple[str, LengthConstraint] | None:
    for stem, (slot, unit) in _UNITS.items():
        u = stem + "s?"
        if m := re.search(rf"(\d+)\s*(?:-|–|to)\s*(\d+)\s+{u}\b", line, re.I):
            return slot, LengthConstraint.between(int(m.group(1)), int(m.group(2)), unit)
        if m := re.search(rf"{_MIN}\s+(?:about\s+)?(\d+)\s+{u}\b", line, re.I):
            return slot, LengthConstraint.at_least(int(m.group(1)), unit)
        if m := re.search(rf"{_MAX}\s+(?:about\s+)?(\d+)\s+{u}\b", line, re.I):
            return slot, LengthConstraint.at_most(int(m.group(1)), unit)
        if m := re.search(rf"(\d+)\+\s+{u}\b", line, re.I):
            return slot, LengthConstraint.at_least(int(m.group(1)), unit)
        # A hedged figure must not become a point value. "~650 words" verified
        # as exactly 650 would fail almost every time, which would deflate the
        # self-consistency measurement into an artefact of our own parsing.
        # Hedges become a +/-10% window -- the same tolerance the schema's
        # anti-gaming rule allows for an assumed length.
        if m := re.search(rf"\b(?:about|around|approximately|roughly|~|circa|近)\s*"
                          rf"(\d+)\s+{u}\b", line, re.I):
            v = int(m.group(1))
            return slot, LengthConstraint.between(round(v * 0.9), round(v * 1.1), unit)
        if m := re.search(rf"\b(?:exactly\s+)?(\d+)\s+{u}\b", line, re.I):
            return slot, LengthConstraint.eq(int(m.group(1)), unit)
    return None


def extract_spec(text: str) -> Extraction:
    """Parse a natural-language convention declaration into a typed Spec."""
    ex = Extraction()
    spec = ex.spec
    must: list[Keyword] = []
    forbid: list[str] = []
    markup: dict[str, LengthConstraint] = {}
    wrap_quotes = wrap_title = False
    wrap_end = None
    pol: dict[str, bool] = {}
    content_rules: list[str] = []

    for line in _lines(text):
        low = line.lower()
        hit = False

        if (r := _length(line)) is not None:
            slot, c = r
            if getattr(spec, slot) is None:
                setattr(spec, slot, c)
                spec.provenance[slot] = ASSUMED
            hit = True

        if re.search(r"\ball\s+lower ?case\b|\blower ?case only\b|\bin lower ?case\b"
                     r"|\blower ?case\b", low):
            spec.case, spec.provenance["case"] = "lower", ASSUMED
            hit = True
        elif re.search(r"\ball\s+caps\b|\bupper ?case\b|\bcapital letters\b", low):
            spec.case, spec.provenance["case"] = "upper", ASSUMED
            hit = True
        elif re.search(r"\btitle case\b", low):
            spec.case, spec.provenance["case"] = "title", ASSUMED
            hit = True
        elif re.search(r"\b(?:sentence case|standard|normal) capitali[sz]ation\b"
                       r"|\bstandard case\b", low):
            spec.case, spec.provenance["case"] = "standard", ASSUMED
            hit = True

        if m := re.search(r"(\d+)\s+bullet", low):
            spec.structure = Structure("bullets", int(m.group(1)))
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif m := re.search(r"(\d+)\s+(?:sections?|headings?)", low):
            spec.structure = Structure("sections", int(m.group(1)))
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif re.search(r"\bvalid json\b|\bjson format\b|\bas json\b", low):
            spec.structure = Structure("json")
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif re.search(r"\bmarkdown table\b|\bas a table\b", low):
            spec.structure = Structure("table")
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif re.search(r"\bno bullet|\bplain prose\b|\bprose\b.*\bno head|\bno heading"
                       r"|\bno (?:bold|markdown|formatting)\b|\bno lists?\b", low):
            spec.structure = Structure("prose")
            spec.provenance["structure"] = ASSUMED
            hit = True

        if re.search(r"\bno commas?\b|\bwithout (?:any )?commas?\b"
                     r"|\b(?:avoid|do not use|don't use|never use|omit)\s+"
                     r"(?:any\s+)?commas?\b", low):
            forbid.append(",")
            hit = True
        for m in re.finditer(r"(?:avoid|do not use|don't use|never use|exclude)\s+"
                             r"(?:the word\s+)?[\"'‘“]([^\"'’”]+)[\"'’”]", line, re.I):
            forbid.append(m.group(1))
            hit = True
        for m in re.finditer(r"(?:include|use|contain|mention)\s+(?:the (?:word|phrase)\s+)?"
                             r"[\"'‘“]([^\"'’”]+)[\"'’”]", line, re.I):
            must.append(Keyword(m.group(1)))
            hit = True

        if m := re.search(r"(?:at least\s+)?(\d+)\s+(?:\*?highlighted\*?|bold(?:ed)?|"
                          r"emphasi[sz]ed)\s+(?:sections?|parts?|phrases?)?", low):
            markup["highlights"] = LengthConstraint.at_least(int(m.group(1)), "highlights")
            hit = True
        if m := re.search(r"(?:at least\s+)?(\d+)\s+placeholders?", low):
            markup["placeholders"] = LengthConstraint.at_least(int(m.group(1)), "placeholders")
            hit = True

        if re.search(r"\bwrap(?:ped)?\b.*\bquot|\bin double quot|\bquotation marks\b", low):
            wrap_quotes, hit = True, True
        if re.search(r"<<.+>>|\btitle\b.*\bangle bracket", low):
            wrap_title, hit = True, True
        if m := re.search(r"end (?:with|the response with)\s*[\"'‘“]([^\"'’”]+)[\"'’”]",
                          line, re.I):
            wrap_end, hit = m.group(1), True

        # --- decomposed register (schema v3) ---
        if m := re.search(r"\b(first|second|third)[- ]person\b", low):
            spec.person, spec.provenance["person"] = m.group(1), ASSUMED
            hit = True
        if m := re.search(r"\btone\s*(?:is|:|should be)?\s*"
                          r"(formal|informal|objective|neutral|warm|friendly|"
                          r"professional|conversational|playful|serious|encouraging)", low):
            spec.tone, spec.provenance["tone"] = m.group(1), ASSUMED
            hit = True
        if re.search(r"\bno jargon\b|\bplain language\b|\bavoid jargon\b"
                     r"|\bsimple language\b|\baccessible language\b", low):
            spec.jargon_level, spec.provenance["jargon_level"] = "simple", ASSUMED
            hit = True
        elif re.search(r"\btechnical (?:language|terms|vocabulary)\b|\buse jargon\b", low):
            spec.jargon_level, spec.provenance["jargon_level"] = "technical", ASSUMED
            hit = True
        if m := re.search(r"\b(?:audience|written for|aimed at|target reader)\s*(?:is|:)?\s*"
                          r"([a-z ]{3,40})", low):
            spec.audience, spec.provenance["audience"] = m.group(1).strip(), ASSUMED
            hit = True

        # --- content policy: programmatic half ---
        if re.search(r"\bno (?:external )?(?:links?|urls?)\b|\bavoid (?:links?|urls?)\b", low):
            pol["no_urls"] = True
            hit = True
        if re.search(r"\bno emoji|\bavoid emoji|\bwithout emoji", low):
            pol["no_emoji"] = True
            hit = True
        if re.search(r"\bno profan|\bno swear|\bavoid profan|\bno vulgar", low):
            pol["no_profanity"] = True
            hit = True
        if re.search(r"\bno first[- ]person\b|\bavoid first[- ]person\b"
                     r"|\bno personal (?:anecdote|opinion|experience)", low):
            pol["no_first_person"] = True
            hit = True
        # --- content policy: semantic half (judge) ---
        if re.search(r"\bno politic|\bno religio|\bno controversial|\bno advertis"
                     r"|\bno offensive\b|\bno harmful\b|\bno explicit\b"
                     r"|\bno violen|\bno illegal\b|\bno stereotyp", low):
            content_rules.append(line)
            hit = True

        for name, code in _LANGS.items():
            if re.search(rf"\b(?:in|language:?)\s+{name}\b", low):
                spec.language, spec.provenance["language"] = code, ASSUMED
                hit = True
                break

        (ex.extracted if hit else ex.unextracted).append(line)

    if must:
        spec.must_include = must
        spec.provenance["must_include"] = ASSUMED
    if forbid:
        spec.forbidden = list(dict.fromkeys(forbid))
        spec.provenance["forbidden"] = ASSUMED
    if markup:
        spec.markup = Markup(**markup)
        spec.provenance["markup"] = ASSUMED
    if pol:
        spec.content_policy = ContentPolicy(**pol)
        spec.provenance["content_policy"] = ASSUMED
    if content_rules:
        spec.content_rules = content_rules
        spec.provenance["content_rules"] = ASSUMED
    if wrap_quotes or wrap_title or wrap_end:
        spec.wrappers = Wrapper(quotes=wrap_quotes, title=wrap_title, end=wrap_end)
        spec.provenance["wrappers"] = ASSUMED
    return ex
