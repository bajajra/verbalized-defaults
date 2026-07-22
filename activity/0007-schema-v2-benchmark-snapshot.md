# 0007 — Schema v2: the benchmark snapshot

**Date:** 2026-07-21
**Result:** 45/45 tests passing. Prompts fully expressible went **59.5% → 93.5%**;
instruction instances mapped **71.1% → 95.8%**. This is the frozen benchmark
snapshot for E0.1 and `R_bind`.

## Context

[0006](0006-ifeval-adapter-and-schema-coverage.md) measured that the v1 12-slot
schema could express only 59.5% of IFEval prompts, which risked a *false kill* at
Gate 1: an oracle-prefill probe on partly-inexpressible prompts would show
diluted lift, and a coverage problem would read as evidence against H0.

Decision taken: close the gap rather than subset the probe. Model every real
constraint family; exclude only genuine gimmicks.

## Schema v1 → v2 (12 → 15 slots)

**New slots**

| Slot | Models | Covers |
|---|---|---|
| `markup` | `highlights`, `placeholders`, `caps_words` counts | highlighted sections, placeholders, ALL-CAPS word frequency |
| `positional` | paragraph N starts with word W | `nth_paragraph_first_word` |
| `response_options` | answer must be one of a fixed option set | `constrained_response` |

**Extended slots**

- `wrappers` gained `title` — a `<<wrapped title>>` is present.
- `must_include` (`Keyword`) gained `max_count`, so an *upper* bound on keyword
  frequency is expressible, not just a floor.
- `structure` gained a `splitter` and a `responses` kind: `sections` can now be
  counted by IFEval's splitter semantics rather than approximated with markdown
  headers, and multi-response decomposition is a first-class structure.

`markup` deliberately bundles three dimensions into one slot, following the
precedent already set by `wrappers` (quotes + title + start + end): it passes
only if every declared dimension passes, and names the ones that failed.

## Parity notes for the new counters

Each new counter mirrors IFEval's own checker rather than a reasonable-looking
reimplementation:

- **highlights** — counts both `*single*` and `**double**` spans with non-empty
  content (IFEval counts both forms separately).
- **placeholders** — non-greedy `[...]` spans.
- **caps_words** — word-tokenised tokens where `token.isupper()`.
- **sections** — split on `\s?<splitter>\s?\d+\s?` and take `len(parts) - 1`,
  because text before the first splitter is not a section.
- **responses** — split on the separator, require exactly N non-empty parts *and*
  that they are distinct (IFEval requires the two responses to differ).
- **positional** — first token of the target paragraph, lowercased, leading
  quotes stripped, truncated at the first punctuation character.

## Coverage: before and after

| | v1 | v2 |
|---|---:|---:|
| mapped | 593 (71.1%) | **799 (95.8%)** |
| partial | 37 (4.4%) | 2 (0.2%) |
| unmapped | 204 (24.5%) | 33 (4.0%) |
| **prompts fully expressible** | 322/541 (59.5%) | **506/541 (93.5%)** |

Excluding the deliberately-out-of-scope family, v2 expresses **799 of 801
in-scope instruction instances (99.75%)**.

## What remains unexpressible, and why that is correct

1. **`keywords:letter_frequency` — 33 instances (4.0%).** Letter arithmetic
   ("use the letter 'a' at least 5 times"). This is Bucket C in the taxonomy: a
   constraint no real user wants, testing character counting rather than a
   generation convention. Modelling it would bloat the schema and teach the model
   to satisfy a gimmick. **Excluded on purpose, permanently.**
2. **Structure-slot conflicts — 2 instances (0.2%).** A prompt asking for two
   structure constraints at once (e.g. sections *and* bullets) can only fill the
   single `structure` slot; the second claim is reported as `partial`. Making
   `structure` a list would fix it, but 2/834 does not justify the schema
   complexity or the reward-accounting ambiguity. Reported honestly instead.

## Status

This is the **benchmark snapshot**: schema v2 is what E0.1's oracle prefill will
use and what `R_bind` will score against. The 93.5% figure is the ceiling on how
much of IFEval an oracle spec can carry, and it should be quoted alongside any
Gate 1 result.

## Open items

- Run the same coverage analysis on **IFBench** — its 58 held-out families are the
  real OOD eval and were designed to be unlike IFEval's, so coverage there will
  likely be lower and is the more informative number.
- Carried over: `forbidden` substring-vs-word-boundary default.
