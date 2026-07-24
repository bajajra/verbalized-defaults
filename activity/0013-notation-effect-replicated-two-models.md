# 0013 — Correction to 0012, and the notation effect replicated on two models

> **PARTIALLY SUPERSEDED.** Its 5-sample effect sizes are superseded by the 541×4 run in [0014]. Its retraction of 0012 stands.

**Date:** 2026-07-21
**Status:** **retracts the headline number in [0012](0012-e01-notation-matters-more-than-surfacing.md)**
and replaces it with a properly powered result.

## The retraction

0012 reported "+0.11 prompt-strict, Gate 1 passes" from a single-sample n=100
run. **It does not replicate.** Re-running the identical configuration moved
every condition:

| condition | run 1 | run 2 | Δ |
|---|---:|---:|---:|
| vanilla | 0.580 | 0.650 | +0.070 |
| typed_think | 0.580 | 0.640 | +0.060 |
| nl_think | 0.680 | 0.630 | **−0.050** |
| nl_think_sys | 0.690 | 0.710 | +0.020 |

Run-to-run variance of 0.02–0.07 per condition, on identical inputs — and a
*lift* is a difference of two such quantities, so its noise is larger still. The
+0.11 was sampling noise. It was committed too quickly, on one run, with no
repeat and no CI.

**Process lesson:** a single-sample run is a smoke test, not a measurement. The
experiment design already mandated temp-0.7 ×5 with paired bootstrap CIs; that
requirement is not optional bookkeeping, it is what separates a result from an
artifact.

## Corrected methodology

- **5 samples per (prompt, condition)** with distinct seeds → each cell is a pass
  *rate* in [0,1], not a coin flip.
- **Paired on the prompt** — conditions see identical prompts, so the paired
  delta cancels per-prompt difficulty.
- **Bootstrap CI over prompts** (10k resamples). A CI spanning 0 is not a finding.
- Validity gates: truncation 0% and looping ≤1% on both models at temp 1.0.

## Result 1 — spec vs no spec: INCONCLUSIVE

Paired Δ prompt-strict against `vanilla`, 100 prompts × 5 samples:

| model | condition | strict | Δ vs vanilla | 95% CI | sig |
|---|---|---:|---:|---|---|
| Qwen3.5-2B | nl_insys | 0.652 | +0.048 | [−0.014, +0.112] | no |
| Qwen3.5-2B | typed_insys | 0.606 | +0.002 | [−0.054, +0.058] | no |
| Gemma 4 E4B | nl_insys | 0.884 | +0.050 | [−0.000, +0.104] | no |
| Gemma 4 E4B | typed_insys | 0.786 | −0.048 | [−0.110, +0.014] | no |

Natural-language surfacing trends **+0.05 on both models**, but neither CI
excludes zero. **Gate 1 is unresolved**, not passed and not failed. Resolving a
+0.05 effect needs roughly 4× the data — the full 541 rows × 5 samples, which
would narrow the CI to about ±0.026.

## Result 2 — notation: SIGNIFICANT, and it replicates

The within-subjects test: same placement, same constraints, same system prompt —
**only the rendering differs**.

| model | NL − typed | 95% CI | sig |
|---|---:|---|---|
| **Gemma 4 E4B** | **+0.098** | [+0.048, +0.152] | **yes** |
| **Qwen3.5-2B** | **+0.046** | [+0.002, +0.092] | **yes** |

Both CIs exclude zero, same sign, on two different model families at two
different scales. **Rendering identical constraints as a typed `<spec>` block
instead of plain English costs 5–10 points of prompt-strict accuracy.**

On Gemma the typed spec is *worse than giving no spec at all* (0.786 vs 0.834),
i.e. handing the model a perfect, complete, machine-readable statement of every
constraint made it follow those constraints **less** well than saying nothing.

## What this does and does not mean for C1

C1's contribution is the *typed* multi-slot spec. This is direct evidence that,
**at inference time on untrained models**, the typing is not neutral packaging —
it is a measurable tax, and the larger model pays more of it.

It does **not** kill C1, for one specific reason: the typed spec exists to be
machine-verifiable for `R_exec`. A model that has never seen the format paying a
comprehension cost says little about a model *trained* to emit it. The honest
statement is that **C1 cannot be justified on inference-time evidence — it has to
earn its place in Phase 1**, and the SFT ablation now has a concrete number to
beat: typed must recover ≥0.098 (Gemma) relative to natural language, or the
typing is a net loss.

A hybrid also becomes attractive: natural-language spec for the model to read,
typed spec derived from it for the verifier. That keeps `R_exec` mechanical
without making the model parse a DSL.

## Incidental: partial instrument validation on Gemma

Gemma 4 E4B vanilla scores **0.860 prompt-loose** on this 100-row subset. The
failure taxonomy reports ~0.90 for E4B on full IFEval. Same ballpark, with the
gap plausibly explained by the NVFP4 quantization and the subset — so the harness
is measuring roughly what earlier hand analysis measured. Not a rigorous
validation (different subset, different precision), but reassuring.

Gemma is also far stronger than Qwen here (0.834 vs 0.604 vanilla strict), which
is expected at 4B vs 2B and consistent with IFEval-shaped familiarity.

## Open items

- **Full 541 × 5 on both models** — the only thing that resolves Gate 1.
- Gemma has no `<think>`/`</think>`, so the reasoning-block placement is
  Qwen-only; `*_insys` (spec in the system prompt) is the cross-model condition
  and is what these numbers use.
- Over-application metric (how far past `>=N` outputs overshoot).
- The Gemma *prior inventory* still has not been run — this entry is E0.1 only.
