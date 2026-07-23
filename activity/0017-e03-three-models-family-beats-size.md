# 0017 — E0.3 across three models: self-consistency holds, and length is a *family* effect

**Date:** 2026-07-22
**Models:** Qwen3.5-2B, Gemma 4 E2B (NVFP4), Gemma 4 E4B (NVFP4).
60 genre prompts × 2 samples per cue per model, temp 1.0.

E2B is the control that separates **size** from **family**: same parameter class
as Qwen-2B, same family as E4B.

## Concrete cue (the reliable measurement)

| model | no-decl | slots | coverage | **self-cons** | perfect | **len median** | under |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-2B | 0.00 | 4.47 | 0.66 | **0.495** | 0.008 | **−26%** | 0.74 |
| Gemma E2B | 0.00 | 3.62 | 0.43 | **0.425** | 0.008 | **−5%** | 0.60 |
| Gemma E4B | 0.11 | 3.13 | 0.41 | **0.460** | 0.065 | **−1%** | 0.54 |

## Finding 1 — self-consistency ~0.45 is robust across three models

**0.495 / 0.425 / 0.460.** Two families, three models, two parameter classes, all
landing near one another. The model obeying only about **half of its own freely
declared conventions** is now an established result, not a single-model quirk.

The design gates the RLVR work here (">95% would mean the signal is thin"). At
~0.45 across every model tested, the headroom for an assumed-slot reward is real
and general. **This is the strongest support the project has for its central
premise**, and it holds on dimensions nobody asked about.

Perfect-compliance is near zero everywhere (0.8% / 0.8% / 6.5%) — essentially no
response fully honours its own declaration.

## Finding 2 — length underproduction is a FAMILY effect, not a size effect

This resolves the question left open in [0014](0014-e01-full-benchmark-both-models.md),
where model-dependence was confounded.

| comparison | holds constant | varies | Δ median length error |
|---|---|---|---|
| Qwen-2B vs **Gemma E2B** | **size (~2B)** | family | **−26% → −5%** |
| Gemma E2B vs **Gemma E4B** | **family** | size | −5% → −1% |

**Family dominates.** At the *same parameter class*, Gemma misses its self-declared
length by 5% where Qwen misses by 26% — a 5× difference attributable to family
alone. Scaling within Gemma buys a further modest improvement (−5% → −1%).

So the earlier reading — "a capability floor; 2B cannot hit a self-set length" —
was **wrong**. A 2B model can hit it; *Qwen's* 2B cannot. The retraction in
[0016](0016-quantitative-magnitude-and-qualitative-inventory.md) stands and is
now explained rather than merely observed.

## Finding 3 — the soft cue is a Qwen phenomenon

| model | no-declaration (soft) | qualitative lines/response |
|---|---:|---:|
| Qwen3.5-2B | 0.34 | **11.6** |
| Gemma E2B | 0.71 | 5.8 |
| Gemma E4B | 0.80 | 4.4 |

Both Gemmas mostly **decline to declare anything** under the soft cue. The entire
qualitative theme inventory in 0016 — clarity 19.5%, tone 14.1%, the
content-policy discovery — therefore rests on Qwen output and **should not be
generalised**. It describes one model's convention vocabulary, not models'.

## A caveat about our own instrument

Extraction coverage is **0.66 (Qwen) vs 0.43 / 0.41 (Gemma)**. The extractor's
regexes were developed by reading *Qwen* declarations, so some of that gap is
plausibly **our bias, not Gemma's vagueness**. Coverage should not be quoted as a
property of a model until the extractor has been tuned symmetrically — or, better,
until an LLM extractor is benchmarked against it on both families.

## Process failure worth recording

E2B's server never started for ~12 hours while being reported as "still loading".
Two compounding mistakes:

1. `pkill -f "vllm serve"` issued over SSH **matched its own command string** and
   killed the shell before it relaunched anything — the same self-match bug hit
   earlier with `pgrep`.
2. The status check used `pgrep -f "vllm serve"`, which matched the *still-running
   Qwen and E4B* servers, so "a vLLM is running" was misread as "E2B is loading".

Fixes applied: kill by **PID**, and check for a **port-specific** pattern
(`pgrep -f "port 8002"`) plus log freshness rather than existence of any server.
**A liveness check must identify the specific process, not the class.**

## Open items

- E0.2 binding data now exists for all three models but is **unanalysed**.
- Re-tune the extractor against Gemma declarations to remove the instrument bias.
- E0.4 still blocked: the E0.2 runner records binding but does not score the
  answer, so P(pass | bind✓) cannot be computed yet.
