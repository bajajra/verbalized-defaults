"""Categorise the *qualitative* conventions a model verbalizes.

`spec_extract` handles conventions a verifier can score — counts, casing,
structure. But when asked to declare its conventions the model also volunteers a
large body of statements no programmatic checker can touch:

    "Write in the third person."   "Maintain an objective yet engaging tone."
    "Use clear language with no jargon."   "Keep sentences relatively short."

Discarding these as "unextractable" would be a mistake. They are latent defaults
being verbalized — exactly the phenomenon the project is about — and they are the
model's *natural* convention vocabulary, which turns out to be stylistic rather
than metric. This module inventories them so the qualitative half is measured
rather than thrown away.

The output serves two purposes: it says which dimensions the model has
*articulable* priors on (a superset of the typed schema), and it tells us whether
the single soft `register` slot is hiding several distinct dimensions that
deserve separating.

Rule-based and inspectable, like the typed extractor. Themes are keyword
patterns, not a classifier, so the mapping can be audited and revised.
"""
from __future__ import annotations

import re
from collections import Counter

# theme -> pattern. A line may carry several themes; all are recorded.
THEMES: dict[str, str] = {
    "tone_register": r"\btone\b|\bvoice\b|\bwarm\b|\bfriendly\b|\bobjective\b|\bformal\b"
                     r"|\binformal\b|\bprofessional\b|\bconversational\b|\bplayful\b"
                     r"|\bserious\b|\bneutral\b|\bencouraging\b|\bempathetic\b|\bcasual\b",
    "person_perspective": r"\b(?:first|second|third)[- ]person\b|\bpoint of view\b"
                          r"|\bperspective\b|\baddress the reader\b",
    "clarity_simplicity": r"\bclear\b|\bclarity\b|\bsimple\b|\bplain language\b|\bjargon\b"
                          r"|\baccessible\b|\beasy to understand\b|\bstraightforward\b"
                          r"|\bconcise\b|\bwordy\b|\bverbose\b|\bdirect\b",
    "audience": r"\baudience\b|\breader\b|\blayperson\b|\bbeginner\b|\bexpert\b"
                r"|\bgeneral public\b|\bnon-technical\b",
    "narrative_structure": r"\bintroduction\b|\bconclusion\b|\bbody paragraph"
                           r"|\bflow\b|\blogical\b|\bcoheren|\btransition"
                           r"|\bopening\b|\bclosing\b|\bnarrative arc\b|\bsign-?off\b",
    "formatting_style": r"\bmarkdown\b|\bbold\b|\bitalic\b|\bplain text\b|\bformatting\b"
                        r"|\bheaders?\b|\bemoji\b",
    "factuality": r"\baccurate\b|\bfactual\b|\bevidence\b|\bcite\b|\bcitation\b"
                  r"|\bspeculat|\bverif|\btruthful\b|\bmake up\b|\bhallucin",
    "engagement": r"\bengaging\b|\binteresting\b|\bcompelling\b|\bvivid\b|\bdescriptive\b"
                  r"|\bevocative\b|\bimagery\b|\bhook\b",
    "completeness": r"\bcomprehensive\b|\bthorough\b|\bdetailed\b|\bcover (?:all|the)\b"
                    r"|\bcomplete\b|\bin depth\b|\bin-depth\b",
    "hedging_confidence": r"\bhedge\b|\bdefinitive\b|\bconfident\b|\bcaveat\b|\buncertain"
                          r"|\bqualif(?:y|ier)\b|\bavoid absolutes?\b",
    "grammar_mechanics": r"\bgrammatical\b|\bgrammar\b|\bpunctuation\b|\bspelling\b"
                         r"|\bsyntax\b|\btypo",
    "safety_scope": r"\bsafe\b|\bharm\b|\bappropriate\b|\bsensitive\b|\bdisclaim",
    # Discovered empirically: under a soft cue the model volunteers a large
    # self-imposed CONTENT POLICY nobody asked for -- "no advertising", "no
    # political statements", "no personal anecdotes", "no external links". This
    # was 61% of unthemed lines and is a whole default-bearing dimension the
    # typed schema does not model at all.
    "content_exclusion": r"\bno (?:external )?(?:links?|urls?)\b|\bno personal\b"
                         r"|\bno advertis|\bno politic|\bno religio|\bno offensive\b"
                         r"|\bno harmful\b|\bno explicit\b|\bno violen|\bno illegal\b"
                         r"|\bno controversial\b|\bno profan|\bno slur|\bno stereotyp"
                         r"|\bavoid (?:politic|religio|controversial|offensive)"
                         r"|\bno anecdote|\bno opinion|\bno speculation\b",
    "content_inclusion": r"\binclude a (?:title|heading|call to action|summary|conclusion)"
                         r"|\bcall to action\b|\binclude (?:citations?|examples?|sources?)"
                         r"|\badd a (?:title|summary|note)\b",
}

_COMPILED = {k: re.compile(v, re.I) for k, v in THEMES.items()}


def classify_line(line: str) -> list[str]:
    """Return every theme a single convention statement matches."""
    return [name for name, rx in _COMPILED.items() if rx.search(line)]


def inventory(lines: list[str]) -> tuple[Counter, list[str]]:
    """-> (theme counts, lines matching no theme).

    The unmatched list is returned rather than dropped: it is the frontier of
    convention types we have not learned to name yet.
    """
    counts: Counter = Counter()
    unmatched: list[str] = []
    for line in lines:
        themes = classify_line(line)
        if themes:
            counts.update(themes)
        else:
            unmatched.append(line)
    return counts, unmatched
