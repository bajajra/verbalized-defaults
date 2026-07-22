# 0005 — Spec parser and measured IFEval parity

**Date:** 2026-07-21
**Result:** 30/30 tests passing; exact metric agreement with IFEval on 412 samples.

## Context

Two gaps left open by [0004](0004-verifier-suite-v0.md):

1. `Spec` objects could only be built programmatically — nothing could read or
   emit the `<spec>` block the model is supposed to produce, which blocks both
   generation and `R_bind`.
2. Parity with IFEval was established by *reading its source*, not by
   measurement. That is exactly the kind of claim the project's own methodology
   says should be verified rather than asserted.

## 1. Canonical spec format (decision)

The proposal shows an illustrative, prose-y spec block (multiple slots per line,
free-text values, em-dash for "none"). That is fine as prose but not as a machine
contract, so this defines the **canonical form**: one slot per line,
`slot: value [provenance]`, with a strict grammar per slot.

```
<spec>
length_words: 300 [assumed]
length_sentences: >=5 [given]
case: lower [given]
structure: bullets=3 [given]
delimiters: "******" [given]
must_include: "banana"x2, "apple" [given]
forbidden: "utilize" [given]
wrappers: quotes, end="THE END" [given]
language: en [assumed]
register: playful [assumed]
response_boundary: "Answer:" [given]
</spec>
```

Grammar notes: lengths are `300` (point), `>=50`, `<=100`, or `280-320`;
structure is `prose | bullets=N | sections=N | json | table`; string lists are
double-quoted with optional `xN` minimum counts; `—`/`none`/`n/a` explicitly
declares a slot unconstrained. The parser also accepts two aliases from the
proposal's illustrative format — `length: ~300 words` (unit-inferred) and
`audience:` (→ `register`) — so specs written in the paper's style still parse.

**Decision: parsing is lenient, never raising.** `parse_spec` returns a
`ParseResult` carrying both the recovered `Spec` and a list of errors. A
malformed, duplicated, untagged or hallucinated slot is precisely the signal
`R_bind` must measure and penalise; raising would discard it. Recoverable slots
still parse alongside the errors.

Missing `[given]`/`[assumed]` tags are recorded as errors rather than silently
defaulted — provenance is the contribution, so an untagged slot is a defect.

## 2. Measured IFEval parity (result)

`scripts/fetch_ifeval_reference.py` downloads IFEval's own
`instructions_util.py` and its 541-prompt `input_data.jsonl` into `reference/`
(gitignored, not vendored — third-party Apache-2.0 code). `tests/test_ifeval_parity.py`
then diffs our counters against IFEval's own functions sample by sample.

| Metric | Samples diffed | Mismatches |
|---|---|---|
| `count_words` | 412 | **0** |
| `count_sentences` | 412 | **0** |

The corpus is 400 real IFEval prompts plus 12 adversarial strings chosen to break
naive implementations: contractions (`don't`), hyphenates
(`state-of-the-art`), abbreviations (`Dr.`, `p.m.`, `e.g.`), decimals (`3.14159`),
markdown, currency, and unicode punctuation. A third test asserts the corpus is
actually ≥100 prompts, so the parity tests cannot silently pass on a handful of
strings if the download fails.

The tests skip cleanly when `reference/` is absent, so the suite stays runnable
offline.

## Observations

- The IFEval prompt file is **not** at the HuggingFace path
  `google/IFEval/resolve/main/input_data.jsonl` (404). The canonical copy is in
  the google-research repo next to the verifier code, which is also the version
  the reference implementation was written against — better provenance anyway.
- Parity now covers the *metric primitives*. It does **not** yet cover the slot
  verifiers against IFEval's per-instruction checkers; that is a larger job
  because it needs response text, not just prompts.

## Open items

- **Extend parity to the instruction checkers.** Diff our slot verifiers against
  IFEval's `instructions.py` checkers over generated responses. This is the
  remaining Bucket-B exposure.
- **`structure: sections`** still approximates IFEval's section-splitter with a
  markdown-header count (carried over from 0004).
- **`forbidden` substring-vs-word-boundary default** remains unresolved and must
  be settled before gold-data generation (carried over from 0004).
- No prompt→constraint extractor yet, so `R_bind` cannot be computed end-to-end:
  the spec side is now readable, but the prompt side is not.
