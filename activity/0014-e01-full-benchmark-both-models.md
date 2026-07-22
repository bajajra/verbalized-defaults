# 0014 — E0.1 on the full benchmark, both models: the definitive run

**Date:** 2026-07-21
**Scale:** 541 IFEval prompts × 4 samples × 7 conditions × 2 models = **30,296
generations**. Both files verified: 15,148 rows each, zero duplicates, 2,164 per
condition. Paired bootstrap CIs over prompts.

Supersedes the underpowered pilots in
[0011](0011-ifeval-scoring-and-e01-pilot.md)–[0013](0013-notation-effect-replicated-two-models.md).

## Results

**Qwen 3.5-2B** (vanilla 0.656 strict)

| condition | strict | Δ vs vanilla | 95% CI | sig |
|---|---:|---:|---|---|
| nl_insys | 0.683 | +0.028 | [+0.001, +0.053] | yes |
| nl_think_sys | 0.677 | +0.021 | [−0.005, +0.046] | no |
| typed_insys | 0.629 | −0.026 | [−0.052, +0.000] | no |
| typed_think_sys | 0.614 | **−0.042** | [−0.068, −0.015] | yes |
| typed_prefix_sys | 0.552 | **−0.104** | [−0.133, −0.074] | yes |
| nl_prefix_sys | 0.497 | **−0.159** | [−0.190, −0.126] | yes |

**Gemma 4 E4B (NVFP4)** (vanilla 0.835 strict)

| condition | strict | Δ vs vanilla | 95% CI | sig |
|---|---:|---:|---|---|
| nl_insys | 0.898 | **+0.064** | [+0.043, +0.084] | yes |
| nl_think_sys | 0.890 | **+0.055** | [+0.034, +0.076] | yes |
| nl_prefix_sys | 0.885 | +0.050 | [+0.031, +0.070] | yes |
| typed_prefix_sys | 0.883 | +0.049 | [+0.028, +0.069] | yes |
| typed_think_sys | 0.852 | +0.017 | [−0.003, +0.037] | no |
| typed_insys | 0.799 | −0.036 | [−0.061, −0.011] | yes |

## Finding 1 — the notation effect replicates (robust)

Within the thinking placement, holding constraints, placement and hint fixed and
varying **only the rendering**:

| model | NL − typed | 95% CI | sig |
|---|---:|---|---|
| Qwen 3.5-2B | **+0.063** | [+0.038, +0.087] | yes |
| Gemma 4 E4B | **+0.038** | [+0.022, +0.054] | yes |

Two families, two scales, same sign, both CIs excluding zero at n=541×4.
**Rendering identical constraints as our typed `<spec>` DSL instead of plain
English costs 4–6 points of prompt-strict accuracy.** This is the one result that
survived every round of scrutiny in this session.

## Finding 2 — whether surfacing helps at all is MODEL-DEPENDENT

This is the surprise, and it does *not* replicate:

| | Qwen 3.5-2B | Gemma 4 E4B |
|---|---:|---:|
| best arm (nl_insys) | +0.028 | +0.064 |
| your design (nl_think_sys) | +0.021 (ns) | **+0.055** (sig) |
| Gate 1 verdict (≥+0.05 / <+0.02) | **fails** | **passes** |

On Gemma, plain-English surfacing in the reasoning channel clears the
pre-registered proceed threshold. On Qwen the same intervention is +0.021 —
sitting on the falsification line.

The plain reading is a **capability floor**: 2B cannot exploit a spec it is
handed, 4B can. But this is confounded — different families, different training,
different sizes, and Gemma is IFEval-familiar (0.835 vanilla vs 0.656). Size is
the obvious explanation but not an established one.

## Finding 3 — placement REVERSES between models

| placement | Qwen | Gemma |
|---|---:|---:|
| nl_prefix_sys | **−0.159** | **+0.050** |
| typed_prefix_sys | **−0.104** | **+0.049** |

A complete sign flip, both significant, and these are the largest effects in the
table. On Qwen, putting the spec in the visible response body is catastrophic —
consistent with the over-application failure recorded in 0011, where the model
imitated the spec's *form* rather than obeying it. On Gemma the same placement
*helps*, roughly as much as any other.

Any claim about where the spec should live is therefore model-specific, and the
proposal should stop treating placement as settled.

## What this means for the proposal

**The proposal's actual interface — a typed spec in the reasoning channel — does
not clear Gate 1 on either model.** It is +0.017 (ns) on Gemma and −0.042
(significantly *negative*) on Qwen. The idea underneath it (state the constraints
before generating) works on Gemma; the specific typed rendering does not carry it.

Three honest options, unchanged in substance from 0013 but now properly powered:

1. **Report the notation result.** "A typed convention-DSL underperforms plain
   English by 4–6 points at inference time, replicated across two model families"
   is a real finding about the interface.
2. **Test whether typing pays off after training** — the tax is measured on models
   that have never seen the format. C1's premise is that typing buys
   machine-verifiability for `R_exec`; that trade can only be evaluated in Phase 1.
   The bar is now concrete: typed must recover ≥+0.038 (Gemma) / ≥+0.063 (Qwen)
   merely to match plain English.
3. **Hybrid** — natural-language spec for the model, typed spec derived from it
   for the verifier. Keeps `R_exec` mechanical without making the model parse a DSL.

## Limits of this result — important

- **These specs are `[given]`-only.** 832 slots across 541 prompts, mean **1.54
  slots**, 56% of prompts get a single line. This measures *"does restating
  explicit constraints help"* — it does **not** test the `[assumed]` defaults
  mechanism, which is the actual contribution. **A Gate 1 verdict on H0 should not
  be drawn from this run.**
- IFEval rarely creates a genuine collision between a latent default and an
  explicit instruction, which is the mechanism the thesis is about. The
  prior-targeted battery (E4.1) is the appropriate test.
- Both models are untrained on the spec format.
- Gemma is NVFP4; Qwen is bf16.

## Process notes

- The first Gemma run produced a **corrupted file** (22,301 rows, malformed JSON):
  an earlier `pkill` did not actually kill the previous run, and two processes
  interleaved writes to the same path. Caught by an integrity check on row counts
  and duplicate keys — worth running on every generated dataset before analysis.
- Streaming writes were added after a buffered run risked losing hours of work.
- Prompt selection: the earlier 400-row subset was the **first 400 in file order**
  and was measurably skewed (`language` ~3× underrepresented, `startend` ~2×
  over). This run uses all 541, so the skew is gone.
