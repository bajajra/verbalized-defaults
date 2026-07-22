# 0008 — IFBench coverage (a threat to the experiment design) + IFStruct review

**Date:** 2026-07-21
**Result:** Schema v2 expresses **95.8% of IFEval but only 10.5% of IFBench**
(24.5% of IFBench's real-convention subset). This undermines IFBench's role as
the primary external OOD eval and should change Gate 3.

## Guardrail applied first

IFBench is the held-out OOD eval. **No slots were added to cover it.** Designing
the representation by looking at the test set would destroy the generalization
claim, so this entry only *measures* and *classifies*.

## Method

IFBench test = 300 prompts, 58 families, 344 instruction instances. Each family
was hand-classified on two independent axes, recorded as a reviewable table in
`scripts/measure_ifbench_coverage.py` rather than buried in code:

1. **Bucket A (a real convention) or Bucket C (gimmick / arithmetic)** — the
   taxonomy's existing split. This is not a convenient invention: the project's
   own `ifbench.md` report already flagged that IFBench "mixes real asks with
   gimmicks (ratio:\*, syllable-parity, prime-word-lengths, string-reversal…)".
2. **Can schema v2 express it** — yes / partial / no.

## Results

| Split | instances | share |
|---|---:|---:|
| Bucket A (real convention) | 147 | 42.7% |
| Bucket C (gimmick / arithmetic) | 197 | **57.3%** |

| Schema v2 expressiveness | over all 344 | over Bucket A (147) |
|---|---:|---:|
| yes | 36 (10.5%) | 36 (**24.5%**) |
| partial | 27 (7.8%) | 27 (18.4%) |
| no | 281 (81.7%) | 84 (57.1%) |

Against IFEval's 95.8%, this is a collapse of the same shape and roughly the
same magnitude as the model-level collapse IFBench was built to expose
(IFEval ~0.90 → IFBench ~0.39). **The overfitting signature reappears at the
representation level, not just the model level.**

## Reading it honestly — two things are true at once

1. **Our schema is IFEval-shaped.** It was derived from IFEval's convention
   families and does not generalize to unseen constraint types. That is a real
   limitation and should be stated as one, not explained away.
2. **IFBench is a poor fit for this thesis.** 57.3% of it is Bucket C by the
   taxonomy's own criteria — palindromes, prime word lengths, syllable parity,
   string reversal, stop-word ratios. Our project explicitly excludes these as
   gimmicks. So IFBench largely measures something the thesis does not claim to
   address.

A hand classification that happens to flatter our schema deserves suspicion,
which is why both numbers are reported (all instances *and* Bucket A only) and
the table is checked in for revision.

## Consequence: Gate 3 needs rethinking

An oracle spec can carry at most **~10–18% of IFBench**. Any spec-mediated
method therefore has a very low ceiling there, and Gate 3 — "does assumed-slot
RL beat RLCF/UltraIF on IFBench?" — would be scored mostly on constraints the
spec cannot represent. That is close to an unwinnable test, and a failure there
would be uninformative rather than falsifying.

**Recommended changes:**

1. **Promote `OOD-int` to the primary OOD eval.** The experiment design already
   specifies 120 authored constraint families with a frozen 84/36 train/held-out
   split. That held-out set is contamination-proof, consists of real conventions,
   and is the honest generalization test for this thesis.
2. **Demote IFBench to a secondary eval, always reported as two numbers**: the
   full set, and an **IFBench-A** subset (the 147 real-convention instances).
   A full-set number alone is dominated by gimmicks.
3. **Do not fit the schema to IFBench.** Held.

## Integrity note

I have now seen IFBench's family list. Any future schema extension I propose is
therefore **no longer blind to the OOD eval**. Mitigation: the 36 held-out
families must be authored from the taxonomy and first principles, frozen before
use, and any schema change from here must disclose whether it overlaps an
IFBench family. Some Bucket-A gaps (nested sub-bullets, indentation,
sentence-level positional) are plausible conventions our own authoring would
likely produce independently — but that claim is now unfalsifiable from my side
and should be treated with suspicion.

## IFStruct v1.0 (Liquid AI) — reviewed, not adopted

A generative benchmark + dataset for **structured-output compliance**: does a
model emit valid JSON/YAML matching a schema presented in varied realistic forms
(chat prose, bullet field lists, raw JSON Schema, annotated examples, ASCII
tables)? Binary pass/fail on format constraints (JSON/YAML validity, top-level
structure, item counts, code fencing, commentary rules) and schema compliance
(fields, types, enums, numeric bounds, nesting). Released as a GitHub repo and
`LiquidAI/ifstruct-v1.0` on HF.

**Relevance — adjacent, but a different axis.** IFStruct measures compliance with
an *explicitly given* schema. Our thesis is about *latent conventions that fill
the dimensions nobody specified*. In our own vocabulary IFStruct is almost purely
a **binding + execution** test with no `[assumed]` component, so it cannot
exercise the contribution that distinguishes this work.

Three things worth taking from it anyway:

- **Its "commentary rules" are our `response_boundary` slot** — no preamble, no
  chatter around the payload. Independent evidence that slot is a real,
  separately-verifiable convention rather than a Gemma-specific patch.
- **`Qwen3.5-4B` scores 36.25%.** Our subject is Qwen3.5-2B, same family, so
  expect meaningfully lower — a useful prior on how weak the base model is at
  verifiable format compliance.
- **LFM2.5-350M went 21.10% → 44.90% with GRPO.** Direct evidence that RLVR on
  verifiable output constraints works at *very* small scale, which supports the
  2B GRPO plan on the 5090.

**Decision: cite in related work, do not adopt as an eval.** Adopting it would
pull the project toward structured-output/schema compliance — a different and
already-crowded problem — and would require modelling nested JSON schemas, far
outside "conventions".

## Open items

- Author the 120 constraint families (84/36 split) — now the critical path, since
  `OOD-int` becomes the primary OOD eval.
- Update the experiment design doc: Gate 3's IFBench threshold, and the IFBench-A
  reporting split.
- Carried over: `forbidden` substring-vs-word-boundary default.
