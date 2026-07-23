# Conclusions

Running list of what this project can currently defend, graded by how much weight
each statement bears. Updated as evidence lands; entries move between sections
rather than being deleted, and retractions stay visible.

**Grading**
- **[E] Established** — measured, powered, replicated or verified against ground truth.
- **[S] Suggestive** — measured but single-model, underpowered, or confounded.
- **[U] Untested** — asserted by the design, not yet evidenced.
- **[R] Retracted** — previously claimed, since disproved.

---

## 1. The interface: notation and placement

**[E] A typed `<spec>` DSL underperforms plain English carrying identical
constraints, by 4–6 points of prompt-strict accuracy.**
Within the reasoning-channel placement, holding constraints, placement and system
prompt fixed and varying only the rendering: Qwen3.5-2B **+0.063** [+0.038,
+0.087], Gemma 4 E4B **+0.038** [+0.022, +0.054]. 541 prompts × 4 samples, paired
bootstrap. Two families, two scales, both CIs excluding zero. *(0014)*

**[E] The proposal's actual interface — a typed spec in the reasoning channel —
clears Gate 1 on neither model.** +0.017 (ns) on Gemma, **−0.042** (significantly
negative) on Qwen. Handing a 2B model a perfect machine-readable spec makes it
follow constraints *worse than saying nothing*. *(0014)*

**[E] Placement effects reverse between models.** Spec in the visible response
body: Gemma **+0.050**, Qwen **−0.159**. Both significant, and the largest
effects measured. No claim about where the spec should live generalises. *(0014)*

**[S] Whether surfacing helps at all is model-dependent.** Plain-English spec in
the reasoning channel: Gemma **+0.055** (clears the ≥+0.05 proceed threshold),
Qwen **+0.021** (ns, on the falsification line). Reads as a capability floor, but
size and family are confounded — Gemma 4 E2B is the control that separates them
and has not yet run. *(0014)*

**[E] Natural language is the right rendering for the model.** Direct consequence
of the above; adopted as the project's working interface. The typed form is
retained only as a *derived* artifact for verification (see §5).

---

## 2. The mechanism: does surfacing work the way the thesis says?

**[E] The benefit scales with constraint load.** Gemma, Δ vs vanilla by number of
constraints in the prompt: 1 → **+0.031**, 2 → **+0.085**, 3 → **+0.088**, all
significant. Monotonic, and 1→2 nearly triples it. Supports *binding* (getting
constraints registered) as the operative mechanism. Qwen shows no gradient. *(0014)*

**[E] Surfacing helps exactly the constraint families with a latent default, and
does nothing for families without one.** On Gemma, families that move:
`change_case:english_lowercase` **+0.186**, `combination:repeat_prompt` +0.171,
`length_constraints:number_sentences` +0.125, `number_bullet_lists` +0.105,
`number_words` +0.095. Families that do not: `language:response_language`
**+0.000**, `startend:quotation` **+0.000**, `number_highlighted_sections` −0.036.

This is the single strongest result in the project. Case, length and structure
are precisely the taxonomy's A1–A3 latent-default families; language and
quotation have no absorbed prior to override. The split is a *mechanism
confirmation*, not just an effect size, and it corroborates a taxonomy built on
a different model. *(0014)*

---

## 3. Latent defaults exist and are genre-conditioned

**[E] Defaults are strongly genre-conditioned, and global aggregates conceal
them.** Qwen3.5-2B emoji usage has a global median of **0**, which reads as "no
prior at all", yet emoji appear in **8 of 20 genres** and are the norm in social
posts (median 6) and recipes (median 5). Fitting defaults globally would have
concluded the dimension does not exist. *(0010)*

**[E] The genre natural-length prior reproduces on a new model.** Qwen3.5-2B word
counts span **6×** across genres — 136 (apology note) to 818 (report) — on
prompts that specify no length. This is the A1 prior the taxonomy identified on
Gemma 4 E4B, now measured independently. *(0010)*

**[E] Schema membership is decidable empirically.** A dimension earns a typed
slot iff the model exhibits a stable prior on it. By that test **emoji** and
**nesting depth** qualify (nesting median 3 in faq/howto/recipe, 0–1 elsewhere);
**indentation** does not (0 everywhere, no variation). *(0010)*

