# Conclusions

What this project can currently defend, graded by how much weight each statement
bears. Rewritten 2026-07-22 after the extractor de-biasing (0018) and the
universal-underproduction correction (0019) invalidated several earlier entries.

**Grading**
- **[E] Established** — measured, powered, replicated across models or verified against ground truth.
- **[S] Suggestive** — measured but single-model, underpowered, or confounded.
- **[U] Untested** — asserted by the design, not yet evidenced.

Retractions live in §9, not inline, so no claim appears twice.

**All numbers below are post-fix.** Metrics are re-derived from stored raw
generations via `scripts/recompute_e03.py` and `analyze_e0*.py`; the `data/*.json`
run summaries hold pre-fix values and should not be quoted.

---

## 1. Headline

**[E] Models declare their conventions readily, and then obey about 40% of them.**
Self-consistency on unconstrained prompts: Qwen3.5-2B **0.468**, Gemma E2B
**0.376**, Gemma E4B **0.436**. Perfect compliance is ~0 — not one response in 120
fully honours its own declaration on Qwen or E2B. Three models, two families, two
parameter classes.

**[E] Half to two-thirds of stated constraints are never *correctly* registered.** Value-aware binding recall: **0.324 / 0.476 / 0.443** (Qwen / E2B / E4B). The earlier 0.485/0.540/0.559 scored a slot as bound regardless of its value, and **33.5% of those carried the wrong value** — a prompt asking for 300 words against a declaration saying 450. *(0020)*

Together these are the project's central empirical claim: **there is a large,
trainable gap on both stages, and it exists on dimensions nobody asked about.**
The design gates RLVR on self-consistency being below ~95%; at ~0.4 the headroom
is not marginal.

---

## 2. The interface: notation and placement (E0.1)

541 IFEval prompts × 4 samples × 7 conditions, Qwen3.5-2B and Gemma 4 E4B.
*(E0.1 was never run on E2B.)*

**[E] A typed `<spec>` DSL underperforms plain English carrying identical
constraints by 4–6 points.** Holding constraints, placement and system prompt
fixed and varying only the rendering: Qwen **+0.063** [+0.038, +0.087], E4B
**+0.038** [+0.022, +0.054]. *(0014)*

**[E] The proposal's actual interface — a typed spec in the reasoning channel —
clears Gate 1 on neither model.** +0.017 (ns) on E4B, **−0.042** (significantly
negative) on Qwen. Handing a 2B model a perfect machine-readable spec makes it
follow constraints *worse than saying nothing*. *(0014)*

**[E] Placement effects reverse between models.** Spec in the visible response
body: E4B **+0.050**, Qwen **−0.159**. Both significant, and the largest effects
measured. No claim about where the spec should live generalises. *(0014)*

**[S] Whether surfacing helps at all is model-dependent.** NL spec in the
reasoning channel: E4B **+0.055** (clears the ≥+0.05 threshold), Qwen **+0.021**
(ns). Confounded — E0.1 has not been run on E2B, so the size/family control that
worked for E0.3 does not exist here. *(0014)*

**[E] Natural language is the working interface.** Adopted as a consequence of the
above; the typed form is retained only as a *derived* artefact for verification.

---

## 3. Binding and execution fail on different families — C2's premise, measured

200 IFEval prompts × 2 samples (binding); 60 genre prompts × 2 (execution).
Three models.

**[E] Binding failure is concentrated in dimensions with no latent default.**
Always registered: word count, lowercase (**97–100%**). Almost never: keyword
requirements (3–32%), highlight counts (3–6%), `combination:repeat_prompt` at
**0.0% on all three models**. Constraints landing on a default-bearing dimension
get registered; ones introducing a dimension the model has no prior about get
dropped. *(0018)*

**[E] Per-slot execution is an identical difficulty gradient on all three models.**

| slot | Qwen-2B | E2B | E4B |
|---|---:|---:|---:|
| language | **100%** | **100%** | **100%** |
| case | 82.9% | 61.5% | 48.5% |
| structure | 49.6% | 56.8% | 42.0% |
| length_paragraphs | 12.5% | 12.1% | 16.3% |
| length_words | **7.5%** | 12.5% | 12.4% |

