# 0001 — Model and compute plan

**Date:** 2026-07-21

## Context

The experiment design (`verbalized-defaults-experiments.md` §1) specifies Gemma 4
E4B-it as the primary training subject, full-parameter fine-tuning for headline
configs, a Qwen3.6-4B cross-family replication, and a 27B scale point. That table
was written assuming cluster-scale compute. The actual available hardware is two
LAN boxes, which changes what is trainable.

## Available compute

| Host | Address | Hardware | Characteristics |
|---|---|---|---|
| `turing` | 192.168.1.220 | RTX 5090, 32 GB GDDR7 | fast compute + bandwidth, small VRAM |
| `spark` | 192.168.1.253 | DGX Spark, 128 GB unified | large capacity, low memory bandwidth |

Division of labour: **turing = trainer** (and fast probe inference);
**spark = judge / teacher / rollout + best-of-n generation server** (its 128 GB
comfortably holds the NVFP4 judge; its low bandwidth makes it a poor trainer).

## Decision: primary subject is Qwen3.5-2B

Model roles, revised from the experiment design:

| Role | Model | Notes |
|---|---|---|
| **Primary training subject** | `Qwen/Qwen3.5-2B` | instruct (base exists separately as `-Base`), thinking + non-thinking modes, 262k context |
| Judge / teacher | `unsloth/Qwen3.6-35B-A3B-NVFP4` | inference-only on spark; NVFP4 is appropriate here |
| Reference / oracle ceiling | `unsloth/gemma-4-E4B-it-NVFP4` | **inference only** — NVFP4 cannot be fine-tuned through |

Selection path: Qwen3-1.7B was considered first (purely a compute-fit choice),
then replaced by Qwen3.5-2B — newer generation, larger context, marginally more
capacity (a slightly higher execution ceiling, which matters because the taxonomy
says small-model failures are execution-side), while keeping the property that
actually drives the design: a **separate reasoning channel**.

Full fine-tuning of a 2B model fits the 5090 (~20 GB with 8-bit Adam + gradient
checkpointing), so full FT is available for headline configs, not just LoRA.
GRPO is tighter — plan is LoRA-GRPO on turing with rollouts served from spark.

## Consequences (accepted, not worked around)

1. **The Gemma 4 E4B failure taxonomy does not transfer.** The entire
   `failure-taxonomy-reports/` grounding — genre length priors, poem
   auto-capitalisation, the P.S. recasing failure, the 0.53 IFBench collapse — is
   an *E4B measurement*. Phase 0 must be re-run on Qwen3.5-2B to establish its
   own defaults and failure taxonomy before any data is mined. Phase 0 is
   inference-only and cheap, so this is a one-time cost, not a blocker.
2. **No scale point, no trained cross-family replication.** Scale-invariance
   cannot be claimed. The work becomes explicitly a **small-model (~2B) study**,
   and the experiment design's "does the interface work below 4B?" probe is
   **promoted from a side probe to the headline question**. This is a scope
   statement, not a hedge: small models are where instruction-following is worst
   and where the technique is most needed.
3. **Cross-model checking is inference-only.** E4B can still be used for
   oracle-prefill probes as a cheap sanity comparison, but not full replication.

## Upside

Qwen's separate reasoning channel removes the confound that the experiment design
lists as Risk 7 — Gemma's inline-thinking-in-`content` artifact, where reasoning
prose pollutes the scored output. The `response_boundary` slot exists largely to
patch that; on this model it becomes a cleaner, less load-bearing slot.

## Open items

- Confirm on the model card whether Qwen3.5-2B is genuinely a vision-language
  model. If so: prefer a text-only variant if one exists, otherwise freeze/skip
  the vision tower so it is not dead weight in VRAM or the optimizer, and check
  whether the advertised 2B *includes* the vision encoder.
- Deploy-quant target is undecided: the experiment design names `w4a16`, but the
  available artifacts are NVFP4. Pick one before the QAT survival check.
- **Measure defaults at training precision.** Phase 0 feeds `defaults.json`,
  which fills the `[assumed]` slots in SFT data. Measuring defaults on an NVFP4
  checkpoint and then training bf16 risks a precision mismatch in the measured
  priors. Measure on the precision we train on.
