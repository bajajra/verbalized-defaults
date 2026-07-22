# 0016 — Length-miss magnitude, and an inventory of the qualitative defaults

**Date:** 2026-07-21
**Model:** Qwen3.5-2B, 60 genre prompts × 2 samples per cue (n=120 each), temp 1.0.

Two extensions to [0015](0015-e03-self-consistency-first-assumed-result.md):
quantify the length failure properly rather than as pass/fail, and stop
discarding the *qualitative* conventions the model volunteers.

## 1. Quantitative: how badly does it miss its own length target?

"94% violated" says nothing about whether the miss is 5% or 5×. Measuring the
relative error against the model's own declared target (range midpoint):

| statistic | value |
|---|---:|
| median relative error | **−26.0%** |
| mean absolute relative error | 51.4% |
| fraction under target | **74%** |
| p10 | −53.0% |
| p90 | +36.2% |

**Systematic underproduction, against a target the model set itself.** The
taxonomy found Gemma 4 E4B landing "10–15% short" of *externally imposed* length
targets; here Qwen3.5-2B lands **26% short (median)** of its *own*, and the worst
decile writes barely half of what it promised.

This is the cleanest version of the A1 result the project has: the model cannot
plead misreading the instruction, because it authored the instruction one turn
earlier. What is missing is not comprehension but a count→gap→extend loop.

Self-consistency replicated at **0.495** (0.471 in 0015), so that number is stable.

## 2. Qualitative: the model's natural convention vocabulary

`spec_extract` types what a verifier can score. Everything else was being written
off as "unextractable" — but those lines are latent defaults being verbalized,
which is the phenomenon the project exists to study. `qualitative.py` inventories
them by theme.

**The cue determines which kind of default you get, and the trade is sharp:**

| | concrete cue | soft cue |
|---|---:|---:|
| typed slots per response | **4.5** | 0.9 |
| extraction coverage | **0.66** | 0.11 |
| qualitative lines per response | 2.7 | **11.5** |

Asking for numbers suppresses the qualitative vocabulary; asking openly
suppresses the metrics. **The model's natural declaration is qualitative** —
quantification has to be demanded explicitly.

### Theme distribution (soft cue, 800 lines)

| theme | share |
|---|---:|
| clarity_simplicity | **19.5%** |
| tone_register | **14.1%** |
| narrative_structure | 8.5% |
| formatting_style | 6.2% |
| content_inclusion | 2.2% |
| grammar_mechanics | 1.8% |
| person_perspective | 1.6% |
| factuality | 1.5% |
| content_exclusion | 1.5% |
| safety_scope | 1.5% |
| audience | 1.4% |
| engagement | 1.2% |
| *unthemed* | 48% |

### Discovery: a self-imposed content policy

The unthemed set surfaced a whole dimension the typed schema does not model at
all — the model volunteers content prohibitions nobody asked for:

> "No external links or URLs" · "No personal anecdotes" · "No advertising" ·
> "No political statements" · "No religious references" · "No offensive content" ·
> "No violence" · "No controversial content"

Alongside content *inclusions*: "Include a title", "Include a call to action",
"Include citations to support claims".

This is a genuine latent default — a standing editorial policy carried into every
response — and it is exactly the kind of unstated convention the project is about.
It has no slot.

## 3. Consequence for the schema

**The `register` slot is badly under-specified.** The schema devotes a single
soft, judge-only slot to the entire qualitative half. The data shows that half is
**at least eight distinct dimensions** — clarity, tone, narrative structure,
person, audience, engagement, factuality, content policy — and together they are
the *majority* of what the model actually declares.

Two implications:

1. A trained model should emit **both halves**: quantified slots for `R_exec`
   and qualitative conventions for the judge. The current interface treats the
   second as an afterthought when it is most of the volume.
2. The soft slot needs decomposing before it can be scored at all. "register:
   playful" cannot represent "third person, no jargon, no political content,
   ends with a call to action".

## Caveats

- Themes are keyword patterns, not a classifier; **48% of soft-cue lines remain
  unthemed**, so the inventory is a lower bound and the shares are approximate.
- The qualitative sample is the stored `unextracted` field, capped at 8 lines per
  record, so proportions are better trusted than absolute counts.
- Soft-cue *length* statistics are unreliable (mean |err| 194%, p90 +750%) —
  vague phrasings parse badly. Only the concrete-cue length numbers should be
  quoted.
- Single model, one temperature.

## Open items

- Decompose `register` into the measured dimensions and re-run schema
  adjudication on each (does the model show a *stable* prior per dimension?).
- Drive unthemed below ~20%, or switch to a judge for the qualitative half.
- Run both cues on Gemma E4B / E2B.
- **E0.2 binding still not run.**
