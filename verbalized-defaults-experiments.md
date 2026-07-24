# Verbalized Defaults — experiment design v2 (repositioned after prior-art review)

Companion to `verbalized-defaults-proposal.md` (draft 2). Covers: model selection, data curation pipeline, training recipes, and the experiment matrix that defends each contribution, with metrics, baselines, and go/kill gates.

**v2 changes:** contribution ordering follows the novelty study — C2 (factorization) is now the headline, C4 (counterfactual) second, the assumed-slot claim (was C3) is demoted to conditional and must beat RLCF/UltraIF head-to-head; spec-as-state and interleaved verify are applications. New external baselines: RLCF-style checklist reward (E3.5), UltraIF-style data (E3.6), STICK (E6.2), plain multi-constraint RLVR control for causality (E4.1). Multi-IF paper figure (0.877→0.707) cited alongside our Gemma-measured drift.

**Contributions to defend (v2 ordering)**

- **C1** — The typed convention-spec with `[given]/[assumed]` tags improves IF over no declaration *and* over untyped free-form planning (the representational claim; steerability is demoted to a demo, not a capability claim).
- **C2 (headline)** — Binding/execution factorization: the two stages fail independently, can be measured independently, and rewarding them separately beats a single monolithic reward — including the Tülu-3-style direct prompt-constraint reward.
- **C3** — Counterfactual slot intervention causally breaks convention priors, beyond matched-size ordinary SFT **and beyond matched plain multi-constraint RLVR** (the survey's causality threshold).
- **C4 (conditional)** — Self-consistency reward on *assumed* slots over unconstrained prompts improves unseen-constraint generalization **beyond RLCF-style and UltraIF-style baselines at matched compute**. If it only matches them, C4 leaves the abstract and is reported as a simpler-infrastructure equivalent.
- **App-1 (was C5)** — Trained spec-as-state flattens multi-turn drift; framed as the temporal application of C2, with the trained-vs-prompted-ledger comparison (prior work found inference-time restatement can hurt small models).
- **App-2 (was C6)** — Interleaved verify-against-spec vs STICK at matched inference budget; framed as application (typed schema + programmatic checks + training-time), not contribution.

---

## 1. Models

| Role | Model | Why |
|---|---|---|
| **Primary subject** | **Gemma 4 E4B-it** (bf16 checkpoint for training; eval both bf16 and the QAT w4a16 deploy config) | Full harness, baselines, and ~thousands of triaged failure dumps already exist for exactly this model. Train on bf16 — never fine-tune through the w4a16 quant; re-quantize after and confirm deltas survive QAT. |
| **Small-scale probe** | Gemma 4 E2B-it | Does the interface work below 4B? Cheap iteration on data-recipe bugs before E4B runs. |
| **Cross-family replication** | **Qwen3.6-4B-instruct** | Controls for Gemma-specific quirks — especially the inline-thinking-in-`content` artifact, since Qwen has a separate reasoning channel. If C1–C3 replicate here, the claim is about the method, not about Gemma's template. |
| **Scale point (stretch)** | next Gemma 4 sibling up, or Qwen3.6-27B (one headline config only) | One point to show the effect isn't a small-model artifact. LoRA if compute-bound. |
| **Teacher / rejection-sampling fallback** | Qwen3.6-35B-A3B (already serving locally as the judge) | Free, local, strong enough. Used only when target-model best-of-n can't produce a verified-compliant response. |
| **Judge** | Qwen3.6-35B-A3B thinking-ON (existing pipeline), Haiku cross-check on Bucket-B disagreements | Reuse the deployed A/B/C triage exactly as in the taxonomy plan. |

Training stack: LoRA (r=64) for all ablation sweeps; full-parameter FT only for the 3–4 headline configurations. TRL or OpenRLHF; GRPO for RLVR (verifiable rewards, no reward model needed).

**Why not train from base?** The claim is about *overriding* SFT-ingrained conventions, and the instruct model demonstrably has them (Phase-0 measurements). Post-training the instruct model is both the realistic deployment path and the honest test. A from-base run is a stretch-goal ablation, not core.

---

## 2. Slot schema (frozen before any data generation)

Twelve slots, each with a literal verifier matched to the evaluator's metric:

| Slot | Values | Verifier |
|---|---|---|
| length_words | point or narrow range (±10%) | whitespace tokens |
| length_sentences | point / floor / ceiling / range | split on `.?!` (NLTK punkt, same as IFEval) |
| length_paragraphs | count | split on `\n\n` |
| case | standard / lower / CAPS / title | char-class scan, all zones incl. abbreviations |
| structure | prose / N bullets (global) / N sections / json / table | markdown parse, exact counts |
| delimiters | exact separator strings | exact char match |
| must_include | exact strings (+ min counts) | exact substring, inflections don't count |
| forbidden | exact strings | substring incl. morphological containment |
| wrappers | quotes / start-phrase / end-phrase / title | exact match |
| language | ISO code | langdetect |
| register/audience | open vocab (small enum for verifiable subset) | judge-scored only (soft slot, excluded from R_exec) |
| response_boundary | "answer starts immediately with X / no preamble" | prefix match — the anti-inline-pollution slot |

Schema-granularity rule (anti-gaming): assumed length must be a point value or ≤±10% range; assumed structure must name exact counts. "10–10000 words" is rejected by the spec parser itself.

---

## 3. Data curation

### 3.1 Prompt sources

| Pool | Source | Use | Size |
|---|---|---|---|
| **U (unconstrained)** | WildChat-1M + LMSYS-Chat-1M first-turns, English, dedup, generation-style tasks only (essays, emails, stories, explanations, lists — things with convention-governed dimensions) | assumed-slot data, RLVR stream | 100k curated |
| **K (constrained)** | Base tasks from U ∪ No Robots ∪ Tulu-3 persona prompts, with constraints **programmatically composed on top** (Tulu-3 IF-data style) | binding + execution training | 60k |
| **M (multi-turn)** | 3-turn conversations built by our own constraint-accumulation generator over K-style bases (Multi-IF protocol, but our constraints — Multi-IF itself stays eval-only) | C5 | 8k conversations |

**Decontamination (critical):** IFBench is built from held-out WildChat — before anything else, remove from U every prompt within 8-gram overlap or >0.92 embedding similarity of the 300 IFBench prompts, all IFEval prompts, and all Multi-IF English conversations. Log the removal count. Without this, C3 is dead on arrival at review.

### 3.2 Constraint generator (the diversity engine)

Author **~120 constraint families**: IFEval's 25 + IFBench-*style* (not IFBench's actual 58 — those stay untouched) + new ones (position constraints, nested structure, conditional constraints "if you mention X then Y", stylistic bans, format mixtures). Each family = template + parameter sampler + programmatic verifier.

