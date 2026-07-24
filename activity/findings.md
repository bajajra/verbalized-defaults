# Findings — measured results

Every number this project has measured, with its protocol and provenance.
This file is **data**; interpretation and graded claims live in
[conclusions.md](conclusions.md).

**All values are post-fix**, re-derived from stored raw generations after the
extractor de-biasing (0018). The `data/*.json` run summaries still hold pre-fix
values and must not be quoted.

---

## 0. Setup

| | |
|---|---|
| Subject models | `Qwen/Qwen3.5-2B` (bf16), `unsloth/gemma-4-E2B-it-NVFP4`, `unsloth/gemma-4-E4B-it-NVFP4` |
| Host | `turing` — RTX 5090, 32 GB, driver 595.71.05 |
| Serving | vLLM 0.25.0, torch 2.11.0+cu130, sm_120, `max-model-len 8192` |
| Sampling | temp **1.0**, top_p 0.95 (greedy is invalid — see §7) |
| Scoring | IFEval's own `instructions_registry`, not our verifiers |
| Stats | paired bootstrap over prompts, 10k resamples, 95% CI |

**Metric definitions**

- `prompt_strict` — all constraints in a prompt satisfied by the response as written.
- `prompt_loose` — satisfied by any of IFEval's 8 response variants.
- `instruction_strict` — fraction of individual constraints satisfied.
- `self-consistency` — fraction of the model's *own declared* slots the response satisfies.
- `binding recall` — `|declared ∩ required| / |required|`.
- `repetition` — fraction of duplicated 10-grams (degeneracy detector).

---

## 1. E0.1 — oracle spec prefill

**Protocol:** 541 IFEval prompts × 4 samples × 7 conditions × 2 models =
**30,296 generations**. Verified 15,148 rows/model, 0 duplicates, 2,164/condition.
E0.1 was **not** run on E2B.

### Qwen3.5-2B

| condition | p-strict | p-loose | i-strict | trunc/2164 | rep |
|---|---:|---:|---:|---:|---:|
| vanilla | 0.6557 | 0.6913 | 0.7455 | 40 | 0.017 |
| typed_insys | 0.6294 | 0.6705 | 0.7242 | 92 | 0.040 |
| nl_insys | **0.6835** | **0.7237** | 0.7695 | 62 | 0.025 |
| typed_think_sys | 0.6137 | 0.6465 | 0.7194 | 85 | 0.035 |
| nl_think_sys | 0.6765 | 0.7241 | **0.7710** | 70 | 0.030 |
| typed_prefix_sys | 0.5518 | 0.5910 | 0.6640 | 56 | 0.022 |
| nl_prefix_sys | **0.4972** | 0.5527 | 0.6181 | 105 | 0.044 |

### Gemma 4 E4B

| condition | p-strict | p-loose | i-strict | trunc/2164 | rep |
|---|---:|---:|---:|---:|---:|
| vanilla | 0.8346 | 0.8614 | 0.8834 | 0 | 0.007 |
| typed_insys | 0.7990 | 0.8373 | 0.8576 | 0 | 0.010 |
| nl_insys | **0.8983** | 0.9145 | **0.9308** | 0 | 0.005 |
| typed_think_sys | 0.8517 | 0.8863 | 0.8963 | 0 | 0.023 |
| nl_think_sys | 0.8896 | **0.9150** | 0.9245 | 0 | 0.008 |
| typed_prefix_sys | 0.8831 | 0.9131 | 0.9203 | 1 | 0.007 |
| nl_prefix_sys | 0.8849 | 0.9043 | 0.9188 | 0 | 0.007 |

### Paired Δ vs vanilla (prompt-strict)

| condition | Qwen Δ | 95% CI | sig | E4B Δ | 95% CI | sig |
|---|---:|---|---|---:|---|---|
| nl_insys | +0.028 | [+0.001, +0.053] | yes | **+0.064** | [+0.043, +0.084] | yes |
| nl_think_sys | +0.021 | [−0.005, +0.046] | no | **+0.055** | [+0.034, +0.076] | yes |
| nl_prefix_sys | **−0.159** | [−0.190, −0.126] | yes | **+0.050** | [+0.031, +0.070] | yes |
| typed_insys | −0.026 | [−0.052, +0.000] | no | −0.036 | [−0.061, −0.011] | yes |
| typed_think_sys | **−0.042** | [−0.068, −0.015] | yes | +0.017 | [−0.003, +0.037] | no |
| typed_prefix_sys | −0.104 | [−0.133, −0.074] | yes | +0.049 | [+0.028, +0.069] | yes |

