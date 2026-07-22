# 0004 — Verifier suite v0

**Date:** 2026-07-21
**Result:** 21/21 tests passing on turing.

## Context

The verifier suite is the dependency root of the whole program, which is why it
was built first:

- `R_bind` and `R_exec` are verifier calls.
- The Phase-0 kill-gate probes (E0.3 self-consistency, E0.4 decomposition) cannot
  run without per-slot checkers.
- `defaults.json` measurement needs the same checkers to measure priors.
- Every gold training example is hard-gated on "passes all verifiers".

The taxonomy's central warning applies directly: a verifier that does not match
the evaluator's *literal* metric means training against a buggy checker
(Bucket B). So metric parity, not coverage, was the design priority.

## What was built

```
src/verbalized_defaults/
  metrics.py              IFEval-parity counting primitives
  schema.py               frozen 12-slot Spec, provenance, anti-gaming validator
  verifiers/
    base.py               SlotResult / SpecReport
    length.py             length_words | length_sentences | length_paragraphs
    case.py               case
    structure.py          structure + delimiters
    keywords.py           must_include + forbidden
    wrappers.py           wrappers + response_boundary
    language.py           language
    __init__.py           verify_spec() registry
tests/
  test_metrics.py         metric-parity pins
  test_verifiers.py       taxonomy-anchored failure cases
```

`verify_spec(text, spec) -> SpecReport` exposes exactly the three things the
program needs:

| Property | Consumer |
|---|---|
| `.ok` | hard gate on gold data |
| `.score` | dense `R_exec` reward (fraction of hard slots satisfied) |
| `.failures()` | per-slot patch signal for interleaved verification |

All 11 programmatic slots are covered. `register` is a soft slot: reported but
flagged `skipped`, so it is excluded from scoring rather than inflating it.

## Observations — metric parity

**1. The proposal's `length_words` definition is wrong and should be corrected.**
The experiment design §2 says length_words is verified by "whitespace tokens".
IFEval actually uses `nltk.tokenize.RegexpTokenizer(r"\w+")`:

```python
def count_words(text):
  tokenizer = nltk.tokenize.RegexpTokenizer(r"\w+")
  return len(tokenizer.tokenize(text))
```

These differ substantially — `"state-of-the-art"` is 1 whitespace token but 4
`\w+` tokens; `"don't"` is 1 vs 2. Since IFBench's `count:word_count_range` is
scored this way, **the suite implements `\w+`**. Verified by test.

**2. Sentences are Punkt, not a literal `.?!` split.** The design says "split on
`.?!` (NLTK punkt, same as IFEval)", which conflates two different things.
IFEval uses the Punkt tokenizer, which is materially smarter: it does not split
on abbreviation dots. This surfaced as a *test* bug — `"A. B. C. D."` counts as
2 sentences, not 4, because Punkt reads the single letters as abbreviations. The
verifier was right and the test was wrong; the test now uses real sentences.

**3. Paragraphs split on a blank line only.** `\n\n` starts a new paragraph, a
single `\n` does not — matching the Bucket-B case in the taxonomy (doc 435).

## Design decisions

- **`must_include` and `forbidden` use deliberately different policies.**
  `must_include` is word-boundary + case-insensitive (IFEval's
  `keywords:existence`), so inflections do not count: requiring `correlated` is
  *not* satisfied by `correlation`. `forbidden` is substring + case-insensitive,
  so morphological containment *does* count: banning `engage` fires on `engages`.
  This is the aggressive choice, taken to catch the real A4 derived-form leakage,
  and it carries a known risk of cross-lingual false positives (`heute` inside
  `heutige` — which the taxonomy classified as a Bucket-B artifact). The policy is
  configurable via `substring=False`. **Revisit before gold-data generation.**
- **`case: lower`/`upper` are strict across every zone** — a single capitalised
  proper noun or a `P.S.` prefix fails a lowercase spec. This is the taxonomy's
  A2 lesson encoded directly.
- **`structure: bullets` counts globally**, across the whole response, which is
  what makes the A3 "3 bullets total became 3 per stanza" failure detectable.
- **Anti-gaming validation is enforced in the schema**: an `[assumed]` length must
  be a point value or a range no wider than ±10%, so a declared `10–10000 words`
  is rejected by the parser itself; `bullets`/`sections` must name an exact count.

## Test coverage (taxonomy-anchored)

Each of the taxonomy's named failure modes is pinned by a test: P.S. left
uncased, proper noun left capitalised, 9 bullets against an "exactly 3" spec,
`******` (6) required but `*****` (5) produced, `correlated` required but
`correlation` written, `engage` banned but `engages` written.

## Open items

- **`structure: sections` counts markdown headers**, which is an approximation of
  IFEval's section-splitter semantics. Revisit when wiring real IFBench families.
- **No `<spec>` text parser yet.** `Spec` objects are constructed
  programmatically; parsing the model's emitted spec block is required before
  anything can emit or bind specs.
- **No parity harness yet.** Parity with IFEval is currently established by
  reading its source, not by measurement. The next step is to run these verifiers
  over real IFEval prompts and diff against the official
  `instruction_following_eval` verdicts — converting "anchored by inspection" into
  "verified agreement on N prompts".
