# 0027 — Deviations from the pre-registered design

**Date:** 2026-07-23

A record of where the executed Phase-0 work departed from
`verbalized-defaults-proposal.md` / `verbalized-defaults-experiments.md`, with the
reason and the evidence for each. This is the diff between what was planned and
what was run; it is not a list of bugs (those are in the numbered activity log).

Categories: **adopted** (proceeding this way), **forced** (compute/tooling
constraint), **scope** (reduction), **added** (not in the design), **recommended**
(proposed, not yet acted).

---

## 1. Interface: typed `<spec>` DSL → natural-language spec  [adopted]

**Design:** the model emits a typed 12-slot `<spec>` block; each slot has a literal
verifier. The typed spec is the interface.

**Executed:** the model emits **plain-English** convention statements; a rule-based
extractor (`spec_extract`) derives the typed `Spec` for verification (the
"hybrid"). Natural language is the working interface; the typed form is a derived
artefact used only for scoring.

**Reason / evidence:** E0.1 (0014) — the typed DSL underperforms plain English
carrying identical constraints by **+0.063 (Qwen) / +0.038 (E4B)** prompt-strict,
both CIs excluding zero, on models that have never seen the format. The typed spec
in reasoning also failed to clear Gate 1 (E4B +0.017 ns, Qwen −0.042). The
contradiction test (0024) confirmed an NL spec is causal (0.99–1.00 control on
case).

**Consequence:** added `spec_extract` (NL→typed) and `spec_nl` (typed→NL). The
typed-vs-NL gap does not kill C1 because it is measured on untrained models; the
Phase-1 bar is now "typed must recover ≥+0.038/+0.063 to match NL."

---

## 2. Subject models  [forced]

**Design:** primary **Gemma 4 E4B-it** (bf16 train), Gemma 4 E2B probe,
Qwen3.6-4B trained cross-family replication, a 27B scale point, 35B judge.

**Executed:** primary **Qwen3.5-2B** (bf16); Gemma 4 E2B and E4B as **NVFP4,
inference-only** subjects. No trained replication, no scale point, no judge model
used yet.

**Reason:** available compute is one RTX 5090 (32 GB) + a DGX Spark; only a ~2B
model is trainable here (0001). NVFP4 Gemmas cannot be fine-tuned through the
quant, so they are inference-only.

**Consequence:** the failure taxonomy (built on bf16 E4B) does not transfer;
Phase-0 was re-run on the actual subjects. Qwen's separate reasoning channel is a
cleaner substrate than Gemma's inline-thinking artefact.

---

## 3. Scope: explicit small-model study  [scope]

**Design:** scale point (27B), from-base ablation, trained cross-family
replication.

**Executed:** **dropped all three.** This is a below-4B study; the design's "does
it work below 4B?" probe is promoted to the main question.

**Reason:** compute (as §2). Stated as scope, not hidden.

---

## 4. Schema: 12 slots → 15 (v2) → decomposed (v3)  [adopted]

**Design:** 12 frozen slots, frozen before data generation.

**Executed:** grew to **15** (added `markup`, `positional`, `response_options`;
extended `wrappers`/`must_include`/`structure`), then v3 decomposed `register`
into `person` (programmatic) + `tone`/`jargon_level`/`audience` (judge) and added
`content_policy`.

**Reason / evidence:** the 12-slot schema expressed only 59.5% of IFEval prompts;
v2 reaches 93.5% (0006/0007). v3 followed the empirical finding that `register`
was one soft slot carrying ≥8 distinct dimensions the model actually declares
(0016). Membership decided by measured priors, not by hand (0010).

**Disclosure:** two v2 additions (`markup`, `wrappers.title`) and the `emoji`/`nesting`
candidates overlap IFBench families; justified by measured priors, but the overlap
with the held-out eval is stated (0006/0010).

---

## 5. Added the `other` slot  [added]

**Design:** every constraint maps to a typed default-bearing slot.

**Executed:** added an **`other`** slot for stated constraints on dimensions with
**no latent default** (letter arithmetic, palindromes). It can only ever be
`[given]`; excluded from `R_exec`; carried for binding.

**Reason:** a typed slot exists iff its dimension has a latent default; predicates
with no default (Bucket C) still must be carried so binding does not silently drop
them (0009).

---

## 6. Declaration elicitation: two controlled phases + a cue  [adopted]

**Design:** model emits the spec in-thinking, then generates (single pass).

**Executed:** **two phases** — elicit the declaration bounded by a delimiter we
control (`<conventions>…</conventions>`), then feed it back and generate. A
**cue** (concrete vs soft) in the system prompt asks for the declaration.

**Reason:** single-pass fails because these models write reasoning as prose and do
not emit a closing think token, giving a spurious 83% no-declaration rate (0015).
The concrete cue is needed to elicit checkable values (the natural declaration is
qualitative: 0016).

---

## 7. Binding metric: value-aware  [adopted]

**Design:** binding = did the declared `[given]` slot match the prompt constraint
(implicitly slot-level).

**Executed:** a slot counts as bound only if its declared **value** would satisfy
the requirement (`binding.py`). Slot-presence alone counted 33% wrong-valued slots
as bound and inverted the E0.4 diagnostic (0020).

---

## 8. E4.1 run as an inference-time diagnostic, not the training comparison  [scope/added]

**Design:** E4.1 compares **trained** conditions (SFT-only vs +D3-dpo vs
matched-ordinary-data vs matched plain RLVR) on the prior battery.

**Executed:** ran the battery as a **pre-training inference probe** (vanilla /
oracle-declare / self-declare) to test whether surfacing helps override a prior
(0022). The trained comparison is untouched.

**Reason:** no training has been done; the pre-training diagnostic is the cheap
falsification available now.

---

## 9. Added: the contradiction test  [added]

**Design:** E4.3 "slot-control score" prefills a spec value and measures output
control; there is no system-rule-vs-spec contradiction test.

**Executed:** built a contradiction test (system rule vs reasoning-spec) to isolate
the spec's causal power (0024). Not in the design; run because E4.1's spec was
redundant with the user instruction.

---

## 10. Sampling: temperature 1.0  [adopted]

**Design:** report temp-0 **and** temp-0.7 ×5.

**Executed:** **temp 1.0** (top_p 0.95). Temp-0 causes verbatim repetition loops on
these models, with asymmetric truncation that manufactured a false negative
(0011/0012).

---

## 11. Storage & serving infrastructure  [adopted]

**Design:** unspecified.

**Executed:** immutable, self-describing **runstore** (full untruncated text, no
stored metrics, provenance, `verify_run`) after a 2000-char answer cap corrupted a
length finding (0020/0021); **decoupled vLLM server/client** so probes import no
vLLM (0010).

---

## 12. Recommended, not yet acted

- **Demote IFBench to a secondary eval**, always reported as full-set plus an
  IFBench-A (real-convention) subset, because 57% of IFBench is Bucket C (0008).
  The design treats IFBench as the primary external OOD eval.
- **Author the 120 constraint families (84/36 split)** — the design's `OOD-int`.
  Not built; would become the primary OOD eval if IFBench is demoted.
- **Re-centre on execution (`R_exec`) over binding/surfacing** — a
  recommendation from the Phase-0 findings (execution is the dominant failure on
  capable models; 0025), not yet a design change.

---

## Not deviated from

Kept as designed: the `[given]`/`[assumed]` provenance split; the C2
binding/execution factorization as the object of study; the Bucket A/B/C
discipline; verifier metric parity with IFEval (measured, 0005); the
falsification-first / pre-registered-gate stance; decontamination intent (though
no training data has been generated to decontaminate yet).