**[S] `response_boundary` is nearly irrelevant for Qwen3.5-2B.** Preamble present
in only 1 of 20 genres (recipes). The slot was designed around Gemma's
inline-thinking pollution and should not be a headline mechanism here. *(0010)*

---

## 4. Schema coverage

**[E] Schema v2 (15 slots) expresses 95.8% of IFEval instruction instances and
93.5% of prompts fully.** The only deliberate exclusion is letter-level
arithmetic (Bucket C). *(0007)*

**[E] Low IFBench coverage is a fact about IFBench, not a defect in the schema.**
57.3% of IFBench is Bucket C (palindromes, prime word lengths, syllable parity,
stop-word ratios). The schema is an inventory of *default-bearing dimensions*,
not a universal constraint language, so predicates with no latent default
correctly fall outside it. *(0008, corrected by 0009)*

**[E] A slot exists iff its dimension carries a latent default.** Constraints
without defaults are carried in `other`, which can only ever be `[given]` —
an `[assumed]` entry there is a category error, rejected by both validator and
parser. *(0009)*

---

## 5. Design decisions this evidence forces

**[E] Phase 1 needs a natural-language-spec arm.** The design's controls
(no-spec / free-form-plan / untyped-spec) cannot separate "typing helps" from
"structure helps". Without an NL-structured arm, C1 is untestable.

**[E] Gate 1 is conditionally passed, not cleanly.** Passed for the *mechanism*
(NL surfacing on Gemma), failed for the *proposed interface* (typed, either
model). Proceed with C1's representation as an open question rather than a
premise.

**[U] Hybrid: NL spec emitted by the model, typed spec derived from it for the
verifier.** Keeps `R_exec` mechanical without making the model parse or produce a
DSL. This is the current preferred design and its feasibility rests on an
NL→typed extractor that has not been built.

**[E] The typed-vs-NL result does not kill C1.** The tax is measured on models
that have never seen the format; C1's premise is that typing buys
machine-verifiability. That trade can only be evaluated after training. The bar
is now concrete: typed must recover **+0.038 (Gemma) / +0.063 (Qwen)** merely to
match plain English.

---

## 6. Methodology — hard-won and non-negotiable

**[E] Greedy decoding is invalid for these models.** At temperature 0, Qwen3.5-2B
enters verbatim repetition loops that exhaust the token budget, and it does so
*asymmetrically* — 20–22% truncation in spec conditions vs 5% vanilla —
manufacturing a fake negative result. temp 1.0 gives ~0% looping. *(0011, 0012)*

**[E] Single-sample runs are not measurements.** Identical configurations re-run
at temp 1.0 moved every condition by **0.02–0.07**, larger than the effects under
test. Multiple samples per prompt plus paired bootstrap CIs are mandatory. *(0013)*

**[E] Truncation is a validity gate.** A condition that exhausts its budget scores
near zero for reasons unrelated to instruction following; unbalanced truncation
across conditions invalidates the comparison outright.

**[E] Generated datasets must be integrity-checked before analysis.** A silent
`pkill` failure let two processes interleave writes into one file, producing a
corrupted 22,301-row dataset that would otherwise have been analysed. Check row
counts, per-condition counts and duplicate keys every time. *(0014)*

**[E] "First N" is not a sample.** The first 400 IFEval rows are measurably
skewed — `language` ~3× underrepresented, `startend` ~2× over. Use the full set
or sample randomly. *(0014)*

**[E] Verifier metrics must match the benchmark's, measured not assumed.** IFEval
counts `\w+` regex tokens (not whitespace) and uses the Punkt tokenizer (not a
`.?!` split). Both corrections came from reading its source; parity is now pinned
by measurement on 412 samples with zero mismatches. *(0004, 0005)*

---

## 7. Retractions

**[R] "Oracle prefill gives +0.11, Gate 1 passes."** *(0012, retracted in 0013)*
Single-sample n=100; did not replicate. The corrected estimate for the same
condition is ~+0.02 and not significant.

**[R] "Our schema is overfit to IFEval / Gate 3 is unwinnable."** *(0008,
retracted in 0009)* Rested on treating the typed schema as a universal constraint
language. Low IFBench coverage is expected and correct.

