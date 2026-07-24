# 0011 — IFEval scoring harness and the first E0.1 pilot

> **PARTIALLY SUPERSEDED.** The n=60 pilot numbers and the "Qwen avoids inline pollution" reading are superseded by [0014]. The four methodology traps it documents stand.

**Date:** 2026-07-21
**Result:** 60/60 tests passing. First interpretable E0.1 run: **oracle spec
prefill does not help this model — it is neutral to harmful.** The run is
underpowered (n=60, single sample), so this is a *signal*, not a Gate 1 verdict.
Four methodological traps were found and fixed along the way; three of them had
already corrupted earlier runs.

## The scoring harness

`verbalized_defaults.ifeval_score` delegates to IFEval's **own**
`instructions_registry` rather than reusing our verifier suite. Our verifiers
exist to train against; the reported benchmark numbers must be the benchmark's,
or a verifier bug becomes a headline result. (Our suite is separately *pinned* to
IFEval's metrics by the parity harness — that is a cross-check, not a substitute.)

Implements prompt-level and instruction-level strict/loose, with IFEval's eight
loose variants reproduced exactly. Seven tests guard it, including the ones that
matter most: it must discriminate compliant from non-compliant, an empty
response must never pass, and **loose can never be stricter than strict**.

## E0.1 design

Oracle specs come from `ifeval_adapter` (benchmark metadata, never a model), are
rendered by `format_spec`, and are placed in the *prompt*, so they never appear
in the generated text and nothing has to be stripped before scoring.

| condition | construction |
|---|---|
| `vanilla` | no-think template, no spec — the baseline |
| `spec_think` (a) | spec inside a reasoning block **we close ourselves** |
| `spec_prefix` (b) | spec as a visible response header, no-think |
| `vanilla_think_open` | diagnostic only, excluded from the comparison |

## Four methodological traps (all found by looking at raw output)

**1. Greedy decoding is invalid for this model.** At `temperature=0.0`,
generations fall into verbatim repetition loops — one truncated sample repeated
*"And make my journey seem a little more."* until it exhausted the budget. This
inflated truncation *asymmetrically* (spec conditions 20–22%, vanilla 5%) and
made the spec conditions look far worse than they are. Qwen documents sampling as
required; the runner now defaults to `temperature=0.7, top_p=0.95`.

**2. The model does not close `<think>` when the block is left open.** Given an
open reasoning block via raw completions, it writes its reasoning as *plain
prose* ("Thinking Process: 1. Analyze the Request…") and never emits `</think>`
— 48/60 unclosed. The reasoning then pollutes the scored answer and fails
constraints like "no commas" on the reasoning text rather than the answer.
**This corrects a claim in [0001](0001-model-and-compute-plan.md) and
[0010](0010-prior-inventory-and-server.md):** Qwen's separate reasoning channel
avoids inline-thinking pollution *only via the chat API*. Prefilling through raw
completions reintroduces exactly the Gemma artifact the model was chosen to
avoid. Fix: close the block ourselves, so the spec sits in reasoning and the
model emits only the answer.

**3. Truncation is a validity gate, not a footnote.** A condition that runs out
of budget mid-generation scores near zero for reasons unrelated to instruction
following. Unbalanced truncation across conditions invalidates the comparison
outright. The runner now reports per-condition truncation and refuses to let a
lift be read as a Gate 1 result when any non-diagnostic condition exceeds 10%.
Raising `max_tokens` 1024→4096 did *not* fix it — that was trap 1 in disguise.

**4. `cond.endswith("think")` also matches `vanilla_nothink`**, so the
unclosed-block counter reported 40/40 failures for a condition that legitimately
has no `</think>` in its output. Cosmetic, but it made trap 2 much harder to see.

## First interpretable result

n=60 IFEval rows, temp 0.7, top_p 0.95, single sample, max_tokens 4096.
Truncation 1.7% / 6.7% / 6.7% — validity gate passes.

| condition | prompt-strict | prompt-loose | inst-strict | trunc |
|---|---:|---:|---:|---:|
| vanilla | **0.6667** | **0.6833** | 0.7634 | 1 |
| spec_think (a) | 0.6167 | 0.6667 | 0.7204 | 4 |
| spec_prefix (b) | 0.5333 | 0.5333 | 0.6237 | 4 |
| vanilla_think_open | 0.2833 | 0.2833 | 0.4409 | 49 |

**Oracle-prefill lift:**

- (a) `spec_think` − vanilla: **−0.050 strict, −0.017 loose**
- (b) `spec_prefix` − vanilla: **−0.133 strict, −0.150 loose**

## How much to read into this

**Not a Gate 1 verdict.** At n=60 with p≈0.67 the binomial standard error is
≈0.06, so (a)'s −0.05 is well within one standard error of zero — indistinguishable
from no effect. Only (b) is plausibly a real decrement. A verdict needs the full
541 rows and the design's temp-0.7 ×5 with paired bootstrap CIs.

What *is* reasonably solid: **prefilling a perfect spec is not producing the
large positive lift H0 predicts.** The design anticipated this outcome and has a
pivot for it — Gate 1 failure re-centers the work on execution training and makes
the C2 binding/execution diagnostic the headline. Worth noting the taxonomy's own
prediction was that failures are "never checked" rather than "can't do", and a
null here would point the other way for this model.

Two candidate explanations to separate before concluding anything:

1. **The spec format may be wrong for a 2B model.** `length_words: >=300 [given]`
   is machine syntax. A small model may parse it poorly or be distracted by it.
   Mode (b) putting it in the visible response is *more* harmful than mode (a)
   hiding it in reasoning, which is consistent with "the spec text itself is a
   distraction."
2. **The ceiling may already be high.** Vanilla is 0.667 strict on these rows;
   the remaining failures may be execution-side, exactly where a spec cannot help.

## Status

- Gemma 4 E4B (NVFP4) weights downloaded — the HF **Xet/CAS backend errored**;
  `HF_HUB_DISABLE_XET=1` fixed it. Server relaunching; the validation probe has
  not run yet.
- E0.1 has run only on 60/541 rows, single sample.

## Open items

- **Full E0.1**: all 541 rows × 5 samples at temp 0.7, paired bootstrap → the
  actual Gate 1 reading.
- **Ablate the spec format** — a terse natural-language spec vs the typed block —
  to separate "surfacing does not help" from "this notation does not help".
- Run the Gemma prior-inventory validation (instrument check vs the taxonomy).
- `vanilla_think_open` is a real finding about the model worth reporting: native
  thinking mode via raw completions is unusable, 81.7% truncation.