The ordering tracks exactly one thing: **whether honouring the convention
requires holding a running count while generating.** Not comprehension, not
family, not scale. *(0018)*

**[E] Length is the cleanest existence proof for the factorization.** Binding on
length is near-perfect (98–100%) while execution is ~10%. The model registers the
constraint flawlessly and then misses it. A monolithic reward cannot separate
those; C2's two rewards can. *(0018)*

**[E] Length underproduction is universal.** All three models undershoot their
*own* declared word count: Qwen **−31%**, E2B **−30%**, E4B **−29%**, with 79–90%
of responses under target. Neither family nor size matters. This is the missing
count→gap→extend loop, and it agrees with the per-slot gradient above. *(0019)*

**[E] "Precision" is not a meaningful binding metric here.** Models declare 3.6–3.9
slots beyond those required; those are `[assumed]` conventions on open dimensions
— the point of the project, not error. *(0018)*

---

## 3b. E0.4 — does binding predict passing?

**[E] Binding must be value-aware, and this inverted a headline.** Scoring a slot
as bound on presence alone made binding *negatively* associated with passing on
E4B (lift −0.105), because "bound" was contaminated with "bound to the wrong
target", which then fails execution. *(0020)*

**[E] The pooled conditional is Simpson-confounded.** Binding rate correlates with
family difficulty: families almost never bound (`postscript` 0.02, `end_checker`
0.00) pass at 0.93–1.00 *without* binding because they are satisfied by default.
Stratify within family or the effect cancels. *(0020)*

**[S] Correct binding predicts passing on the weakest model only.** Stratified
within-family lift: Qwen **+0.102** (10/14 families positive), E2B +0.005,
E4B −0.010. Likely a ceiling effect — the Gemmas satisfy ~80% of constraints
regardless of declaration, leaving little variance for binding to explain. *(0020)*

**[U] E0.4 does not settle C2.** The stages are separable in principle and
measurable in practice, but the causal claim — that fixing binding fixes
compliance — appears only on the weakest model and is correlational even there.
Binding and passing may share a cause: the model simply understood the
constraint. *(0020)*

## 4. The `[assumed]` half: what models volunteer unasked

**[E] Asked for concrete values, models reliably declare defaults.** No-declaration
rate 0.00 / 0.00 / 0.09; **4.7 / 4.1 / 4.2 slots per response** on prompts that
constrain nothing. They commit to word count, paragraph count, structure, casing
and language unprompted. *(0015, 0018)*

**[E] The cue determines which kind of default is elicited, and the trade is
sharp.** Concrete cue (Qwen): 4.67 typed slots, 0.691 coverage, 3.3 qualitative
lines. Soft cue: 1.63 slots, 0.184 coverage, **10.5 qualitative lines**. Asking
for numbers suppresses the stylistic vocabulary and vice versa. **The model's
natural declaration is qualitative**; quantification must be demanded. *(0016, 0019)*

**[S] The soft cue is largely a Qwen phenomenon.** No-declaration under soft:
Qwen 0.18, E2B **0.70**, E4B **0.76**. Both Gemmas mostly decline to declare, so
the qualitative theme inventory describes one model's vocabulary and should not be
generalised. *(0017, 0019)*

**[S] The qualitative half is at least eight distinct dimensions.** By share of
Qwen soft-cue lines: clarity/simplicity 19.5%, tone/register 14.1%, narrative
structure 8.5%, formatting 6.2%, then content inclusion/exclusion, grammar,
person, factuality, safety, audience, engagement. ~48% unthemed, so these are
lower bounds. *(0016)*

**[S] Models carry a self-imposed content policy as a latent default.** Unprompted:
"no external links", "no personal anecdotes", "no advertising", "no political
statements", "no religious references", "no controversial content" — a standing
editorial policy applied to every response. Qwen-weighted evidence. *(0016)*

---

## 5. Latent defaults are real and genre-conditioned

