# Verbalized Defaults: externalizing latent generation conventions as a trainable, verifiable constraint interface

**Status:** research proposal — **draft 2, repositioned after prior-art review** (`compass` novelty study, 2026-07)
**Target model:** Gemma 4 E4B (then Qwen3.6-4B replication)
**Inputs:** IFEval/IFBench/Multi-IF failure taxonomy (deepdive-length/case/keywords/structure, sensible-failure-modes, ifbench, multiif, failure-taxonomy-and-data-mining)

**Changes from draft 1 (summary):** contributions reordered around what the lit review found defensible. The binding/execution factorization is now the headline; counterfactual slot intervention is second; the "wild prompts as free IF supervision" claim is *narrowed* to "self-consistency against self-declared defaults" and must beat RLCF/UltraIF head-to-head to be claimed at all; spec-as-state and interleaved verification are demoted from contributions to applications; steerability is a consequence, not a capability claim.

---

## 1. The observation, restated as a hypothesis

During SFT the model absorbs a large set of *conventions* that are never stated anywhere: an essay is 500–3k words, a rubric is ~20 sentences, verse lines start with a capital, proper nouns are title-cased, "P.S." is spelled "P.S.", a chorus repeats its bullets, a response stops when the content "feels done." These are **latent defaults** — priors over the free dimensions of a response (length, case, structure, register, format) that fill in whatever the prompt leaves unspecified. (Verbalized Sampling, Zhang et al. 2025, supplies a mechanistic account of why such defaults exist — typicality bias in preference data collapsing output modes; our "latent defaults" are the IF-relevant face of the same phenomenon.)

The failure taxonomy shows that nearly every *real* (Bucket A) instruction-following failure is the same event: **an explicit instruction loses a silent fight against a latent default.**

| Taxonomy finding | Latent default that won |
|---|---|
| A1: "never registered" length failures — essay stops at ~40 sentences vs required 50/100 | genre's natural-length prior |
| A2: poem stays sentence-cased despite lowercase rule (doc 104); "P.S." never recased | genre typography prior; abbreviation spelling prior |
| A2: case applied to headers/bullets only, prose exempt (docs 145, 394) | implicit scoping convention ("caps = labels") |
| A3: 3 bullets *per stanza* instead of 3 total (docs 204, 316) | "each stanza gets its own bullets" layout prior |
| A4: `correlated` → `correlation`, `engage` → `engages` | "use the grammatically natural inflection" prior |
| Multi-IF structural drift (`multiple_sections` 1.00→0.23, our Gemma run) | each turn re-derives shape from priors instead of carried state |

The fight is silent because the default is never represented in tokens. The model cannot deliberately override, verify, or even *notice* a variable that exists only as a distributional tendency. The taxonomy's summary — failures are overwhelmingly "never checked," not "can't do" — points at the same gap: there is nothing explicit to check *against*. The clarification literature (Su & Cardie 2025; RIFTS) documents the sibling failure: models silently *make* assumptions on underspecified prompts rather than surfacing them. Where that line of work asks the model to *ask*, we make it *declare and then get verified against* the assumption — a different move.

**Hypothesis (H0):** if the model is trained to *verbalize the resolved value of every convention-governed dimension before generating* — including the dimensions the user did NOT specify — then (a) explicit instructions bind to token-level slots instead of fighting priors, (b) each declared slot becomes programmatically verifiable, enabling dense factorized reward, and (c) varying slot values across training samples causally decouples the slot from the prior.

---

## 2. The interface, and the four contributions

Before writing the response, the model emits a compact spec in its thinking (or as a header in no-think mode):

```
<spec>
audience: middle school            [given]
register: simple, playful, fun facts   [assumed]
length: ~300 words                 [assumed — my default for school essay]
case: standard                     [assumed]
structure: 3 paragraphs, no headers, no bullets   [assumed]
must_include: —      forbidden: —
end_marker: —        language: en  [assumed]
</spec>
```

