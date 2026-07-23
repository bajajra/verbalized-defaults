# 0021 — The length finding, on untruncated data at last

**Date:** 2026-07-23
**Status:** retracts 0019's "universal underproduction" and corrects 0018's
per-slot gradient. This is the fourth version of the length finding and the first
computed on complete answers.

## The artefact that survived three write-ups

The original E0.3 runner stored answers capped at **2000 characters**. That cap
truncated a large fraction of genre answers and deflated every length-derived
metric — and it was present the whole time, through four analyses, because I
never checked answer completeness before computing a length statistic.

| model | genre answers hitting the 2000-char cap |
|---|---:|
| Qwen3.5-2B | 24% |
| Gemma E2B | (high) |
| Gemma E4B | **80%** |

E4B routinely declares 400–500 word essays; the stored answer maxed out at 373
words. So `count_words(stored_answer)` measured the cap, not the model.

## The correction (untruncated runstore data, same protocol)

| model | self-consistency | length median (vs declared) | length_words accuracy |
|---|---|---|---|
| | trunc → **full** | trunc → **full** | trunc → **full** |
| Qwen3.5-2B | 0.468 → **0.457** | −31% → **−22%** | 0.075 → **0.067** |
| Gemma E2B | 0.376 → **0.439** | −30% → **+0.3%** | 0.125 → **0.275** |
| Gemma E4B | 0.436 → **0.529** | −29% → **+0.3%** | 0.124 → **0.41** |

## What is now true

**Length underproduction is Qwen-specific and milder than reported.** Qwen misses
its own declared word count by −22% (median); **both Gemmas hit it on the nose
(+0.3%)**. 0019's "universal ~30%" was the truncation artefact — the Gemmas
*looked* like they underproduced only because their longer answers were clipped.

The irony: 0016/0017's original instinct ("Qwen underproduces, Gemma doesn't")
was closer to correct than 0019's "universal" retraction of it. But 0017 got the
right answer for the wrong reason (a biased extractor sampling Gemma's
well-behaved tail). Only now, with a clean extractor *and* complete answers, is
the family effect real.

**Per-slot execution gradient, corrected:**

| slot | Qwen | E2B | E4B |
|---|---:|---:|---:|
| language | 1.00 | 1.00 | 1.00 |
| case | 0.80 | 0.64 | 0.53 |
| structure | 0.52 | 0.81 | 0.70 |
| length_paragraphs | 0.10 | 0.01 | 0.00 |
| length_words | **0.07** | **0.28** | **0.41** |

Two distinct facts the truncated data had merged:

1. **`length_words` is NOT a universal catastrophe.** It is Qwen-specific (0.07).
   Gemma does moderately well (0.28–0.41) once answers are not clipped. 0018's
   "identical gradient, length 7–16% everywhere" was truncation-driven for Gemma.
2. **`length_paragraphs` IS universally catastrophic (0.00–0.10), and it is real.**
   Paragraph count does not inflate with answer length the way word count does, so
   truncation does not explain it. Models cannot hit an *exact paragraph count*
   even when they can hit an approximate word count.

That distinction is itself the insight: an **approximate floor** ("about 400
words") is satisfiable; an **exact count** ("exactly 4 paragraphs") is not. The
count→gap→extend loop is missing specifically for exact counts.

## The triangle that exposed it (untruncated)

Correlation between declared and actual word count rises with capability —
**+0.41 (Qwen), +0.89 (E2B), +0.96 (E4B)**. The declaration is a real plan the
model increasingly follows. And declaring *above* a `>= N` requirement acts as a
buffer: over-declarers pass at 70–87% vs 59–64% for at-target declarers. Declaring
"the wrong value" (450 for ≥300) is frequently **adaptive**, not an error — the
model pads against its own undershoot.

## Correction to 0020

The "33.5% of bound slots carry the wrong value" figure used exact equality, which
wrongly flags "declared 450 for ≥300" as wrong when it is a valid binding. Under
the correct `satisfied_by` test the figure is **17.6%**, and `binding.py` (hence
the E0.4 recall numbers) already uses the correct test.

## Methodology rule

**Never compute a length metric without first verifying answers are complete.**
`finish_reason == "length"` and a hard storage cap are different failure modes;
both must be excluded. The runstore removes the storage cap; a `finish_reason`
check must still gate any length statistic. This artefact cost four write-ups
because completeness was assumed, never checked.

## Self-consistency headline, updated

Obeys about half of its own declaration, now **0.457 / 0.439 / 0.529** (was
0.468 / 0.376 / 0.436). The headline survives; the Gemmas are a few points higher
than reported. Quote as **~0.45–0.53**.