### Notation contrast (NL − typed, same placement)

| model | Δ | 95% CI | sig |
|---|---:|---|---|
| Qwen3.5-2B | **+0.063** | [+0.038, +0.087] | yes |
| Gemma E4B | **+0.038** | [+0.022, +0.054] | yes |

### Δ by constraint load (E4B, nl_think_sys vs vanilla)

| constraints in prompt | n | Δ | 95% CI | sig |
|---|---:|---:|---|---|
| 1 | 305 | +0.031 | [+0.007, +0.056] | yes |
| 2 | 179 | **+0.085** | [+0.043, +0.128] | yes |
| 3 | 57 | **+0.088** | [+0.031, +0.158] | yes |

### Δ by constraint family (E4B, nl_think_sys vs vanilla)

| family | n | Δ | 95% CI | sig |
|---|---:|---:|---|---|
| change_case:english_lowercase | 39 | **+0.186** | [+0.096, +0.288] | yes |
| combination:repeat_prompt | 41 | **+0.171** | [+0.061, +0.287] | yes |
| length_constraints:number_sentences | 46 | **+0.125** | [+0.033, +0.223] | yes |
| detectable_format:number_bullet_lists | 31 | **+0.105** | [+0.032, +0.185] | yes |
| length_constraints:number_words | 50 | **+0.095** | [+0.025, +0.175] | yes |
| keywords:frequency | 39 | +0.071 | [−0.013, +0.167] | no |
| keywords:existence | 39 | +0.071 | [−0.006, +0.167] | no |
| keywords:letter_frequency | 33 | +0.068 | [−0.023, +0.167] | no |
| punctuation:no_comma | 66 | +0.061 | [+0.000, +0.133] | no |
| keywords:forbidden_words | 49 | +0.056 | [−0.010, +0.138] | no |
| detectable_content:number_placeholders | 27 | +0.037 | [+0.000, +0.093] | no |
| detectable_format:title | 37 | +0.034 | [−0.007, +0.088] | no |
| detectable_content:postscript | 26 | +0.029 | [−0.019, +0.096] | no |
| startend:end_checker | 26 | +0.029 | [−0.010, +0.087] | no |
| length_constraints:number_paragraphs | 27 | +0.028 | [−0.019, +0.102] | no |
| **language:response_language** | 31 | **+0.000** | [−0.048, +0.048] | no |
| **startend:quotation** | 40 | **+0.000** | [−0.050, +0.044] | no |
| detectable_format:number_highlighted_sections | 48 | −0.036 | [−0.094, +0.016] | no |

---

## 2. E0.2 — binding

**Protocol:** 200 IFEval prompts × 2 samples, concrete cue, three models.
Declaration elicited in the reasoning channel, bounded by `<conventions>…
</conventions>`. Scored against adapter ground truth. Soft cue **not run**.

| model | binding recall (slot-presence) | extra slots/resp |
|---|---:|---:|
| Qwen3.5-2B | 0.485 | 3.90 |
| Gemma E2B | 0.540 | 3.61 |
| Gemma E4B | 0.559 | 3.94 |

**Superseded:** these count a slot as bound on presence alone. The value-aware
recall (a wrong-valued declaration is not bound) is 0.324 / 0.476 / 0.443 — see §10.

### Per-family binding recall

| family | Qwen | E2B | E4B |
|---|---:|---:|---:|
| length_constraints:number_words | 100% | 100% | 98% |
| change_case:english_lowercase | 100% | 100% | 97% |
| length_constraints:number_sentences | 48% | 88% | 86% |
| startend:quotation | 34% | 97% | 78% |
| punctuation:no_comma | 77% | 73% | 52% |
| keywords:frequency | 12% | 59% | 62% |
| keywords:existence | 15% | 24% | 32% |
| keywords:forbidden_words | 3% | 25% | 22% |
| detectable_format:number_highlighted_sections | 6% | 3% | 3% |
| **combination:repeat_prompt** | **0%** | **0%** | **0%** |

### Most-missed slots (count of prompts where required but not declared)