Every slot is tagged **[given]** (extracted from the prompt) or **[assumed]** (the model's own default, now stated). On this interface we make four claims, ordered by defensibility per the prior-art review.

### C1 — The representational contribution: a typed spec of *conventions*, with provenance tags

The plan-then-generate lineage (Plan-and-Write, Yao et al. 2019; Aristotelian rescoring; QA-Blueprint, Narayan et al. TACL 2023 — the closest typed-intermediate-representation prior) plans **content**: what to say, in what order. No prior work declares a *typed, multi-slot spec of output conventions* — length, case, register, structure, wrappers, language — with per-slot [given]/[assumed] provenance. The nearest single-slot exception (structure-guided length control, arXiv 2511.01807) is length-only and inference-time. "Verbalized X" is an established term of art for externalizing a latent quantity into tokens (verbalized confidence, Lin 2022/Tian 2023; Verbalized Sampling 2025; Verbalized ML); applying it to **SFT-absorbed generation conventions** is new, and the branding is deliberate.

A consequence — not a contribution — is steerability: once the default is an addressable token-level object, a system prompt can edit it ("unless asked, ≤150 words"). Controllable generation (CTRL, PPLM, LIFT) already steers attributes, so we do **not** claim steering as new; we claim the *default itself* becomes explicit and addressable rather than an inaccessible distributional tendency, and we demo steering as evidence of that.

### C2 — The training contribution (headline): binding/execution factorization with two verifiable rewards

The spec factorizes IF into two separately measurable, separately trainable stages:

1. **Binding** — prompt → spec. Did the model extract every stated constraint into a [given] slot with the right value? Failure = the taxonomy's "never registered."
2. **Execution** — spec → output. Does the response satisfy its own declared spec? Failure = the taxonomy's "registered but slipped" (case leaks, morphological drift, delimiter off-by-one, miscounts).

Each gets a programmatic reward: **R_bind** matches declared [given] slots against constraints extracted from the prompt (penalizing missed, misread, *and hallucinated* constraints); **R_exec** verifies the output against the full spec — including [assumed] slots — with checkers aligned to the evaluator's literal metric (sentences by `.?!`, paragraphs by `\n\n`, exact strings, exact delimiter counts).

**Why this is the safe headline:** all existing verifiable-reward IF training — Tülu 3 RLVR, IF-RLVR/IFBench (Pyatkin et al. 2025), VerIF (hard/soft verification), AutoIF (execution feedback) — rewards the output against **prompt-given** constraints with a single monolithic signal. ConstrainPrompt and Nsvif *extract* prompt constraints into validators but are verification frameworks, not spec-first generation with training rewards. Nobody separates an *extraction* reward from an *obedience* reward. The factorization also has diagnostic value independent of training: it decomposes every IF failure into a measurable stage, and the taxonomy predicts the mapping (length ≈ binding, case ≈ execution, structure ≈ binding, keywords ≈ execution). If the diagnostic shows most failures are execution-side, the factorization's measurement value alone carries the paper.

### C3 — The causal contribution: counterfactual single-slot intervention against a *generation default*

Because the spec is explicit tokens, we can intervene on it: same prompt, k spec variants differing in **one** slot (length 150/300/800/2000; case standard/lower/CAPS), each with a verified-compliant target, trained in-batch so the only learnable signal is the causal link *spec slot → output property*. DPO variant mined from the model's own failures: chosen = spec-compliant output; rejected = the model's actual prior-default output under the same declared spec (the doc-104 capitalized poem under `case: lowercase` — literally "the prior winning the silent fight," pushed down directly).

Intellectual ancestor: counterfactually-augmented data (Kaushik, Hovy, Lipton, ICLR 2020) and contrast sets (Gardner et al. 2020), which minimally edit one attribute to break spurious *feature→label* correlations in classification. Our delta, stated explicitly: **the confound being broken is not a dataset artifact but a distributional generation default**, and the intervention is on a declared spec slot in generation space. The review rates this the freshest component; per its threshold, the claim is causal only if intervention-structured data beats *matched-size plain multi-constraint RLVR* on prior-targeted tests — that control is in the experiment design.

### C4 — The narrowed self-supervision contribution: self-consistency against self-declared defaults

**What we no longer claim:** "wild prompts become free verifiable IF training data." RLCF (Viswanathan et al., NeurIPS 2025 — WildChecklists, 130k instructions with checklist rewards) and UltraIF (An et al., EMNLP 2025 — wild prompts decomposed into constraint + eval question) already do that, and AutoIF/Suri/Conifer/Crab back-translate constraints from responses. Draft 1's version of this claim is dead as stated.

**What survives, precisely:** in *all* of that work, the verification criteria come from the **instruction** (UltraIF's decomposition, RLCF's checklist derived from the prompt) or from a **teacher** (RLCF's grading). R_exec on [assumed] slots verifies the output against the **policy model's own freely-declared defaults** — no externally specified constraint exists anywhere in the loop. The hypothesized advantages over prompt-derived criteria: (i) the constraint distribution is the model's *own* convention space — exactly the priors that fight instructions — rather than what a decomposer can parse from prompts; (ii) it trains the declare→execute link itself, which is the same muscle explicit constraints use; (iii) it needs no teacher, judge, or prompt parser at reward time — pure program checks.

This is now an **empirical question, not an assumed contribution**: C4 stands only if assumed-slot training beats an RLCF-style checklist baseline and an UltraIF-style baseline at matched compute on IFBench (held-out families). If it merely matches them, we report it as a simpler-infrastructure equivalent and drop it from the abstract.

---

## 3. Applications (not contributions)

**Spec-as-state for multi-turn drift.** Re-emitting the accumulated spec each turn turns constraint forgetting into a *binding* failure punished by R_bind. The review found constraint-ledger/restatement ideas already emerging in 2025–26 multi-turn work — including the caveat that inference-time restatement can *hurt small models* (−2.1pp on Qwen3-8B in one study) by occupying context. That caveat is actually our opening: prior ledger work is prompting; we *train* the carry-forward with an explicit reward on ledger completeness. Framed as the temporal instantiation of C2, evaluated on Multi-IF (citing the paper's own headline figure, 0.877→0.707 over 3 turns for o1-preview, alongside our Gemma measurement of −0.22/−0.26 prompt-strict).

**Interleaved verification.** Draft→check-each-slot→patch against the spec. Closest neighbor: TICK/STICK (Cook et al. 2024) — self-generated YES/NO checklist, self-graded, inference-time refinement. Our deltas are real but incremental, so this is an application: the target is a *typed fixed-schema* spec including [assumed] slots (not per-instruction checklist questions), the per-slot checks are *programmatic literal metrics* (not LLM-judged YES/NO), and the loop is a *training target* with rewards, not only inference-time. The "LLMs Cannot Self-Correct" line (Huang et al., ICLR 2024) supports the design choice: intrinsic self-correction fails without a mechanical target — the spec is the mechanical target. Experiments include a STICK head-to-head at matched inference budget.

---

## 4. Method (unchanged in structure; baselines added)

Phases as in draft 1 — 0: convention-schema discovery and default measurement; 1: SFT on spec-format data (with no-spec / free-form-plan / untyped-spec token-matched controls); 2: counterfactual DPO and in-batch intervention; 3: RLVR with α·R_bind + β·R_exec on mixed constrained+unconstrained streams; 4 (optional): interleaved verify. All gold data hard-gated by programmatic verifiers; Bucket-B judge triage stays in the loop; held-out constraint families frozen at day 0.

New required baselines (from the review): **RLCF-style checklist reward** and **UltraIF-style decomposition data** at matched compute in Phase 3; **Tülu-3-style direct prompt-constraint RLVR** (no spec) in Phase 2; **STICK** at matched inference budget in Phase 4; **plain multi-constraint RLVR at matched size** against the intervention data in the C3 tests. Full matrix in `verbalized-defaults-experiments.md`.

---

## 5. Positioning and must-cite map

Lead with the synthesis: *an interface and a training decomposition*, not an IF trick — no single component is safe as a standalone "first," but no prior work combines a pre-generation typed convention-spec, [given]/[assumed] provenance, factorized binding/execution rewards, and counterfactual slot intervention.

| Area | Must cite | One-line delta |
|---|---|---|
| Plan-then-generate | Plan-and-Write; QA-Blueprint (Narayan 2023); arXiv 2511.01807 | they plan content / single slot; we declare typed conventions with provenance |
| Verifiable-reward IF | IFEval; Tülu 3; **IFBench/IF-RLVR (2507.02833)**; VerIF; AutoIF | all reward vs prompt-given constraints, monolithically; we factorize extraction vs obedience |
| Wild-prompt IF supervision | **RLCF (2507.18624)**; **UltraIF (2502.04153)**; Suri; Conifer; Crab | their criteria are prompt-/teacher-derived; ours are the policy's own declared defaults |
| Self-verification | **TICK/STICK (2410.03608)**; Self-Refine; Reflexion; Huang et al. ICLR 2024 | typed fixed schema, programmatic per-slot checks, training-time not inference-only |
| Counterfactual data | **Kaushik et al. ICLR 2020**; contrast sets; Polyjuice | confound broken is a latent generation default, not a dataset artifact |
| Verbalized-X | Verbalized Sampling; verbalized confidence; VML | new latent quantity: SFT-absorbed generation conventions |
| Multi-turn | **Multi-IF (2410.15553)** (cite 0.877→0.707 exactly); 2025–26 ledger work incl. the small-model caveat | trained carry-forward with binding reward vs inference-time restatement |
| Controllable generation | CTRL; LIFT | steerability is a consequence of externalization, not a claimed capability |

**Concurrent-work risk** (checklist rewards and wild-prompt IF are hot): mitigate by getting the Phase-0 probes and the C2 diagnostic out early (workshop/preprint) — the factorization diagnostic is the piece least likely to be scooped and the cheapest to publish first.

## 6. Risks (updated)

Draft-1 risks stand (spec gaming bounded by schema granularity; binding-reward symmetry against hallucinated slots; Bucket-B verifier hygiene; 4B execution ceiling; inline-thinking pollution → `response_boundary` slot). Added:

- **C4 collapses to RLCF-equivalence.** Pre-registered: if it doesn't beat the checklist baseline on held-out families, it moves out of the abstract and the paper leans on C2+C3.
- **Ledger hurts at 4B** (per the restatement caveat). Pre-registered: report the trained-vs-prompted ledger comparison either way; a negative here is itself a useful finding about small-model context budgets.
- **Reviewer weights the TICK/STICK overlap heavily.** Mitigation: interleaved verify is framed as application from the start; the STICK head-to-head is in the matrix.

---

*One-line summary (unchanged): teach the model to say its defaults out loud in a typed spec, reward it separately for reading the prompt into the spec and for obeying the spec — including the parts nobody asked for — and the silent fight between instructions and SFT conventions becomes an explicit, verifiable, trainable variable.*