**[R] "Qwen's separate reasoning channel avoids inline-thinking pollution."**
*(0001/0010, corrected in 0011)* True only via the chat API. Prefilling through
raw completions reintroduces exactly the Gemma artifact.

**[R] "Gemma 4 E4B has no reasoning channel."** *(0013, corrected in 0014)* It
does — `<|channel>thought … <channel|>`, enabled by `<|think|>` in the system
prompt. A capability probe that only looked for `<think>` wrongly excluded
Gemma's strongest condition.

---

## 7b. Self-consistency: the model does not obey its own declarations

**[E] Asked for concrete values, the model reliably declares its defaults.**
Qwen3.5-2B: 0% no-declaration rate, **4.5 slots per response**, on prompts that
constrain nothing. It commits to a word count, paragraph count, structure, casing
and language unprompted. *(0015)*

**[E] It then satisfies only about 40% of what it declared — robust across three
models.** Recomputed with the de-biased extractor: Qwen3.5-2B **0.468**, Gemma
E2B **0.376**, Gemma E4B **0.436**. Quote as **~0.4**, not ~0.5. Perfect
compliance is ~0: not one response in 120 fully honours its own declaration on
Qwen or E2B. *(0019)* Two families, three models, two parameter
classes, all near one another. Perfect-compliance rate 0.8% (Qwen) and 6.5% (E4B). The
design gates the RLVR work here (">95% would mean no signal"); at ~0.5 the
headroom is large on both models, on dimensions nobody asked about.
*(0015, 0016, E4B run)*

**[S] The soft cue is a Qwen phenomenon and its inventory does not generalise.**
No-declaration under the soft cue: Qwen 0.34, Gemma E2B **0.71**, Gemma E4B
**0.80**; qualitative lines/response 11.6 / 5.8 / 4.4. Both Gemmas mostly decline
to declare at all, so the theme inventory (clarity 19.5%, tone 14.1%, the
content-policy discovery) describes **one model's** convention vocabulary.
*(0017)*

**[R] "Extraction coverage measures the model."** It measured our instrument.
The regexes were **format-biased**: Gemma writes `Bullet Points: 0`,
`Paragraph count: 4`, `Exactly three paragraphs` (label-then-value, and number
words), where the patterns only knew prose-with-digits. Fixing six such classes
moved E4B coverage 0.414 → **0.555** and slots 3.13 → **4.16**. *(0018)*

**[R] "The bigger model declares less, not more."** Largely an artefact of the
same bias. Slots per response after the fix: **4.67 / 4.09 / 4.16** (Qwen / E2B /
E4B) against 4.47 / 3.62 / 3.13 before — the gap shrank ~60%. All three models
declare roughly the same number of conventions. *(0018)*

**[S] Residual coverage gap, now smaller.** 0.66
(Qwen) vs 0.43 / 0.41 (Gemma). The extractor's patterns were written by reading
Qwen declarations, so the gap is plausibly our bias. Do not quote coverage as a
model property until the extractor is tuned symmetrically. *(0017)*

**[E] A liveness check must identify the specific process, not the class.**
`pkill -f "vllm serve"` over SSH matched its own command string and killed the
shell; `pgrep -f "vllm serve"` then matched *other* running servers, so a server
that never started was reported as "still loading" for ~12 hours. Kill by PID,
check a port-specific pattern plus log freshness. *(0017)*