| model | top misses |
|---|---|
| Qwen | must_include 77, wrappers 56, markup 51, forbidden 45, response_boundary 34 |
| E2B | must_include 62, markup 54, forbidden 39, response_boundary 34, wrappers 30 |
| E4B | must_include 57, markup 52, forbidden 49, wrappers 35, response_boundary 34 |

---

## 3. E0.3 — self-consistency

**Protocol:** 60 unconstrained genre prompts × 2 samples per cue per model
(n=120 each). Two-phase: elicit declaration (≤512 tokens, stop at
`</conventions>`), then feed it back and generate the answer.

### Headline — concrete cue, UNTRUNCATED (0021)

| model | self-cons | length median (vs declared) | length_words acc | corr(declared,actual) |
|---|---:|---:|---:|---:|
| Qwen3.5-2B | **0.457** | **−22%** | 0.07 | +0.41 |
| Gemma E2B | **0.439** | **+0.3%** | 0.28 | +0.89 |
| Gemma E4B | **0.529** | **+0.3%** | 0.41 | +0.96 |

*Buffer effect (`>=N` constraints): over-declarers pass 70–87% vs at-target
59–64%. Over-declaring is adaptive, not error.*

Truncated originals (superseded — 24–80% of answers were clipped at 2000 chars):
self-cons 0.468/0.376/0.436, length median −31%/−30%/−29%, length_words acc
0.075/0.125/0.124. Soft-cue metrics remain unreliable (near-empty declarations
for both Gemmas) and are not requoted.

*Soft-cue length figures are unreliable (vague phrasings parse badly) and
soft-cue self-consistency is computed over near-empty declaration sets for both
Gemmas — treat those cells as undefined.*

### Per-slot accuracy (concrete cue — of times declared, how often kept)

| slot | Qwen-2B | E2B | E4B |
|---|---:|---:|---:|
| language | **100%** | **100%** | **100%** |
| case | 80% | 64% | 53% |
| structure | 52% | 81% | 70% |
| length_paragraphs | **10%** | **1%** | **0%** |
| length_words | **7%** | **28%** | **41%** |

*Untruncated (0021). The earlier 7.5/12.5/12.4 for length_words was a
truncation artefact for Gemma — its longer answers were clipped at 2000 chars.
length_paragraphs is genuinely catastrophic on all three; length_words is
Qwen-specific.*
| person | — | 100% (n=6) | 100% (n=1) |
| must_include | 66.7% (n=3) | — | — |

Declaration counts (Qwen): length_words 120, length_paragraphs 120,
structure 115, case 111, language 87.

### Phase-1 budget convergence

| decl-tokens | truncation | slots | coverage |
|---|---:|---:|---:|
| 256 | 3.3% | 4.50 | 0.675 |
| 512 | 3.3% | 4.50 | 0.676 |
| 1024 | 3.3% | 4.50 | 0.683 |

Flat — 512 is sufficient with headroom; the 3.3% residual is budget-independent.

### Qualitative theme inventory (Qwen soft cue, 800 sampled lines)

| theme | share |
|---|---:|
| clarity_simplicity | 19.5% |
| tone_register | 14.1% |
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
| *unthemed* | **48%** |

Sample is the stored `unextracted` field, capped at 8 lines/record — trust
proportions over absolute counts.

---

## 4. Prior inventory (defaults measurement)

**Protocol:** 20 genres × 3 prompts × 3 samples = 180 generations, Qwen3.5-2B,
temp 0.7, max_tokens 1536. 3/180 truncated (excluded from length stats).

| dimension | global median | per-genre range |
|---|---:|---|
| words | 556 | **136 (apology_note) → 820 (story), 6.0×** |
| bullets | 3.5 | 0 in 7 genres (essay, story, poem, email, dialogue, news, apology) → 27 (faq) |
| headers | 4 | 0 for narrative genres → 11 (report) |
| highlights (`**bold**`) | 23.5 | 0 (essay, poem) → 82 (faq) |
| **emoji** | **0** | **0 in 17 genres; review 4, recipe 5, social_post 6** |
| max nesting | 1 (flat) | 3 in faq/howto/recipe |
| has_preamble | 0 | only recipe |

---

## 5. Schema coverage (IFEval, 541 prompts / 834 instruction instances)