**[E] Defaults are strongly genre-conditioned, and global aggregates conceal
them.** Qwen emoji usage has a global median of **0** — reading as "no prior at
all" — yet emoji appear in **8 of 20 genres** and are the norm in social posts
(median 6) and recipes (median 5). *(0010)*

**[E] The genre natural-length prior reproduces on a new model.** Qwen word counts
span **6×** across genres, 136 (apology note) to 818 (report), on prompts
specifying no length. This is the taxonomy's A1 prior, measured independently. *(0010)*

**[E] Schema membership is decidable empirically.** A dimension earns a typed slot
iff the model shows a stable prior on it. By that test **emoji** and **nesting
depth** qualify; **indentation** does not. *(0010)*

**[S] `response_boundary` is nearly irrelevant for Qwen.** Preamble present in
1 of 20 genres. Designed around Gemma's inline-thinking pollution; not a headline
mechanism here. *(0010)*

---

## 6. Schema

**[E] Schema v2 (15 slots) expresses 95.8% of IFEval instruction instances and
93.5% of prompts fully.** Only deliberate exclusion is letter-level arithmetic
(Bucket C). *(0007)*

**[E] Low IFBench coverage is a fact about IFBench, not a defect.** 57.3% of
IFBench is Bucket C. The schema is an inventory of *default-bearing dimensions*,
not a universal constraint language. *(0008, 0009)*

**[E] A slot exists iff its dimension carries a latent default.** Constraints
without defaults go in `other`, which can only ever be `[given]` — an `[assumed]`
entry there is a category error, rejected by validator and parser. *(0009)*

**[E] Schema v3 decomposes `register` and adds `content_policy`.** `register` →
`person` (**programmatic**, pronoun scan), `tone`, `jargon_level`, `audience`
(judge) + catch-all remainder. `content_policy` covers surface-checkable rules
(no_urls / no_emoji / no_profanity / no_first_person, programmatic); semantic
rules go to a separate judge-only `content_rules` slot, because mixing scored and
unscored predicates in one slot was `register`'s original defect. *(0018)*

**[S] The decomposition captures real signal but does not solve coverage.** Post-fix
coverage: Qwen 0.691, E2B 0.481, E4B 0.555 on the concrete cue; soft-cue coverage
remains ~0.05–0.18. The bottleneck is now pattern narrowness, not missing slots. *(0018)*

---

## 7. Design decisions this evidence forces

**[E] Phase 1 needs a natural-language-spec arm.** The design's controls
(no-spec / free-form-plan / untyped-spec) cannot separate "typing helps" from
"structure helps".

**[E] Gate 1 is conditionally passed, not cleanly.** Passed for the *mechanism*
(NL surfacing on E4B), failed for the *proposed interface* (typed, either model).

**[E] The typed-vs-NL result does not kill C1.** The tax is measured on models
that have never seen the format; C1's premise is that typing buys
machine-verifiability, and that trade can only be evaluated after training. The
bar is concrete: typed must recover **+0.038 (E4B) / +0.063 (Qwen)** merely to
match plain English.

**[E] The hybrid is built and working.** `spec_extract` derives a typed `Spec`
from plain English, rule-based so it is deterministic and free at reward time,
with uncovered lines reported rather than silently counted as satisfied.

---

## 8. Methodology — hard-won, non-negotiable

**[E] Greedy decoding is invalid for these models.** At temperature 0 Qwen enters
verbatim repetition loops, *asymmetrically* — 20–22% truncation in spec conditions
vs 5% vanilla — manufacturing a fake negative result. temp 1.0 gives ~0% looping. *(0011, 0012)*

**[E] Single-sample runs are not measurements.** Identical configs re-run moved
every condition by 0.02–0.07, larger than the effects under test. Multiple samples
plus paired bootstrap CIs are mandatory. *(0013)*

**[E] A failing instrument produces biased data, not noisy data.** The extractor
silently dropped Gemma's declaration format, so the surviving sample was the
well-behaved tail — which read as "Gemma is well calibrated" across two write-ups.
Inputs an instrument fails on are rarely a random sample. *(0019)*

