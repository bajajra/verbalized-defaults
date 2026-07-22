"""Measure how much of IFBench schema v2 can express -- WITHOUT fitting to it.

IFBench is the held-out OOD eval. We deliberately do **not** add slots to cover
its families: designing the representation by looking at the test set would
destroy the generalization claim. This script only *measures* and *classifies*.

Two separate questions, kept apart because they have very different answers:

1. **Is the family a real convention (Bucket A) or a gimmick (Bucket C)?**
   Bucket C is the taxonomy's category for character/word arithmetic and verbatim
   puzzles that no real user wants -- IFBench mixes many of these in, and the
   failure-taxonomy report already flagged them (ratio:*, syllable parity,
   prime word lengths, string reversal) as things to ignore, not to fix.

2. **Given it is real, can schema v2 express it?**

The classification below is a hand judgement, recorded here so it can be
reviewed and revised rather than hidden inside a function. Treat the derived
percentages as indicative, not precise.

    uv run python scripts/measure_ifbench_coverage.py
"""
from __future__ import annotations

import collections
import glob
import sys

# family -> (bucket, expressible_in_schema_v2, note)
#   bucket: "A" real convention | "C" gimmick / arithmetic (taxonomy Bucket C)
#   expressible: "yes" | "partial" | "no"
CLASSIFICATION: dict[str, tuple[str, str, str]] = {
    # --- lexical-class and arithmetic counting: gimmicks -------------------
    "count:conjunctions": ("C", "no", "counts a lexical class"),
    "count:numbers": ("C", "no", "counts a lexical class"),
    "count:person_names": ("C", "no", "counts a lexical class"),
    "count:pronouns": ("C", "no", "counts a lexical class"),
    "count:punctuation": ("C", "no", "punctuation arithmetic"),
    "count:unique_word_count": ("C", "no", "type-token arithmetic"),
    "count:words_japanese": ("C", "no", "script-specific word arithmetic"),
    "format:no_whitespace": ("C", "no", "character-level puzzle"),
    "sentence:alliteration_increment": ("C", "no", "letter puzzle"),
    "sentence:increment": ("C", "no", "length arithmetic per sentence"),
    "words:alphabet": ("C", "no", "letter puzzle"),
    "words:consonants": ("C", "no", "letter puzzle"),
    "words:last_first": ("C", "no", "letter-chaining puzzle"),
    "words:no_consecutive": ("C", "no", "letter puzzle"),
    "words:odd_even_syllables": ("C", "no", "syllable parity"),
    "words:palindrome": ("C", "no", "word puzzle"),
    "words:paragraph_last_first": ("C", "no", "letter-chaining puzzle"),
    "words:prime_lengths": ("C", "no", "prime word lengths"),
    "words:repeats": ("C", "no", "repetition arithmetic"),
    "words:vowel": ("C", "no", "letter puzzle"),
    "ratio:overlap": ("C", "no", "ratio arithmetic"),
    "ratio:sentence_balance": ("C", "no", "ratio arithmetic"),
    "ratio:sentence_type": ("C", "no", "ratio arithmetic"),
    "ratio:sentence_words": ("C", "no", "ratio arithmetic"),
    "ratio:stop_words": ("C", "no", "ratio arithmetic"),
    # --- expressible real conventions -------------------------------------
    "count:keywords_multiple": ("A", "yes", "must_include"),
    "count:word_count_range": ("A", "yes", "length_words range"),
    "format:options": ("A", "yes", "response_options"),
    "format:quotes": ("A", "yes", "wrappers.quotes"),
    "format:title_case": ("A", "yes", "case=title"),
    "repeat:repeat_simple": ("A", "yes", "response_boundary"),
    # --- real conventions, partially expressible ---------------------------
    "format:list": ("A", "partial", "delimiters capture the separator, not list semantics"),
    "format:no_bullets_bullets": ("A", "partial", "structure prose/bullets, semantics uncertain"),
    "format:parentheses": ("A", "partial", "wrappers start/end approximates it"),
    "format:quote_unquote": ("A", "partial", "wrappers, semantics uncertain"),
    # --- real conventions our schema cannot express ------------------------
    "format:emoji": ("A", "no", "emoji presence is not an exact string"),
    "format:line_indent": ("A", "no", "indentation not modelled"),
    "format:newline": ("A", "no", "newline discipline not modelled"),
    "format:output_template": ("A", "no", "free-form template not modelled"),
    "format:sub-bullets": ("A", "no", "nested structure; our bullets are flat"),
    "format:thesis": ("A", "no", "rhetorical structure not modelled"),
    "repeat:repeat_change": ("A", "no", "repeat with transformation"),
    "repeat:repeat_span": ("A", "no", "span-indexed repeat"),
    "sentence:keyword": ("A", "no", "sentence-level position; positional is paragraph-level"),
    "words:keywords_specific_position": ("A", "no", "word-index position not modelled"),
    "words:start_verb": ("A", "no", "POS-conditioned opening not modelled"),
    "words:words_position": ("A", "no", "word-index position not modelled"),
}
# every custom:* family is a bespoke one-off puzzle
_CUSTOM = ("C", "no", "bespoke one-off puzzle")


def classify(family: str) -> tuple[str, str, str]:
    if family.startswith("custom:"):
        return _CUSTOM
    return CLASSIFICATION.get(family, ("?", "no", "UNCLASSIFIED"))


def main() -> int:
    files = glob.glob(
        "/data/cache/huggingface/hub/datasets--allenai--IFBench_test/snapshots/*/data/*.parquet")
    if not files:
        print("IFBench_test parquet not found; snapshot_download it first", file=sys.stderr)
        return 1
    import pyarrow.parquet as pq

    rows = pq.read_table(files[0]).to_pylist()
    counts: collections.Counter = collections.Counter()
    for r in rows:
        for iid in r["instruction_id_list"]:
            counts[iid] += 1

    by_bucket: collections.Counter = collections.Counter()
    by_expr: collections.Counter = collections.Counter()
    a_by_expr: collections.Counter = collections.Counter()
    unclassified = []

    for fam, n in counts.items():
        bucket, expr, _ = classify(fam)
        if bucket == "?":
            unclassified.append(fam)
        by_bucket[bucket] += n
        by_expr[expr] += n
        if bucket == "A":
            a_by_expr[expr] += n

    total = sum(counts.values())
    print(f"IFBench rows: {len(rows)}   families: {len(counts)}   instances: {total}\n")

    print("--- bucket split (is the constraint a real convention at all?) ---")
    for b, label in (("A", "real convention"), ("C", "gimmick / arithmetic")):
        print(f"  Bucket {b} ({label:22s}) {by_bucket[b]:4d}  ({100.0*by_bucket[b]/total:5.1f}%)")

    print("\n--- schema v2 expressiveness over ALL instances ---")
    for e in ("yes", "partial", "no"):
        print(f"  {e:8s} {by_expr[e]:4d}  ({100.0*by_expr[e]/total:5.1f}%)")

    a_total = by_bucket["A"]
    print(f"\n--- schema v2 expressiveness over BUCKET A only (n={a_total}) ---")
    for e in ("yes", "partial", "no"):
        print(f"  {e:8s} {a_by_expr[e]:4d}  ({100.0*a_by_expr[e]/a_total:5.1f}%)")

    if unclassified:
        print(f"\nUNCLASSIFIED families (fix the table): {sorted(unclassified)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