**Family split, frozen at day 0:** 84 TRAIN / 36 HELD-OUT. Held-out families never appear in any training data and form our internal OOD eval (`OOD-int`). IFBench remains the external OOD eval. This split is the backbone of E3.3.

Per K-prompt: sample 1–5 constraints, reject unsatisfiable combos (the doc-528 lesson: run a SAT-style pairwise conflict check; keep ~2% *deliberately* conflicting pairs, gold = surface the conflict explicitly).

### 3.3 Default measurement (feeds assumed slots)

Run the untouched target model over 2k stratified U-prompts (20 genres × 100), temp 0.7 ×3. Fit per-genre default distributions for every slot (essay length median/IQR, poem case behavior, list propensity...). Outputs: (a) `defaults.json` used to fill calibrated assumed values in SFT specs; (b) the "prior inventory" — the quantitative before-picture for C4.

### 3.4 Response generation & verification

For every training example:

1. Build spec programmatically: given slots from constraint-generator metadata (never from a model — binding labels must be exact); assumed slots sampled from `defaults.json` (SFT) or from intervention grids (§3.5).
2. Generate response with **target model, spec prefilled, best-of-n (n≤8) against the verifier suite**. Fallback to teacher only on persistent failure (tag provenance; cap teacher share at 30%, report the ratio).
3. **Hard gate:** every gold response passes all verifiers for its full spec — given *and* assumed slots. No fabricated self-audits, no "Total: 15" annotations (structure-deep-dive rule). Judge screens a 5% sample for Bucket-B-style verifier bugs before scaling.

### 3.5 The five training sets