**[E] When the instrument changes, every stored number is stale.** Metrics must be
re-derived from stored raw generations; run outputs are raw data plus a snapshot,
never the authoritative metric. *(0019)*

**[E] A metric computed over a near-empty declaration set is undefined, not high.**
E4B's soft-cue self-consistency of 0.667 was computed over ~0.2 slots per
response. Correctly measured: 0.160. *(0019)*

**[E] Truncation is a validity gate.** Unbalanced truncation across conditions
invalidates a comparison outright.

**[E] Size an elicitation window by convergence.** Sweeping the phase-1 budget
256/512/1024 left slots declared at 4.50 throughout and coverage within 1pp —
raise it until the distribution stops moving. *(0016)*

**[E] Generated datasets must be integrity-checked before analysis.** A silent
`pkill` failure let two processes interleave writes, producing a corrupted
22,301-row dataset. Check row counts, per-condition counts, duplicate keys. *(0014)*

**[E] A liveness check must identify the specific process, not the class.**
`pkill -f "vllm serve"` over SSH matched its own command string; `pgrep -f "vllm
serve"` then matched *other* servers, so a server that never started was reported
as "loading" for ~12 hours. Kill by PID, check a port-specific pattern plus log
freshness. *(0017)*

**[E] "First N" is not a sample.** The first 400 IFEval rows are skewed —
`language` ~3× underrepresented, `startend` ~2× over. *(0014)*

**[E] Verifier metrics must match the benchmark's, measured not assumed.** IFEval
counts `\w+` regex tokens (not whitespace) and uses Punkt (not a `.?!` split).
Parity pinned by measurement on 412 samples, zero mismatches. *(0004, 0005)*

---

## 9. Retractions

Kept visible; none of these should be cited as current.

| claim | why it fell | where |
|---|---|---|
| "Oracle prefill gives +0.11, Gate 1 passes" | single-sample n=100, did not replicate | 0012 → 0013 |
| "Our schema is overfit to IFEval / Gate 3 unwinnable" | treated the schema as a universal constraint language | 0008 → 0009 |
| "Qwen's reasoning channel avoids inline-thinking pollution" | true only via the chat API; raw completions reintroduce it | 0001/0010 → 0011 |
| "Gemma 4 E4B has no reasoning channel" | it has `<\|channel>thought … <channel\|>` | 0013 → 0014 |
| "Extraction coverage measures the model" | it measured our format-biased regexes | 0017 → 0018 |
| "The bigger model declares less, not more" | artefact of the same bias; slots are 4.67/4.09/4.16 | 0017 → 0018 |
| "Underproduction is Qwen-specific" | universal, ~30% on all three | 0016 → 0019 |
| "Underproduction is a family effect, not size" | neither; the E2B control was fed biased data | 0017 → 0019 |
| "No `[assumed]` slot has ever been tested" | closed by E0.3 | 0015 |

---

## 10. Open gaps

**[U] The defaults mechanism has never been tested in collision.** `[assumed]`
behaviour is measured on *unconstrained* prompts, but not where a declared default
and an explicit instruction directly conflict. That is the prior-targeted battery
(E4.1) and it remains the sharpest untested claim.

**[E] E0.1's oracle specs are `[given]`-only.** 832 slots across 541 prompts, mean
**1.54 per prompt**, 56% of prompts getting a single line. E0.1 measures
*restating explicit constraints*, so **no Gate 1 verdict on H0 should be drawn
from it**.

**[U] E0.4 is blocked, not merely unstarted.** The E0.2 runner records binding but
does not score the answer, so P(pass | bind✓) cannot be computed. Smallest
remaining gap in Phase 0.

**[U] `repeat_prompt` binds at 0.0% on all three models** — plausibly an adapter
slot-mapping artefact (`response_boundary`) rather than a real failure. Unverified.

**[U] E0.2 has never been run with the soft cue**, so it is unknown whether
qualitative conventions get bound from prompts that request them.

**[U] E0.1 has never been run on E2B**, so its model-dependence result lacks the
size/family control that E0.3 has.
