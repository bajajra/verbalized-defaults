# 0012 — E0.1: surfacing works, the typed notation is what fails

**Date:** 2026-07-21
**Result (n=100, temp 1.0, Qwen3.5-2B):** a **plain-English** spec in the
reasoning channel lifts prompt-strict **+0.11**, clearing the Gate 1 threshold.
The **typed `<spec>` DSL captures almost none of it** (+0.00 to +0.04). This
reverses [0011](0011-ifeval-scoring-and-e01-pilot.md)'s reading and is a direct
challenge to C1's representational choice.

## What changed since 0011

0011 ran a single arm — typed spec, no system prompt — and read its null result
as evidence against H0. Two confounds were identified: the model had never seen
the notation, and was never told to follow it. This entry runs the factorial that
separates them.

| axis | levels |
|---|---|
| notation | typed `<spec>` DSL / plain-English requirement list |
| placement | inside a closed reasoning block / visible response header |
| hint | system prompt explaining the block / none |

## Results

n=100 IFEval rows, temp 1.0, top_p 0.95, max_tokens 4096. Truncation ≤7% for all
non-diagnostic conditions and looping ≤7% — validity gate passes.

| condition | strict | loose | inst-strict | Δstrict vs vanilla |
|---|---:|---:|---:|---:|
| vanilla | 0.5800 | 0.6300 | 0.6994 | — |
| typed_think | 0.5800 | 0.6000 | 0.6810 | +0.000 |
| typed_think_sys | 0.6200 | 0.6300 | 0.7485 | +0.040 |
| typed_prefix_sys | 0.5500 | 0.5600 | 0.6319 | −0.030 |
| **nl_think** | 0.6800 | 0.7200 | 0.7730 | **+0.100** |
| **nl_think_sys** | **0.6900** | 0.6900 | **0.7853** | **+0.110** |
| nl_prefix_sys | 0.5100 | 0.5400 | 0.6258 | −0.070 |
| vanilla_think_open | 0.3400 | 0.3500 | 0.4908 | −0.240 |

## Three findings

**1. Surfacing works — H0's premise survives.** The best-case arm lifts
prompt-strict from 0.58 to 0.69 (+0.11) and instruction-strict from 0.699 to
0.785 (+0.086). Against the pre-registered Gate 1 rule (≥+0.05 proceed, <+0.02
falsify) this **passes**. Restating a prompt's constraints before generating
measurably improves compliance.

**2. The typed notation is where the benefit dies.** Same constraints, same
placement, same hint — only the rendering differs — and typed captures +0.04
against natural language's +0.11. **The DSL costs roughly two-thirds of the
available lift.** This is a direct problem for C1, whose contribution *is* the
typed multi-slot spec: on a 2B model the typing is not neutral packaging, it is
a substantial tax.

**3. It was the notation, not the missing hint.** The system prompt was the
suspected confound, but it is worth only +0.04 for typed and +0.01 for natural
language (nl_think +0.100 → nl_think_sys +0.110). Notation dominates hint by an
order of magnitude.

**Placement is a real and separate effect.** Both notations are *negative* as a
visible response header (−0.03 typed, −0.07 NL) and positive-or-neutral inside
the reasoning block. Surfacing helps only when the spec stays out of the answer.
This is consistent with the over-application failure seen in 0011's example,
where the model treated the spec as a style template to imitate.

## Statistical care

n=100 with p≈0.6 gives an unpaired SE of ≈0.049, so +0.11 is ≈2.2 SE. The
conditions are **paired** (identical prompts), so the correct test is McNemar or
a paired bootstrap, which is more powerful than that figure implies — but it has
**not been run**. Treat +0.11 as a strong signal, not a certified effect.
Remaining gaps: 100/541 rows, single sample per condition, no CIs.

## What this means for the proposal

The C1/C2 split is unaffected in principle, but C1's *specific* claim — that a
**typed** convention-spec is the right representation — now has direct evidence
against it at 2B scale. Options, in order of honesty:

1. Report it. "Typed notation underperforms natural language at 2B" is a real,
   publishable negative result about the interface, and it is exactly the kind of
   thing the pre-registered design says to report rather than bury.
2. Test whether typing pays off *after training*. The whole point of the typed
   spec is that it is machine-verifiable for `R_exec`; an untrained model paying a
   comprehension tax says little about a model trained to emit it. **This is the
   real open question** — the tax may vanish with SFT.
3. Consider a hybrid: natural-language spec for the model, typed spec derived from
   it for verification.

Option 2 is the one that matters, and it means this result does **not** kill C1 —
it says C1 cannot be justified on inference-time evidence alone.

## Open items

- Paired significance testing (McNemar / bootstrap CIs).
- Full 541 rows × 5 samples.
- Same matrix on Gemma 4 E4B — note Gemma has **no `<think>`/`</think>` tokens**,
  so the reasoning-block placement does not transfer; needs a system-prompt
  placement as the model-agnostic analogue.
- Over-application metric (how far past `>=N` outputs overshoot), per 0011.