| Set | Contents | Size | Defends |
|---|---|---|---|
| **D1** | K-prompts · spec-in-think · verified response. 70% thinking-form, 30% compact header-form (no-think transfer) | 30k | C1, C2 |
| **D2** | U-prompts · all-assumed spec · self-consistent verified response | 15k | C1, C3 |
| **D3-int** | Intervention sets: same prompt, k=4 spec variants on ONE slot (length ×4, case ×3, structure ×3), all verified. Stored grouped for in-batch training | 6k prompts → 24k examples | C4 |
| **D3-dpo** | chosen = spec-compliant; rejected = model's own prior-default output under the same spec (mined: prefill spec into *untouched* model, keep generations where output matches `defaults.json` value instead of spec value — verifier-confirmed). Plus Bucket-A failures from existing IFEval/IFBench dumps, judge-triaged | 12k pairs | C4 |
| **D4** | M-conversations: each turn's thinking re-emits the full accumulated spec, response re-satisfies everything; verified per-turn cumulatively | 8k convs | C5 |
| **Controls** | D1/D2 with (a) spec stripped, (b) spec replaced by free-form plan (teacher-paraphrased, matched token count), (c) untyped spec (tags removed) — same responses, same size | — | C1 ablations |

---

## 4. Experiment matrix

### Phase 0 — probes, no training (week 1; runs on existing harness)

| ID | Design | Metric | Gate |
|---|---|---|---|
| **E0.1 oracle prefill** | IFEval + IFBench, thinking-ON, spec constructed from benchmark metadata prefilled into think. vs vanilla ON. | Δ prompt-strict/loose per family | Lift ≥5pt overall → surfacing-limited, proceed. Lift <2pt → pivot budget to C6/execution. Predicted from taxonomy: big on case/structure, partial on length. |
| **E0.2 binding probe** | 4-shot spec emission on IFEval/IFBench; score `[given]` slots vs constraint metadata | binding P/R per family | First quantitative "never registered" rate. Feeds E2.1. |
| **E0.3 calibration probe** | 1k U-prompts: declare, then generate; verify output vs own declaration | self-consistency per slot | Gap = headroom for C3's reward. If already >95% consistent, C3's signal is thin — check before building RLVR. |
| **E0.4 self-spec decomposition** | Model emits own spec then answers; condition adherence on binding correctness | P(pass), P(pass \| bind✓), P(pass \| bind✗) | The C2 diagnostic table, pre-training. |

E0.1's oracle-vs-self gap (E0.1 minus E0.4) is itself the first estimate of how much binding training is worth.

### Phase 1 — SFT ablations (defends C1)

All LoRA on E4B, matched data size/steps/token counts, 3 seeds.

| ID | Condition | Question |
|---|---|---|
| E1.0 | untouched model (+ existing baselines) | floor |
| E1.1 | D1+D2 **no-spec control** | does the verified-response data alone explain gains? |
| E1.2 | D1+D2 **free-form plan control** | is it just "planning helps" (already known from structure deep-dive)? |
| E1.3 | D1+D2 **untyped spec** (no given/assumed tags) | do the tags matter? |
| E1.4 | D1+D2 **full typed spec** | the method |

**Metrics:** IFEval, `OOD-int` (held-out families), IFBench, all strict+loose prompt-level; thinking-OFF eval on header-form to check no-think transfer; AlpacaEval-2-LC + MT-Bench as quality guardrails (kill any config that drops >2pt LC).
**Claim C1 stands if:** E1.4 > E1.2 > E1.1 on OOD-int and IFBench with non-overlapping bootstrap CIs, and E1.4 > E1.3 shows the typing contributes. (Their temp-0 vLLM jitter is ~2pt — require deltas >2× jitter, and additionally eval at temp 0.7 ×5 samples with paired bootstrap.)

### Phase 2 — RLVR reward ablations (defends C2)

GRPO from the E1.4 checkpoint, mixed K+U prompt stream, ~8k steps, group size 8.

| ID | Reward | Question |
|---|---|---|
| E2.2a | α·R_bind + β·R_exec (full) | the method |
| E2.2b | R_exec only | is binding reward needed, or does execution pressure fix reading too? |
| E2.2c | R_bind only | sanity: binding alone shouldn't move execution much |
| E2.2d | **direct prompt-constraint reward, no spec** (Tulu-3 IF-RLVR baseline, same prompts/steps) | is the spec interface adding anything over standard IF-RLVR? |

**E2.1 (diagnostic, free):** re-run E0.2/E0.4 decomposition on every checkpoint. C2's measurement claim stands if (i) binding and execution accuracies move separately across conditions (b vs c), and (ii) per-family end-benchmark deltas are predicted by which stage the family was bottlenecked on (e.g., length families move with binding fixes, case families with execution fixes — the taxonomy's prediction).
**C2's training claim stands if** E2.2a > E2.2b,c and E2.2a > E2.2d on IFBench/OOD-int.

### Phase 3 — assumed-slot self-supervision (defends C3, headline)

