# 0022 — E4.1: the first direct test of the core mechanism, and it is weak

**Date:** 2026-07-23
**Runs:** `e41-qwen`, `e41-e2b`, `e41-e4b` — 80 collision prompts × 3 conditions ×
4 samples × 3 models = **7,680 generations**, integrity-verified.

## What this tested

Every prior experiment measured restating explicit constraints (E0.1) or
self-consistency when nothing is asked (E0.3). E4.1 is the first battery built to
make a **latent default collide with an explicit instruction** — the "silent
fight" the entire project is premised on. Five priors from the taxonomy, each a
prompt whose explicit instruction a known prior resists:

    poem_lowercase / proper_noun_lowercase / ps_recase   (A2 case)
    global_bullets                                       (A3 structure)
    length_2x                                            (A1 length)

Three conditions: **vanilla** (instruction alone), **oracle_declare** (constraint
surfaced into reasoning), **self_declare** (model states its own conventions
first). The thesis predicts declaring the default helps override it.

## Override rate (fraction satisfying the explicit instruction)

| prior | model | vanilla | oracle_declare | self_declare |
|---|---|---:|---:|---:|
*(vanilla / oracle_declare, per model Qwen/E2B/E4B; ps_recase row uses the audited checker, 0023)*

| poem_lowercase | Qwen/E2B/E4B | 0.98 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | — |
| length_2x | | 1.00 / 0.97 / 0.99 | 1.00 / 1.00 / 1.00 | — |
| proper_noun_lowercase | | 0.90 / 0.85 / 1.00 | 0.78 / 0.90 / 0.93 | — |
| ps_recase | | 0.93 / 0.98 / 1.00 | 0.98 / 0.98 / 0.98 | — |
| global_bullets | | **0.27** / 0.83 / 0.88 | 0.28 / 0.95 / 0.92 | — |

## Finding 1 — the taxonomy's priors mostly do not reproduce as collisions

Four of five priors sit near ceiling in vanilla on all three models (0.85–1.00).
When an explicit instruction is present, these models simply obey it — the poem
does come out lowercase, the 2× length target is met, the proper nouns are
lowercased. **The "silent fight" is faint here.**

The taxonomy was built by *mining E4B failures*, which selects for the tail.
A tail is real but small; constructing explicit collisions and finding the models
mostly comply is consistent with "the priors exist but are rarer than
failure-mining's emphasis implies."

## Finding 2 — the one strong collision is not the collision we thought

Qwen's `global_bullets` at **0.27** looked like the A3 "global count applied
per-stanza" prior. It is not. The bullet-count distribution on failures:

| model | 0 bullets | 3 (correct) | 9 (per-stanza prior) |
|---|---:|---:|---:|
| Qwen | **39/60** | 16 | **2** |
| E2B | 2 | 50 | 0 |
| E4B | 4 | 53 | 0 |

Qwen fails by **omitting bullets entirely** (39/60), not by applying the count
per-stanza (2/60). Bullets in a poem are unnatural, so the weak model drops the
instruction — an omission failure, not a prior overriding a count. The taxonomy's
A3 mechanism does not reproduce.

## Finding 3 — surfacing the default does not reliably help (CORRECTED post-audit)

**Two of the three "significant" ps_recase effects in the first version of this
entry were artefacts of a checker blind spot** (0023): the postscript detector
matched only literal `"p.s"` and missed `ps:`/`ps.`/`postscript:`, and surfacing
changed which marker the model used. With the audited detector, ps_recase is at
ceiling on both Gemmas. The surviving significant effects:

| prior | model | condition | lift | 95% CI |
|---|---|---|---:|---|
| global_bullets | E4B | self_declare | **+0.100** | [+0.017, +0.183] |
| ps_recase | Qwen | self_declare | **−0.133** | [−0.200, −0.067] |

Surfacing helped significantly **once** (global_bullets/E4B self_declare) and
hurt significantly **once** (ps_recase/Qwen self_declare). **Every
`oracle_declare` condition is null**, and the previously-reported E2B "+0.20 help"
and E4B "−0.15 harm" are gone. On the one genuine weak-model collision
(global_bullets/Qwen 0.27) surfacing did **nothing** (+0.017, ns).

The picture is if anything *more* negative than the first version: the one clear
"surfacing helps override a prior" result did not survive audit.

## The honest verdict

**This is the sharpest negative result in the project so far, and it lands on the
central claim.** The thesis — "declaring a latent default lets an explicit
instruction beat it" — was tested directly at inference for the first time, and:

- the collisions the thesis is built on mostly do not manifest (ceiling vanilla),
- the one strong failure is a different mechanism (omission, not prior override),
- surfacing the default helped once and hurt once (both self_declare), never via
  oracle_declare, and was otherwise null (0023).

What this does **not** do: it does not falsify the *training* claim. The proposal's
H0 is about a model *trained* to declare-then-obey; E4.1 as I ran it is an
inference-time probe, and it is consistent with E0.1's finding that inference-time
surfacing is weak-to-harmful. The training test is Phase 2/4 and is untouched.

What it **does** do: it removes the inference-time support the thesis was counting
on, and it raises a prior question the design did not — **how common is the silent
fight actually?** If explicit instructions already win ~90% of the time on these
models, the ceiling on what any binding/surfacing method can add is low, and the
headroom is concentrated in *execution* (counting) rather than *prior override*.
That echoes every other Phase-0 result: the failures are length/paragraph/bullet
*counting*, not priors defeating instructions.

## Caveats — this cuts both ways

- **The battery may under-induce the priors.** Short prompts with a blunt explicit
  instruction may be too easy; the taxonomy found these priors in longer, less
  direct contexts. A stronger battery — validated to reproduce the priors in
  vanilla *before* testing surfacing — would be a fairer test, and is the correct
  next step before drawing a firm conclusion.
- Quantized Gemmas (NVFP4), a different Qwen than the taxonomy's E4B.
- Inference-time only; no training.

## Recommendation

Do **not** proceed to Phase 1 SFT on the assumption that prior-override is the
mechanism. Two cheaper things first:

1. **Strengthen the battery** until priors reproduce in vanilla (target vanilla
   ≤0.6), then re-test surfacing. If they cannot be made to reproduce, that itself
   is the finding: the premise is weaker than the proposal assumes.
2. **Re-centre on execution.** Every Phase-0 result points at counting failures
   (length, paragraphs, bullets), not prior override. The count→gap→extend loop is
   the intervention the data actually supports.
