# 0019 — Correction: length underproduction is universal, not model-specific

**Date:** 2026-07-22
**Status:** retracts the headline of [0017](0017-e03-three-models-family-beats-size.md)
and the framing in [0016](0016-quantitative-magnitude-and-qualitative-inventory.md).

All E0.3 metrics recomputed from stored declarations using the de-biased
extractor from [0018](0018-e02-binding-and-per-slot-execution.md). Generation was
not repeated; only measurement.

## The reversal

| model (concrete cue) | len median **before** | **after** | under-target after |
|---|---:|---:|---:|
| Qwen3.5-2B | −26% | **−31%** | 82% |
| Gemma E2B | **−5%** | **−30%** | 79% |
| Gemma E4B | **−1%** | **−29%** | 90% |

**Every model underproduces against its own declared length by roughly 30%, with
79–90% of responses landing short.**

### Why the earlier numbers were wrong

The extractor could not parse Gemma's declaration format — `Paragraph count: 4`,
`Exactly three paragraphs`, `Bullet Points: 0` — so for Gemma it only captured the
minority of declarations written in Qwen-like prose. That subset was **not
representative**: it happened to be the well-behaved tail. Measuring it produced
"Gemma misses by 1%", which was a statement about our regexes, not the model.

This is a textbook selection artefact, and it is worth naming precisely: **a
measurement instrument that fails on some inputs does not produce noisy data, it
produces biased data**, because the inputs it fails on are rarely a random sample.

## What is retracted

1. **[0016] "Systematic underproduction is Qwen-specific."** No — universal.
2. **[0017] "Length underproduction is a FAMILY effect, not a size effect."** No —
   it is neither. The E2B control was sound in design; the instrument fed it bad
   data. At the same size *and* across families, all three models underproduce
   ~30%.

The E2B control still did its job — it just answered a different question than I
claimed. Family and size both turn out to be irrelevant to this metric.

## What survives, and is now stronger

The universal result **agrees with the per-slot execution gradient** in 0018
(length accuracy 7–16% on all three models) instead of sitting awkwardly beside
it. Two independent measurements now say the same thing: **no model tested can
hold a running count against a target it set itself.** That is the missing
count→gap→extend loop, and it is a property of current small models generally,
not of any family.

## Other revised numbers

| model / cue | self-cons before → after | perfect before → after |
|---|---|---|
| Qwen concrete | 0.495 → **0.468** | 0.008 → 0.000 |
| E2B concrete | 0.425 → **0.376** | 0.008 → 0.000 |
| E4B concrete | 0.460 → **0.436** | 0.065 → 0.028 |
| Qwen soft | 0.496 → **0.515** | 0.405 → 0.393 |
| E2B soft | 0.446 → **0.224** | 0.429 → 0.207 |
| E4B soft | 0.667 → **0.160** | 0.667 → 0.160 |

**Self-consistency on the concrete cue holds at ~0.38–0.47** — slightly lower than
before because more slots are now captured, so there is more to violate. The
central claim ("the model obeys about half of what it declares") survives, and
should be quoted as **~0.4** rather than ~0.5.

**The soft-cue Gemma numbers were meaningless and are now corrected.** E4B's
previously reported 0.667 self-consistency was computed over ~0.2 slots per
response — it "kept" its declarations because it barely made any. With better
extraction it is **0.160**. Any metric computed over a near-empty declaration set
should be treated as undefined, not as a high score.

Perfect-compliance is now ~0 on the concrete cue for all three models: **not one
response in 120 fully honours its own declaration** on Qwen and E2B.

## Methodological rule this establishes

**When the instrument changes, every stored number is stale.** Comparing a fresh
measurement against a frozen summary silently mixes two instruments.
`scripts/recompute_e03.py` now re-derives all E0.3 metrics from stored raw
generations, so a single extractor version scores every model. Run outputs should
be treated as *raw data plus a snapshot*, never as the authoritative metric.

## Open items

- Regenerate the stored `*.json` summaries, or delete them so the recompute path
  is the only source of truth.
- E0.4 still blocked (binding recorded, answer not scored).
- `repeat_prompt` 0% binding on all three models remains unexplained — possible
  adapter slot-mapping artefact rather than a real failure.