| ID | Design | Question |
|---|---|---|
| **E3.1** | GRPO on **U-prompts only** (zero explicit constraints ever seen in RL), reward = R_exec on assumed slots (+R_bind trivially). Eval on IFBench + OOD-int. | Can self-consistency training on unconstrained data alone improve unseen-constraint following? |
| E3.2 | Mix sweep: 0 / 25 / 50 / 100% unconstrained share, fixed steps | dose–response |
| E3.3 | Train-family curve: RLVR with 10 / 25 / 50 / 84 constraint families, ± assumed-slot reward | does the assumed-slot reward flatten the generalization curve (less family-count dependence)? |
| E3.4 | Negative control: same U-prompts, same steps, generic quality reward (judge score) instead of R_exec | rules out "any RL on wild prompts helps IF" |
| **E3.5 (new)** | **RLCF-style baseline:** same U-prompts, checklist generated per prompt (Qwen3.6-35B-A3B builds + answers the YES/NO checklist locally, per the WildChecklists recipe), used as RL reward at matched steps/compute | is assumed-slot self-consistency better than prompt-derived checklist reward — or just equivalent with less infrastructure? |
| **E3.6 (new)** | **UltraIF-style baseline:** wild prompts decomposed into (query, constraint, eval question), constraint-injected SFT/RL data at matched size | same question vs the decomposition approach |

