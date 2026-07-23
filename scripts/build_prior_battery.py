"""Author the prior-targeted battery (E4.1).

Every other experiment so far measured either restating explicit constraints or
self-consistency when nothing is asked. This is the first battery built to make a
latent default *collide* with an explicit instruction — the "silent fight" the
whole project is about. Each prompt states a constraint that a known genre/format
prior actively resists, and a programmatic checker for whether the prior was
overridden.

The five priors are the taxonomy's named A1–A3 failures:

  poem_lowercase        verse auto-capitalises each line; instruction says lowercase
  proper_noun_lowercase proper nouns keep their capital; instruction says lowercase
  ps_recase             "P.S." resists recasing; instruction says lowercase
  global_bullets        a global count gets applied per-stanza
  length_2x             genre natural-length prior undershoots a 2x target

Written before any training and frozen, per the design.

    uv run python scripts/build_prior_battery.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prior_battery.jsonl"

POEM_TOPICS = ["the sea in winter", "a city at dawn", "an old train station",
               "the last day of summer", "a lighthouse", "falling snow",
               "a crowded market", "the moon over water", "an empty playground",
               "autumn leaves", "a mountain village", "the desert at night",
               "a river in spring", "a quiet library", "the first frost"]

TRAVEL_PLACES = [
    ("Paris", "France"), ("Tokyo", "Japan"), ("Rome", "Italy"),
    ("Cairo", "Egypt"), ("Sydney", "Australia"), ("Nairobi", "Kenya"),
    ("Lima", "Peru"), ("Oslo", "Norway"), ("Delhi", "India"),
    ("Toronto", "Canada"), ("Lisbon", "Portugal"), ("Seoul", "Korea"),
    ("Athens", "Greece"), ("Havana", "Cuba"), ("Reykjavik", "Iceland")]

NOTE_TOPICS = ["a birthday gift", "help moving house", "a dinner invitation",
               "career advice", "a warm welcome", "a thoughtful card",
               "covering a shift", "a book recommendation", "a kind favour",
               "a job referral", "a home-cooked meal", "weekend hospitality",
               "a ride to the airport", "patient tutoring", "a listening ear"]

# genre -> natural median words (from the prior inventory, defaults.json)
NATURAL = {"apology_note": 136, "email": 203, "poem": 167, "review": 537,
           "product_description": 317, "social_post": 271}
LEN_TOPICS = {
    "apology_note": ["missing a friend's birthday", "a late delivery",
                     "forgetting a meeting", "a billing error", "a rescheduled visit"],
    "email": ["a broken radiator", "a project update", "a deadline extension",
              "a team introduction", "a schedule change"],
    "review": ["a coffee shop", "a science fiction novel", "a budget phone",
               "a hiking backpack", "a neighbourhood diner"],
    "social_post": ["finishing a marathon", "a grand opening",
                    "a photography exhibit", "a charity drive", "a product launch"],
}


def rows():
    out = []

    for t in POEM_TOPICS:
        out.append({"prior": "poem_lowercase",
                    "prompt": f"Write a short poem about {t}. Write it entirely in "
                              "lowercase — do not use any capital letters anywhere.",
                    "check": {"case": "lower"}})

    for city, country in TRAVEL_PLACES:
        out.append({"prior": "proper_noun_lowercase",
                    "prompt": f"Write a short travel paragraph about visiting {city} "
                              f"in {country}. Write it entirely in lowercase — do not "
                              "capitalise anything, including place names.",
                    "check": {"case": "lower"}})

    for t in NOTE_TOPICS:
        out.append({"prior": "ps_recase",
                    "prompt": f"Write a short thank-you note about {t}. Write the "
                              "whole note in lowercase, and end it with a postscript. "
                              "Everything, including the postscript marker, must be "
                              "lowercase.",
                    "check": {"case": "lower", "must_include_ci": "p.s"}})

    for t in POEM_TOPICS[:15]:
        out.append({"prior": "global_bullets",
                    "prompt": f"Write a three-stanza poem about {t}. Somewhere in the "
                              "poem include exactly three bullet points in total "
                              "across the whole poem — three bullets altogether, not "
                              "three per stanza.",
                    "check": {"structure_bullets": 3}})

    for genre, topics in LEN_TOPICS.items():
        target = 2 * NATURAL[genre]
        label = genre.replace("_", " ")
        for t in topics:
            out.append({"prior": "length_2x",
                        "prompt": f"Write a {label} about {t}. Make it at least "
                                  f"{target} words long.",
                        "check": {"length_words_min": target}, "genre": genre})
    return out


def main() -> int:
    data = rows()
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w") as fh:
        for i, r in enumerate(data):
            r["key"] = f"{r['prior']}:{i}"
            fh.write(json.dumps(r) + "\n")
    import collections
    c = collections.Counter(r["prior"] for r in data)
    print(f"wrote {len(data)} prompts to {OUT}")
    for prior, n in c.items():
        print(f"  {prior:24s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
