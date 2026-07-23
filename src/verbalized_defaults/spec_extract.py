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

# Models spell numbers out ("Exactly three paragraphs", "One single paragraph")
# as readily as they use digits. A digit-only pattern set silently under-counts
# every such declaration.
_NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
             "twelve": 12, "fifteen": 15, "twenty": 20, "single": 1, "zero": 0}
_NUM = r"(?:\d+|" + "|".join(sorted(_NUMWORDS, key=len, reverse=True)) + r")"


def _n(s: str) -> int:
    return int(s) if s.isdigit() else _NUMWORDS[s.lower()]


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
        # "Paragraph count: 4", "Words: 250" -- value FOLLOWS the label. Gemma
        # declares almost exclusively this way; a prose-only pattern set scored
        # those declarations as unextractable, which looked like model vagueness
        # but was our own format bias.
        if m := re.search(r"\b" + u + r"(?:\s+count)?\s*:+\s*(" + _NUM + r")\b",
                          line, re.I):
            return slot, LengthConstraint.eq(_n(m.group(1)), unit)
        if m := re.search(r"(" + _NUM + r")\s*(?:-|–|to)\s*(" + _NUM + r")\s+" + u + r"\b",
                          line, re.I):
            return slot, LengthConstraint.between(_n(m.group(1)), _n(m.group(2)), unit)
        if m := re.search(_MIN + r"\s+(?:about\s+)?(" + _NUM + r")\s+" + u + r"\b",
                          line, re.I):
            return slot, LengthConstraint.at_least(_n(m.group(1)), unit)
        if m := re.search(_MAX + r"\s+(?:about\s+)?(" + _NUM + r")\s+" + u + r"\b",
                          line, re.I):
            return slot, LengthConstraint.at_most(_n(m.group(1)), unit)
        if m := re.search(r"(" + _NUM + r")\+\s+" + u + r"\b", line, re.I):
            return slot, LengthConstraint.at_least(_n(m.group(1)), unit)
        # A hedged figure must not become a point value: "~650 words" verified as
        # exactly 650 would fail almost always and deflate self-consistency into
        # an artefact of our own parser. Hedges become the +/-10% window the
        # schema's anti-gaming rule allows for an assumed length.
        if m := re.search(r"\b(?:about|around|approximately|roughly|~|circa)\s*("
                          + _NUM + r")\s+" + u + r"\b", line, re.I):
            v = _n(m.group(1))
            return slot, LengthConstraint.between(round(v * 0.9), round(v * 1.1), unit)
        if m := re.search(r"\b(?:exactly\s+)?(" + _NUM + r")\s+" + u + r"\b",
                          line, re.I):
            return slot, LengthConstraint.eq(_n(m.group(1)), unit)
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
        elif re.search(r"\b(?:sentence case|standard|normal|proper|conventional)\b"
                       r"[\w ]{0,25}\bcapitali[sz]ation\b|\bstandard case\b", low):
            spec.case, spec.provenance["case"] = "standard", ASSUMED
            hit = True

        if re.search(r"\b(?:do not use|don't use|avoid|without|no)\s+bullet", low):
            spec.structure = Structure("prose")
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif m := re.search(r"\bbullet\s*points?\s*:+\s*(" + _NUM + r")\b", low):
            n_ = _n(m.group(1))
            spec.structure = Structure("prose") if n_ == 0 else Structure("bullets", n_)
            spec.provenance["structure"] = ASSUMED
            hit = True
        elif m := re.search(r"(" + _NUM + r")\s+bullet", low):
            spec.structure = Structure("bullets", _n(m.group(1)))
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
            if (re.search(r"\blanguage\s*:+\s*(?:[\w]+\s)?" + name + r"\b", low)
                    or re.search(r"\bin\s+(?:[\w]+\s)?" + name + r"\b", low)
                    or low.strip().rstrip(".") == name):
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