| | count | share |
|---|---:|---:|
| typed (has a slot ⇒ has a default ⇒ verifiable) | 799 | **95.8%** |
| partial | 2 | 0.2% |
| untyped (carried in `other`, bound but unverifiable) | 33 | 4.0% |
| **binding coverage** (typed + `other`) | 834 | **100%** |
| prompts fully typed | 506/541 | **93.5%** |

The 33 untyped are all `keywords:letter_frequency` — deliberate Bucket-C exclusion.

**IFBench** (300 prompts, 58 families, 344 instances): 57.3% Bucket C;
schema v2 types 10.5% of all instances, 24.5% of the Bucket-A subset.

---

## 6. Metric parity with IFEval

| metric | samples diffed | mismatches |
|---|---:|---:|
| `count_words` (`\w+` regex tokens) | 412 | **0** |
| `count_sentences` (Punkt) | 412 | **0** |

Corpus: 400 real IFEval prompts + 12 adversarial strings (contractions,
hyphenates, abbreviations, decimals, markdown, unicode).

---

## 7. Degeneracy and validity

### Temperature sweep (Qwen, n=40, duplicated-10-gram rate / % looping)

| temp | vanilla | spec_think | spec_prefix |
|---|---|---|---|
| **0.0** | 0.084 / 10% | **0.213 / 25%** | 0.183 / 20% |
| 0.7 | 0.032 / 2.5% | 0.090 / 10% | 0.072 / 7.5% |
| 0.9 | 0.036 / 5% | 0.072 / 12.5% | 0.000 / 0% |
| **1.0** | 0.004 / 0% | **0.004 / 0%** | 0.037 / 5% |

Greedy decoding produces repetition loops that truncate **asymmetrically**
(20–22% in spec conditions vs 5% vanilla), manufacturing a false negative.
temp 1.0 is the operating point.

### Native thinking mode is unusable via raw completions

`vanilla_think_open` (block left open for the model to close): 77–95% truncation
at every temperature, 48/60 generations never emitting `</think>`. Excluded from
all comparisons as a diagnostic-only condition.

---

## 8. Extractor coverage before/after de-biasing

| model / cue | coverage before → after | slots before → after |
|---|---|---|
| Qwen concrete | 0.656 → **0.691** | 4.47 → 4.67 |
| E2B concrete | 0.427 → **0.481** | 3.62 → 4.09 |
| E4B concrete | 0.414 → **0.555** | 3.13 → **4.16** |
| Qwen soft | 0.115 → **0.184** | 0.93 → 1.63 |
| E2B soft | 0.046 → 0.047 | 0.30 → 0.31 |
| E4B soft | 0.041 → 0.052 | 0.20 → 0.26 |

Six format classes were missing: label-then-value (`Bullet Points: 0`), number
words (`Exactly three paragraphs`), bare language (`English.`), intervening words
(`standard American English capitalization`), negation (`Do not use bullet
points`), and `Language::` double-colons.

---

## 9. Test suite

76 tests, all passing. Coverage: IFEval metric parity, spec parser round-trip,
NL↔typed round-trip, adapter mapping, schema v3 slots, verifier discrimination
(loose ≥ strict, empty never passes), and taxonomy-anchored failure cases
(P.S. recasing, global-vs-per-stanza bullets, delimiter off-by-one,
`correlated`/`correlation` inflection, `engage`/`engages` leakage).

---

## 10. E0.4 — binding, the C2 diagnostic, and the A/B/C triangle

**Protocol:** 300 IFEval prompts × 3 samples × 3 models = 2,700 generations,
concrete cue, immutable runstore (full untruncated text). Binding is **value-aware**
(a slot counts as bound only if the declared value would satisfy the requirement;
"declared 450 for ≥300" is bound, "declared 250" is not).

### Binding recall (value-aware) and the C2 conditional

| model | binding recall | P(pass) | pooled lift | stratified (within-family) lift |
|---|---:|---:|---:|---:|
| Qwen3.5-2B | 0.324 | 0.493 | −0.007 | **+0.102** (10/14 families +) |
| Gemma E2B | 0.476 | 0.822 | +0.021 | +0.005 |
| Gemma E4B | 0.443 | 0.782 | −0.005 | −0.010 |

Pooled conditional is Simpson-confounded (binding rate correlates with family
difficulty); stratify within family. Binding predicts passing only on the weakest
model; the Gemmas are near ceiling.