**C4 (was C3) stands if:** E3.1 beats its SFT starting point on IFBench by >2× jitter while E3.4 doesn't, **and E3.1 (or the E2.2a full config) beats both E3.5 and E3.6 on IFBench/OOD-int at matched compute** — the survey's pre-registered threshold. If it only matches E3.5/E3.6: report as an equivalence result (no teacher, no judge, no prompt parser at reward time — pure program checks) and pull the claim from the abstract; the paper then leans on C2+C3. E3.3 shows the +assumed curve above the −assumed curve especially at low family counts. Report per-family transfer (prediction: length windows, counts, structure benefit; exotic string puzzles don't).

### Phase 4 — counterfactual intervention (defends C4)

| ID | Design | Question |
|---|---|---|
| E4.1 | **Prior-targeted test battery** (fixed, written before training): 40 poem-lowercase, 40 P.S.-recase, 40 global-bullet-in-stanza, 40 length-2×-natural, 40 proper-noun-lowercase prompts — the taxonomy's five named priors. Compare: E1.4 (SFT only) vs +D3-dpo vs +matched-size ordinary D1-style data vs **+matched plain multi-constraint RLVR (no intervention structure — the survey's causality control)**. | does *intervention structure* beat equal-volume ordinary data AND plain RLVR on the stubborn priors? If not, C3 is not causal and is softened. |
| E4.2 | D3-int trained grouped-in-batch vs same examples shuffled | is the same-batch contrast doing work (the user's original mechanism), or is it just data diversity? |
| E4.3 | **Slot-control score:** prefill spec value X ∈ grid, measure P(output⊨X) vs P(output⊨default) per slot, before/after each config | the causal metric: a slot is "controlled" when P(⊨X) is flat-high across X and P(⊨default \| X≠default) ≈ 0. Report as a per-slot control curve. |

**C4 stands if:** intervention-trained > matched ordinary data on E4.1 battery, and E4.3 shows control curves flattening specifically for intervened slots (untouched slots as within-model controls).

### Phase 5 — multi-turn spec-as-state (App-1)

| ID | Design | Question |
|---|---|---|
| E5.1 | +D4 training → Multi-IF (eval-only, never trained). Metric: **t1→t3 prompt-strict slope**, plus per-constraint drift table (does `multiple_sections` 1.00→0.23 recover?) | does the ledger flatten drift? Baselines today: −0.256 OFF / −0.219 ON on our Gemma run (paper headline for o1-preview: 0.877→0.707 — cite exactly). Target: ≥50% slope reduction, turn-1 level not degraded. |
| E5.2 | Control: same M-conversations, gold responses identical, but **no spec re-declaration** in thinking | is it the multi-turn data or the ledger? |
| **E5.3 (new)** | **Prompted-ledger baseline:** untouched model + inference-time restatement prompt (the 2025–26 ledger recipe) vs our *trained* ledger | prior work found inference-time restatement can hurt small models (−2.1pp on Qwen3-8B); does *training* the carry-forward with R_bind rescue it at 4B? Either outcome is reportable. |
| E5.4 | Long-horizon stress: extend our generator to 5 turns (Multi-IF stops at 3) | does the ledger keep holding? |

### Phase 6 — interleaved verification (App-2)

| ID | Design | Question |
|---|---|---|
| E6.1 | Draft→check-each-slot→patch trajectories (verifiers run mid-trace during data gen) on the slots Phase 0 flagged execution-limited (predicted: long-form length, whole-response case). Declaration-only vs +verify; Δaccuracy per extra token. | prices the "self-verification via interleaved thinking" claim |
| **E6.2 (new)** | **STICK baseline** at matched inference budget: self-generated checklist + self-grade + refine (Cook et al. recipe), on the same eval slice | typed programmatic spec-check vs LLM-judged self-checklist — the head-to-head reviewers will ask for |

### Cross-cutting

- **Replication:** rerun E1.4-vs-E1.1/E1.2 and E3.1 on Qwen3.6-4B (the two claims a reviewer will attack first). Everything else Gemma-only.
- **QAT check:** re-quantize the final E4B checkpoint to w4a16, confirm headline deltas survive.
- **Steerability eval (new capability demo):** 20 system-prompt default edits ("unless asked, ≤150 words / always bullet-free / always en-US"); measure declared-default shift and output shift. Untouched model expected ≈0 — any reliable movement is a qualitatively new control surface. Goes in the paper as a capability, not a comparison.
- **Reporting:** all benchmark numbers = prompt-level strict AND loose, temp-0 plus temp-0.7×5, paired bootstrap CIs; per-family appendices; verifier code released with the family split.

---

## 5. Order of operations & kill gates

```
wk 1      E0.1–E0.4 (probes)            → GATE 1: prefill lift ≥5pt? binding errors ≥20% of failures?
wk 1–3    schema freeze, family split, decontamination, defaults.json, generator + verifiers
wk 3–5    D1/D2 + controls → E1.x sweep  → GATE 2: E1.4 > E1.2 on OOD-int?
wk 5–7    D3 + E4.x  ·  D4 + E5.x       (parallel; independent of RL)
wk 6–9    E2.x → E3.x                    → GATE 3: E3.1 moves IFBench?
wk 9–10   E6.1, Qwen replication, QAT re-check, scale point
```

- **Gate 1 fail** (no prefill lift): the bottleneck is execution, not surfacing → re-center on App-2 + count-and-extend execution training. The probes cost ~2 GPU-days; this is the cheapest possible falsification of H0. Note: if E0.2/E0.4 show failures are mostly execution-side, that *strengthens* C2's diagnostic value even as it weakens C1 — per the survey, the factorization diagnostic then becomes the headline.
- **Gate 2 fail** (typed spec ≤ free-form plan): the contribution collapses to "planning helps" (known) → salvage C2/C3, which don't strictly need the typing, and report the negative honestly.
- **Gate 3 fail** (assumed-slot RL ≤ RLCF/UltraIF baselines): C4 leaves the abstract, reported as equivalence-with-less-infrastructure; C2+C3 still form a coherent paper ("a factorized constraint interface for IF").
- **Publication hedge (concurrent-work risk):** checklist rewards and wild-prompt IF are hot areas. Get Phase 0 + the E2.1 binding/execution diagnostic out early as a workshop paper/preprint — it's the least scoopable piece and needs no training runs.

## 6. Known threats to validity (pre-registered answers)

1. **"It's just more IF data."** → E1.1 no-spec control at matched size; E4.1 matched-ordinary-data control.
2. **"It's just planning."** → E1.2 free-form-plan control at matched tokens.
3. **"It's just RLVR."** → E2.2d Tulu-3-style baseline at matched prompts/steps.
4. **Contamination.** → §3.1 decontamination + released overlap logs; OOD-int as a contamination-proof internal check (we authored the families, they never touched training).
5. **Verifier bugs become the target.** → judge screens gold data; Bucket-B triage stays in the RL loop; strict AND loose always reported.
6. **Spec verbosity confound.** → all controls token-matched; report output-length distributions per condition.
7. **Gemma-template artifact.** → Qwen3.6-4B replication; `response_boundary` slot addresses inline-thinking pollution explicitly.
8. **"RLCF/UltraIF already did this."** → E3.5/E3.6 head-to-heads at matched compute; claim narrowed to self-declared-defaults delta; explicit distinguishing paragraphs in the paper (criteria source: prompt/teacher vs the policy's own declaration).
9. **"STICK already does self-checklist verification."** → E6.2 head-to-head; interleaved verify framed as application with three stated deltas (typed fixed schema, programmatic per-slot metrics, training-time target).