**[E] The bigger model declares less, not more.** E4B: 3.13 slots/response, 11%
no-declaration, 0.41 extraction coverage. Qwen-2B: 4.47 slots, 0% no-declaration,
0.66 coverage. And the **soft cue largely fails on E4B** — 80% no-declaration
against Qwen's 34% — so the qualitative inventory is Qwen-weighted and should not
be generalised. *(E4B run)* Mean self-consistency
**0.471**, median 0.5, and only **1 response in 120** fully honoured its own
declaration. The design gates the RLVR work on this exact number (">95% would
mean the signal is thin"); at 47% the headroom is very large, on dimensions
nobody asked about. *(0015)*

**[E] The violation profile is an execution-difficulty ordering.**
length_words **94.2%** violated, length_paragraphs **85.8%**, structure 37.5%,
case 18.3%. Global-count dimensions fail almost always; locally-checkable ones
rarely. This reproduces the taxonomy's A1 finding in a sharper form — the failure
cannot be blamed on misreading an instruction, because the model authored the
target itself one turn earlier. *(0015)*

**[E] The model's natural convention vocabulary is stylistic, not metric.** Under
a soft cue it declares "be clear and direct", "keep sentences relatively short" —
genuine defaults, but nothing a verifier can score (2% extraction coverage). Only
an explicit request for specific values yields checkable declarations (67%). A
trained model would have to close that gap. *(0015)*

## 7c. The qualitative half of the defaults

**[R] "The model systematically under-produces against its own declared length."**
**SUPERSEDED TWICE — final answer: the underproduction is UNIVERSAL.** With the
de-biased extractor, all three models underproduce against their own declared
length by ~30% (Qwen −31%, Gemma E2B −30%, Gemma E4B −29%) with 79–90% under
target. The earlier "Gemma is well-calibrated at −1%" was a **selection
artefact**: the extractor could not parse Gemma's `Paragraph count: 4` format, so
it measured only the well-behaved prose-formatted minority. Neither family nor
size matters here. *(0019)*

Superseded intermediate claim, kept visible: "it is a FAMILY effect, not
a size effect." Holding size constant at ~2B, Qwen misses by **−26%** while
**Gemma E2B misses by −5%** — a 5× difference from family alone. Holding family
constant, Gemma E2B −5% → E4B −1% is a further modest size gain. So "a 2B model
cannot hit a self-set length" was wrong; *Qwen's* 2B cannot. Gemma 4 E4B −1% with
54% under target — i.e.
E4B hits its own declared length essentially on the nose. The underproduction is
**Qwen-2B-specific, not a general property**, and my earlier framing of it as "the
cleanest A1 result available" was wrong. Consistent with the capability-floor
reading from E0.1: the 4B model can hit a self-set length target, the 2B cannot.
*(0015, 0016; corrected by E4B run)*
Median relative error **−26.0%**, **74%** of responses under target, p10 −53%.
The taxonomy found 10–15% short against *externally imposed* targets; against
self-declared targets it is worse. The failure cannot be misreading, because the
model wrote the target itself one turn earlier — what is missing is a
count→gap→extend loop, not comprehension. *(0016)*

**[E] The cue determines which kind of default is elicited, and the trade is
sharp.** Concrete cue: 4.5 typed slots/response, 0.66 extraction coverage, 3.6
qualitative lines. Soft cue: 0.9 typed slots, 0.11 coverage, **11.5 qualitative
lines**. Asking for numbers suppresses the stylistic vocabulary and vice versa.
**The model's natural declaration is qualitative**; quantification must be
demanded. *(0016)*

**[E] The qualitative half is the majority of what the model declares, and it is
at least eight distinct dimensions.** By share of soft-cue lines:
clarity/simplicity **19.5%**, tone/register **14.1%**, narrative structure 8.5%,
formatting style 6.2%, then content inclusion/exclusion, grammar, person,
factuality, safety, audience, engagement. *(0016)*

**[E] The model carries a self-imposed content policy as a latent default.**
Unprompted, it declares "no external links", "no personal anecdotes", "no
advertising", "no political statements", "no religious references", "no
controversial content" — a standing editorial policy applied to every response,
with **no slot in the schema**. *(0016)*

**[E] The `register` slot is badly under-specified.** One soft judge-only slot is
allocated to a qualitative half that is most of the declared volume and at least
eight dimensions wide. "register: playful" cannot represent "third person, no
jargon, no political content, ends with a call to action". *(0016)*

**[E] Phase-1 declaration budget is empirically sufficient at 512 tokens.**
Sweeping 256 / 512 / 1024 leaves slots declared unchanged (4.50 / 4.50 / 4.50)
and coverage within 1pp (0.675 / 0.676 / 0.683). The declaration distribution has
converged, so declarations are not being silently clipped. The 3.3% residual
truncation is constant across all three budgets, so it is not budget-related.
**This is the right way to size any elicitation window: raise it until the
distribution stops moving.**

**[E] Schema v3 implements the register decomposition and a content-policy slot.**
`register` split into `person` (PROGRAMMATIC — pronoun scan), `tone`,
`jargon_level`, `audience` (judge) plus a catch-all remainder. `content_policy`
added for the surface-checkable rules (no_urls / no_emoji / no_profanity /
no_first_person, all programmatic) with semantic rules routed to a separate
judge-only `content_rules` slot — scored and unscored predicates are never mixed
in one slot, which was `register`'s original defect.

**[S] The decomposition helps, but does not solve extraction coverage.**
Re-extracting the stored declarations: Qwen soft **0.115 → 0.170** (+48%
relative), Qwen concrete 0.656 → 0.657 (nil), E4B concrete 0.414 → 0.425. The new
slots fire 69 times across 120 Qwen soft-cue responses (tone 19, content_policy
15, jargon_level 14, person 12, content_rules 6, audience 3) — real signal that
was previously invisible, but **83% of soft-cue lines still fail to type**. The
bottleneck is now the narrowness of the tone/jargon/audience patterns, not the
absence of slots.

## 7d. Binding and execution fail on *different* families — C2's premise, measured

**[E] About half of stated constraints never reach the declaration.** Binding
recall: Qwen **0.485**, Gemma E2B **0.540**, Gemma E4B **0.559** (200 IFEval
prompts × 2 samples). This is the taxonomy's "never registered" failure,
quantified. *(0018)*

**[E] Binding failure is concentrated in dimensions with no latent default.**
Always registered: word count, lowercase (97–100%). Almost never: keyword
requirements (3–32%), highlight counts (3–6%), and `combination:repeat_prompt`
at **0.0% on all three models**. Constraints that land on a default-bearing
dimension get registered; ones that introduce a dimension the model has no prior
about get dropped — the default-inventory logic showing up in binding. *(0018)*

**[E] Per-slot execution is an identical difficulty gradient on all three models.**
language **100%** everywhere → case 49–83% → structure 42–57% → length **7–16%**.
The ordering tracks one thing: whether honouring the convention requires holding
a *count* while generating. Not comprehension, not family, not scale. *(0018)*

**[E] Length is the cleanest existence proof for the binding/execution split.**
Binding on length is near-perfect (98–100% recall) while execution is ~10%. The
model registers the constraint flawlessly and then misses it. A monolithic reward
cannot separate those; C2's two rewards can. *(0018)*

**[E] Median and in-window accuracy must both be reported for length.** E4B is
*unbiased but imprecise* (median −1%, in-window 12.4%); Qwen is *biased and
imprecise* (−26%, 7.5%). Either statistic alone misleads. *(0018)*

**[E] "Precision" is not meaningful for binding here.** Models declare 3.6–3.9
slots beyond those required — those are `[assumed]` conventions on open
dimensions, which is the point of the project, not error. *(0018)*

**[E] A failing instrument produces biased data, not noisy data.** The extractor
silently dropped Gemma's declaration format, so the surviving sample was the
well-behaved tail — which read as "Gemma is well calibrated" for two full
write-ups. Inputs an instrument fails on are rarely a random sample. *(0019)*

**[E] When the instrument changes, every stored number is stale.** Comparing a
fresh measurement to a frozen run summary mixes two instruments. Metrics are now
re-derived from stored raw generations by `scripts/recompute_e03.py`; run outputs
are raw data plus a snapshot, never the authoritative metric. *(0019)*

**[E] A metric computed over a near-empty declaration set is undefined, not high.**
Gemma E4B's reported soft-cue self-consistency of 0.667 was computed over ~0.2
slots per response — it "kept" its declarations by barely making any. With better
extraction it is 0.160. *(0019)*

## 8. The largest open gap

**[R] "No `[assumed]` slot has ever been tested."** Closed by 0015 — see §7b.
The gap that remains is narrower: `[assumed]` behaviour is now measured on
*unconstrained* prompts, but not yet in a setting where a declared default and an
explicit instruction directly collide (the prior-targeted battery, E4.1).

**[E] E0.1's results specifically remain `[given]`-only.** All 832 oracle slots across 541
prompts are `[given]`, mean **1.54 slots per prompt**, 56% of prompts getting a
single line. Everything measured so far concerns *restating explicit
constraints*. The latent-defaults mechanism — the actual contribution — remains
untested, and no Gate 1 verdict on H0 should be drawn from the E0.1 results.

The two experiments that would close it: **E0.3** (model declares its own
conventions, then is checked against its own declaration) and the
**prior-targeted battery** (E4.1), where a declared default and an explicit
instruction are built to collide.
