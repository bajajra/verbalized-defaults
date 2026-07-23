"""Person and content-policy verifiers — the programmatic half of schema v3.

Both exist because decomposing `register` turned prose the judge had to read into
predicates a program can check. That is the payoff of the decomposition: `person`
and four content rules move from *unscoreable* to *free at reward time*.

Semantic content rules ("no political content") stay in ``Spec.content_rules``
and are judge-scored — deliberately a separate slot, so a scored verdict is never
mixed with an unscored one.
"""
from __future__ import annotations

import re

from ..schema import ContentPolicy
from .base import SlotResult

FIRST = r"\b(?:I|me|my|mine|myself|we|us|our|ours|ourselves)\b"
SECOND = r"\b(?:you|your|yours|yourself|yourselves)\b"
THIRD = r"\b(?:he|him|his|she|her|hers|it|its|they|them|their|theirs)\b"

_FIRST_RE = re.compile(FIRST)          # case-sensitive: "I" is meaningful
_SECOND_RE = re.compile(SECOND, re.I)
_THIRD_RE = re.compile(THIRD, re.I)

_URL_RE = re.compile(r"https?://|www\.[a-z0-9-]+\.[a-z]{2,}", re.I)
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)
# Small, deliberately mild list. A reward signal built on profanity detection
# should use a maintained lexicon, not this.
_PROFANITY = {"damn", "hell", "crap", "shit", "fuck", "bastard", "bitch", "ass"}
_PROFANITY_RE = re.compile(r"\b(?:" + "|".join(_PROFANITY) + r")\b", re.I)


def count_person(text: str) -> dict[str, int]:
    return {
        "first": len(_FIRST_RE.findall(text)),
        "second": len(_SECOND_RE.findall(text)),
        "third": len(_THIRD_RE.findall(text)),
    }


def check_person(text: str, want: str) -> SlotResult:
    """Grammatical person by pronoun scan.

    'third' is checked strictly as *absence of first-person pronouns* rather than
    dominance of third-person ones: a third-person essay that says "I think" has
    broken the convention even if third-person pronouns outnumber it.
    """
    c = count_person(text)
    if want == "first":
        ok = c["first"] > 0
    elif want == "second":
        ok = c["second"] > 0
    elif want == "third":
        ok = c["first"] == 0
    else:
        raise ValueError(f"unknown person {want!r}")
    return SlotResult(
        "person", ok, f"{want} person", c,
        detail="" if ok else f"pronoun counts {c}",
    )


def check_content_policy(text: str, p: ContentPolicy) -> SlotResult:
    violations: list[str] = []
    if p.no_urls and (m := _URL_RE.search(text)):
        violations.append(f"url {m.group(0)!r}")
    if p.no_emoji and (m := _EMOJI_RE.search(text)):
        violations.append("emoji present")
    if p.no_profanity and (m := _PROFANITY_RE.search(text)):
        violations.append(f"profanity {m.group(0)!r}")
    if p.no_first_person and (n := len(_FIRST_RE.findall(text))):
        violations.append(f"{n} first-person pronoun(s)")
    ok = not violations
    return SlotResult(
        "content_policy", ok, p.describe(),
        "clean" if ok else "; ".join(violations),
    )
