# 0018 — E0.2 binding, per-slot execution, and an extractor that was biased

> **PARTIALLY SUPERSEDED.** Binding recall (0.485/0.540/0.559) is superseded by value-aware [0020]; the length accuracy (7–16%) by untruncated [0021]. The extractor de-biasing and the case/structure gradient stand.

**Date:** 2026-07-22
**Models:** Qwen3.5-2B, Gemma 4 E2B, Gemma 4 E4B.
E0.2 on 200 IFEval prompts × 2 samples; E0.3 per-slot on 60 genre prompts × 2.

## 0. First: the extractor was measuring us, not the models

0017 flagged that extraction coverage (0.66 Qwen vs 0.41–0.43 Gemma) might be our
bias. It was. Inspecting Gemma's unextracted lines showed the regexes were
**format-biased, not model-biased**:

| Gemma writes | why our pattern missed it |
|---|---|
| `Bullet Points: 0.` | pattern needed `0 bullet` — value follows the label |
| `Paragraph count: 4` | same inversion |
| `Language:: English.` | pattern needed `in English` |
| `Exactly three paragraphs.` | **number word**, not a digit |
| `Use standard American English capitalization.` | words intervene in `standard…capitalization` |
| `Do not use bullet points.` | no negation pattern |

Fixed all six classes. Effect:

| model / cue | coverage before → after | slots before → after |
|---|---|---|
| Qwen concrete | 0.656 → 0.691 | 4.47 → 4.67 |
| Gemma E2B concrete | 0.427 → 0.481 | 3.62 → 4.09 |
| **Gemma E4B concrete** | 0.414 → **0.555** | 3.13 → **4.16** |
| Qwen soft | 0.115 → 0.184 | 0.93 → 1.63 |

**This retracts a conclusion.** 0017 recorded "the bigger model declares less, not
more" from 4.47 / 3.62 / 3.13 slots. After the fix it is **4.67 / 4.09 / 4.16** —
the gap shrank by ~60% and was largely our instrument. All three models declare
roughly the same number of conventions.

## 1. E0.3 per-slot: an execution-difficulty gradient, identical on all three models

Accuracy = of the times a slot was declared, how often the response satisfied it.

| slot | Qwen3.5-2B | Gemma E2B | Gemma E4B |
|---|---:|---:|---:|
| language | **100.0%** | **100.0%** | **100.0%** |
| case | 82.9% | 61.5% | 48.5% |
| structure | 49.6% | 56.8% | 42.0% |
| length_paragraphs | 12.5% | 12.1% | 16.3% |
| **length_words** | **7.5%** | 12.5% | 12.4% |
| self-consistency | 0.468 | 0.376 | 0.436 |

**The ordering is identical across two families and two scales**, and it tracks
one thing: *does honouring the convention require counting while generating?*

- **language** — fixed at token 1, never revisited → perfect, everywhere.
- **case** — local, per-token, no memory needed → 49–83%.
- **structure** — needs a plan, countable in chunks → 42–57%.
- **length** — requires tracking a running count against a target → **7–16%**,
  catastrophic on every model.

This is the count→gap→extend loop the taxonomy identified, now isolated: the
failure is not comprehension, family, or scale. It is that no model can hold a
count while generating.

**It also refines 0017.** E4B's *median* length error is −1% (well-centred) yet its
in-window accuracy is only 12.4% — E4B is **unbiased but imprecise**, while Qwen
(median −26%, 7.5%) is **biased and imprecise**. Reporting either statistic alone
misleads; the distribution is wide for both.

## 2. E0.2 binding: what the model fails to register

Binding = did the declaration capture the constraints the prompt stated? Scored
against adapter ground truth.

| model | binding recall | extra slots/resp |
|---|---:|---:|
| Qwen3.5-2B | **0.485** | 3.90 |
| Gemma E2B | **0.540** | 3.61 |
| Gemma E4B | **0.559** | 3.94 |

**About half of stated constraints never reach the declaration.** This is the
taxonomy's "never registered" failure, quantified for the first time — and it is
the failure mode a binding reward (`R_bind`) exists to fix.

The "extra slots" figure is **not** an error rate: those are `[assumed]`
conventions the model volunteers on dimensions the prompt left open, which is
the entire point of the project. Precision as conventionally computed (0.16–0.20)
is therefore meaningless here and should not be quoted.

### Per-family recall — a very sharp split

| constraint family | Qwen | E2B | E4B |
|---|---:|---:|---:|
| length_constraints:number_words | 100% | 100% | 98% |
| change_case:english_lowercase | 100% | 100% | 97% |
| length_constraints:number_sentences | 48% | 88% | 86% |
| startend:quotation | 34% | 97% | 78% |
| punctuation:no_comma | 77% | 73% | 52% |
| keywords:frequency | 12% | 59% | 62% |
| keywords:existence | 15% | 24% | 32% |
| keywords:forbidden_words | 3% | 25% | 22% |
| number_highlighted_sections | 6% | 3% | 3% |
| **combination:repeat_prompt** | **0%** | **0%** | **0%** |

Three tiers:

1. **Always registered** — word count, lowercase. These are the dimensions models
   already think about by default, so a stated constraint lands on an existing slot.
2. **Sometimes registered** — sentence count, quoting, no-comma. Highly
   model-dependent (quotation: 34% Qwen vs 97% E2B).
3. **Almost never registered** — keyword requirements, highlight counts, and
   `repeat_prompt` at **0.0% on all three models**.

Most-missed slots agree: `must_include` (57–77 misses), `markup`, `forbidden`,
`wrappers`, `response_boundary`.

**The pattern:** constraints that map onto a *default-bearing dimension* get
registered; constraints that introduce a dimension the model has no prior about
(specific keywords, highlight counts, verbatim repetition) get dropped. That is
the same default-inventory logic as [0009](0009-correction-schema-is-a-default-inventory.md),
now visible in binding rather than in schema coverage.

## 3. What this means for C2

C2 claims binding and execution fail independently and should be rewarded
separately. The data supports that directly:

- **Binding fails on keyword/markup/repeat families** (0–32% recall) while
  execution on those is untested because they were never declared.
- **Execution fails on length** (7–16%) while binding on length is *perfect*
  (98–100%). The model registers the length constraint flawlessly and then misses it.

Length is the cleanest existence proof for the factorization: **100% binding,
~10% execution.** A single monolithic reward cannot distinguish those; two can.

## Open items

- E0.4 remains blocked: the E0.2 runner records binding but does not score the
  answer, so P(pass | bind✓) cannot be computed. This is now the smallest
  remaining gap in Phase 0.
- Re-run E0.3/E0.2 headline numbers with the fixed extractor (the tables above are
  recomputed, but the stored `*.json` summaries still hold pre-fix values).
- `repeat_prompt` at 0% across all models deserves its own look — it may be a
  slot-mapping artefact (`response_boundary`) rather than a genuine binding failure.
