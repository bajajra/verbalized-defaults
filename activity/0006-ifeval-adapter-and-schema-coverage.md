# 0006 — IFEval adapter and schema coverage (a result that affects E0.1)

**Date:** 2026-07-21
**Result:** 39/39 tests passing. **Only 59.5% of IFEval prompts are fully
expressible in the frozen 12-slot schema.** This bounds what E0.1 can measure and
should be settled before the schema is frozen for data generation.

## Context

The adapter maps IFEval/IFBench instruction metadata (`instruction_id_list` +
`kwargs`) into our typed `Spec`. It does double duty:

1. **E0.1 oracle prefill** — builds the ground-truth spec to prefill into the
   model's thinking, from benchmark metadata rather than from a model.
2. **`R_bind` ground truth** — the reference the model's own declared `[given]`
   slots get scored against.

Every slot it emits is tagged `[given]` by construction.

## Ground truth

IFEval is 541 prompts carrying 834 instruction instances across 25 distinct
instruction types (enumerated directly from `input_data.jsonl`, not from memory).

## Two bugs caught by building it

**1. Word-boundary matching broke on `P.S.`** The keyword matcher wrapped needles
in `\b...\b`. For a marker ending in `.`, the trailing `\b` can never match before
whitespace, so a real postscript scored zero — i.e. the taxonomy's single most
cited failure case was silently unverifiable. Anchors are now applied only on
sides where the needle actually starts/ends with a word character. Pinned by an
end-to-end adapter→verifier regression test.

**2. IFEval's `less than` is strict.** `relation: "less than"` means
`count < value`, so the inclusive form is `value - 1`. Mapping it to `<= value`
would have put every such constraint off by one — exactly how a verifier drifts
out of parity with the benchmark.

## Headline result: schema coverage

| | instances | share |
|---|---:|---:|
| mapped cleanly | 593 | **71.1%** |
| partial | 37 | 4.4% |
| unmapped | 204 | 24.5% |
| **prompts fully expressible** | **322 / 541** | **59.5%** |

Splitting the unmapped 24.5% by *why*:

| Reason | instances | share | Verdict |
|---|---:|---:|---|
| Bucket C (letter/capital arithmetic) | 58 | 7.0% | correctly excluded — the taxonomy says ignore these |
| **Genuine schema gaps** | **146** | **17.5%** | candidates for new slots |

The genuine gaps, by volume:

| Gap | instances | Cheapest fix |
|---|---:|---|
| `number_highlighted_sections` (`*highlight*` count) | 48 | a `markup` slot |
| `title` (`<<title>>` wrapper) | 37 | extend the existing `wrappers` slot |
| `number_placeholders` (`[placeholder]` count) | 27 | same `markup` slot |
| `two_responses` (multi-slot decomposition) | 24 | structural; harder |
| `constrained_response` (fixed answer options) | 10 | low value |

## Why this matters for E0.1 and Gate 1

E0.1 prefills an oracle spec and measures the lift over vanilla. **The probe can
only surface what the schema can express.** On the 40.5% of prompts whose
constraint set is partly inexpressible, the prefilled spec is silently
incomplete, the model still fails the missing constraints, and the measured lift
is diluted toward zero.

Gate 1's thresholds (≥5pt → proceed, <2pt → H0 falsified, pivot to execution
training) were written assuming the oracle spec captures the constraint. Run
naively over all 541 prompts, a *schema coverage* problem would be misread as
*evidence against H0* — a false kill.

**Assumption adopted for now:** E0.1 will report the fully-expressible subset
(n=322) as the primary measurement and the full set as a secondary number, with
both stated. That keeps the H0 test honest — the hypothesis is about surfacing
conventions, and one can only surface what is modelled.

## Recommendation (decision needed before schema freeze)

Adding a `markup` slot (highlight + placeholder counts) and a `title` field on
the existing `wrappers` slot would recover **112 instances / 13.4%** of
instruction instances, lifting clean mapping from 71.1% to roughly 84.5% and
raising the fully-expressible prompt share substantially — for two slots' worth
of work. `two_responses` and `constrained_response` (34 instances) are genuinely
structural and not worth chasing.

The schema is documented as frozen *before data generation*, and no data has been
generated, so this is the correct and last cheap moment to make that call.

## Open items

- **Decide: extend the schema (recommended) or accept 59.5% and subset E0.1.**
- IFBench coverage is unmeasured. Its 58 held-out constraint types are the actual
  OOD eval; the same coverage analysis should be run there, and the answer will
  likely be worse since those families were designed to be unlike IFEval's.
- Carried over: `forbidden` substring-vs-word-boundary default;
  `structure: sections` splitter semantics.