### Case A/B/C triangle (instruction A / declared B / output C)

| outcome | Qwen | E2B | E4B |
|---|---:|---:|---:|
| A=B=C (declared right, obeyed) | 6% | 59% | 62% |
| A=B, C≠A (declared right, **execution failed**) | 48% | 25% | 29% |
| A≠B (**binding failed**, declared ≠ asked) | 45% | 15% | 9% |

On capable models the dominant failure is **declared-right-executed-wrong**;
binding failure is secondary. The default capturing the declaration (A≠B) is a
weak-model phenomenon.

### Contradicting declarations (declared a value that would NOT satisfy the ask)

| | Qwen | E2B | E4B |
|---|---:|---:|---:|
| declared & correct | 33% | 48% | 45% |
| declared & **contradict** | 13% | 9% | 10% |
| not declared (omission) | 54% | 43% | 45% |
| contradict, as % of DECLARED | **28%** | 17% | 18% |

Contradictions cluster on hard slots (structure, length_sentences, must_include);
`case` contradiction is 15% (Qwen) vs 5% (E4B) — the genuine "default wins the
declaration" signal, weak-model-concentrated. *Caveat:* `structure` contradictions
are partly an adapter representation mismatch (sections vs paragraphs), an upper
bound.

### Length triangle

| | E2B | E4B |
|---|---:|---:|
| declared satisfies A, output satisfies A | 74% | 67% |
| declared satisfies A, output does NOT (execution) | 21% | 17% |
| declared does NOT, output does (slip saved by output) | 5% | 15% |

---

## 11. E4.1 — prior-targeted collision battery

**Protocol:** 80 collision prompts × 3 conditions (vanilla / oracle_declare /
self_declare) × 4 samples × 3 models = 7,680 generations. Override rate = fraction
satisfying the explicit instruction (post-audit checker, 0023).

### Override rates (vanilla / oracle_declare per model)

| prior | Qwen | E2B | E4B |
|---|---|---|---|
| poem_lowercase | 0.98 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| proper_noun_lowercase | 0.90 / 0.78 | 0.85 / 0.90 | 1.00 / 0.93 |
| ps_recase | 0.93 / 0.98 | 0.98 / 0.98 | 1.00 / 0.98 |
| length_2x | 1.00 / 1.00 | 0.97 / 1.00 | 0.99 / 1.00 |
| global_bullets | **0.27** / 0.28 | 0.83 / 0.95 | 0.88 / 0.92 |

4/5 priors near ceiling in vanilla — collisions mostly do not manifest. Qwen
global_bullets (0.27) is **omission** (39/60 write zero bullets), not the
per-stanza prior (2/60).

**Significant surfacing effects (paired bootstrap, post-audit):** global_bullets/E4B
self_declare **+0.100**; ps_recase/Qwen self_declare **−0.133**. Every
`oracle_declare` condition null. (The pre-audit "E2B +0.20" and "E4B −0.15" were
postscript-checker artefacts.)

---

## 12. Contradiction test — is the reasoning-spec causal?

**Protocol:** 15 neutral poem prompts × 6 conditions × 6 samples × 3 models =
1,620 generations. Fraction of outputs all-lowercase / ALL-CAPS.

**Spec alone is causal:** neutral prompt + injected `case: lower` → output
lowercase **0.99–1.00 on all three models** (poems otherwise capitalise). `upper`
follows, bounded by ability to sustain caps (spec_upper_only: E4B 1.00, Qwen 0.58,
E2B 0.43).

**Contradiction resolves by execution difficulty, not authority:** adding a
contradicting `lower` spec halves system=UPPER compliance (E2B 0.94→0.49, E4B
0.99→0.56) but a contradicting `upper` spec does nothing to system=lower (−0.01).
Asymmetry ⇒ directional bias toward the lower-effort form, all three models.

---

## 13. Checker audit (16 agents)

2,880 E4.1 generations sharded 16 ways, independently judged. **Case, length,
bullets: validated** (independently reproduced). **Postscript: systematic blind
spot** — literal `"p.s"` match false-FAILed `ps.`/`ps:`/`ps`/`postscript:`, ~82
disagreements all one-directional false-FAIL. Fixed (`has_postscript`); the bug
had faked two E4.1 results.
