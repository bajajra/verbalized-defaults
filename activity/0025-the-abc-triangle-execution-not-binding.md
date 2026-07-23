# 0025 — The A/B/C triangle: the fight is lost at execution, not at declaration

**Date:** 2026-07-23
**Source:** E0.4 runs (`e04-*`, 300 IFEval prompts × 3 samples), the model's OWN
declarations — not an injected oracle spec.

Prompted by the observation that the contradiction test (0024) injects an
artificial spec, whereas E0.4 has the model verbalise its own value. For every
**case** constraint the prompt stated, three things: what was asked (**A**), what
the model declared in reasoning (**B**), what it produced (**C**).

## Case triangle — instruction A / declared B / output C

| outcome | Qwen | E2B | E4B |
|---|---:|---:|---:|
| **A=B=C** (declared right, obeyed) | **6%** | 59% | **62%** |
| **A=B, C≠A** (declared right, EXECUTION failed) | 48% | 25% | **29%** |
| **A≠B** (BINDING failed: declared ≠ asked) | 45% | 15% | 9% |

Read the middle row. On both Gemmas the **single largest failure mode is
"declared the right thing, then did the wrong thing"** — the model wrote
`case: lower` in its reasoning and produced mixed-case output anyway (E4B 29%,
E2B 25%). Binding failure (declaring something other than what was asked) is half
that or less (9%, 15%).

**This is direct evidence against the project's framing.** The thesis is "an
explicit instruction loses a silent fight against a latent default." The triangle
says: on the capable models the instruction *wins* the declaration (B=A ~90% of
the time) — the default does **not** capture the verbalisation. The response then
fails at **execution**. The model knows what it should do, says so, and cannot do
it.

## Length triangle — same shape

Does the declared length satisfy A, and does the output?

| | Qwen | E2B | E4B |
|---|---:|---:|---:|
| declared-Y, output-Y (obeyed) | 61% | 74% | 67% |
| declared-Y, output-N (**execution failed**) | — | 21% | 17% |
| declared-N, output-Y (bind slip, saved by output) | — | 5% | 15% |

Again: when the model declares a satisfying target, it still misses it ~20% of the
time (execution), and binding is rarely the problem.

## The weakest model is different — and it is the only one that fits the thesis

Qwen is the exception. It aligns only **6%** of the time, and its failures split
roughly evenly between execution (48%) and **binding (45%)**. Crucially, Qwen
frequently declares `standard` — its *default* — when asked for lower or upper
(32% of case items): here the latent default really does win the verbalisation.
So the "silent fight against a latent default" pattern is real, but it is
concentrated in the **weakest** model, and even there declaring correctly does not
rescue execution.

Caveat: Qwen's case output is almost always `mixed`, which may be a capability
floor (it struggles to produce clean single-case text at all), so its numbers
mix "the default won" with "it cannot execute case".

## What this means

**The dominant, cross-model failure is execution, not binding.** The model usually
verbalises the correct value and then fails to produce it. This is the strongest
version yet of the recurring Phase-0 signal:

- surfacing/binding is *not* where the capable models fail — they declare correctly;
- the leverage is the **execution** step, the count→gap→extend / hold-the-constraint loop.

It sharpens the caution on the thesis: **verbalising a default cannot fix a
failure that is downstream of verbalisation.** On E2B/E4B the model already says
the right thing. A method whose whole mechanism is "make the model say the right
thing" has little left to add there; its value would have to come from the
execution-side reward (`R_exec`), not from binding.

Where the thesis's mechanism *does* appear — the default capturing the
declaration — is the weakest model (Qwen), which is also where execution is most
broken, so surfacing alone still would not carry it.

## Corrects 0024

0024 said the contradiction resolved by "authority" (system rule beats spec) on
the Gemmas. That was wrong. Adding a contradicting spec **halves** system=UPPER
compliance (E2B 0.94→0.49, E4B 0.99→0.56) but does nothing to system=lower
(−0.01) — an asymmetry authority cannot explain. It is a **directional bias
toward lowercase** (the lower-effort form): the system loses control precisely
when it demands the hard direction and the spec offers the easy one. All three
models are on the same execution-difficulty axis; the Gemmas merely sustain
upper better when uncontested.
