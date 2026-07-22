# 0015 — E0.3: the model declares its defaults, then violates half of them

**Date:** 2026-07-21
**Model:** Qwen3.5-2B, 60 unconstrained genre prompts × 2 samples (n=120), temp 1.0.
**Result:** the model declares **4.5 conventions per response** and satisfies only
**47%** of them. **1 response in 120** fully honoured its own declaration.

This is the **first `[assumed]` measurement in the project** — everything prior
concerned restating explicit constraints.

## Why this matters

The experiment design gates the RLVR work on exactly this number: *"self-consistency
per slot. Gap = headroom for C3's reward. If already >95% consistent, C3's signal
is thin — check before building RLVR."*

Measured: **47.1%**, median 0.5, and a perfect-compliance rate of **0.8%**.
That is not a thin signal — it is a very large trainable gap, and it exists on
dimensions **nobody asked about**, which is precisely the claim the project rests
on. Green light for the assumed-slot reward.

## Design: two controlled phases

Letting the model open a reasoning block and close it does not work — Qwen writes
"Thinking Process: …" as prose and never emits `</think>`, which produced a
spurious 83% no-declaration rate in the first attempt. Instead:

1. **Phase 1** — prompt ends with `<conventions>`; generation stops at
   `</conventions>`. The declaration is bounded by a delimiter *we* control.
2. **Phase 2** — the model's own declaration is fed back, the reasoning block is
   closed, and it writes the answer.

Deterministic, identical across both model families, and it mirrors what a
trained model would do: emit the spec, then honour it.

## The cue matters enormously (a finding in itself)

A soft cue — *"think about the conventions your response will follow"* — produced
**qualitative style guidance only**:

> "Be clear and direct." · "No bold text or markdown." · "Write in the third
> person." · "Keep sentences relatively short." · "Maintain an objective yet
> engaging tone."

Those *are* genuine verbalized defaults, but they carry no value a verifier can
check: extraction coverage **2%**, 0.17 slots per response. Asking instead for
**specific values** produced usable declarations:

> Approximate Word Count: ~650 words · Paragraph Count: 3-4 paragraphs ·
> Bullet Points: 0 · Capitalization: Standard · Language: English

| metric | soft cue | concrete cue |
|---|---:|---:|
| no-declaration rate | 0.83 | **0.00** |
| slots declared | 0.17 | **4.51** |
| extraction coverage | 0.02 | **0.67** |

**The model's natural convention vocabulary is stylistic, not metric.** It will
not volunteer quantified, checkable defaults unless asked for them explicitly.
That gap is itself a thing training would have to close.

## The violation profile matches the taxonomy

| declared slot | violated | rate |
|---|---:|---:|
| length_words | 113/120 | **94.2%** |
| length_paragraphs | 103/120 | **85.8%** |
| structure | 45/120 | 37.5% |
| case | 22/120 | 18.3% |
| wrappers | 2/120 | 1.7% |

The ordering is an **execution-difficulty ordering**: dimensions requiring a
*global count* fail almost always, dimensions requiring *local consistency* fail
rarely. The model can commit to "about 650 words" and then miss it 94% of the
time — exactly the taxonomy's A1 finding ("systematic underproduction; no
count→gap→extend loop"), reproduced here against the model's *own* target rather
than an externally imposed one.

That is a sharper version of the A1 result than the taxonomy could get: the
failure cannot be blamed on misreading the instruction, because the model wrote
the instruction itself one turn earlier.

## Caveats

- **Extraction fidelity bounds this.** Coverage is 0.67, so a third of declared
  lines are not typed and go unmeasured. Extraction errors would show up as false
  violations.
- **Hedged figures are read as ±10% windows**, not point values. An earlier
  version parsed "~650 words" as *exactly* 650, which would have deflated
  self-consistency into an artefact of our own parser. ±10% is the tolerance the
  schema's own anti-gaming rule allows for an assumed length. A looser tolerance
  would raise the length numbers.
- Single model, n=120, one temperature.
- **The magnitude of the length miss is not yet measured** — only pass/fail. How
  far off is "about 650 words" in practice? That distribution is more informative
  than the violation rate and is cheap to compute from the stored data.

## Open items

- Run E0.3 on Gemma 4 E4B and E2B for the size/family comparison.
- Measure length-miss magnitude, not just violation rate.
- **E0.2 binding** (`--source ifeval`) has not been run yet; the harness supports it.
- Raise extraction coverage above 0.67, or report the uncovered third explicitly
  as unmeasured rather than as satisfied.
