# 0024 — Contradiction test: is the reasoning-spec a causal control surface?

**Date:** 2026-07-23
**Runs:** `contra-qwen`, `contra-e2b`, `contra-e4b` — 15 neutral poem prompts ×
6 conditions × 6 samples × 3 models = 1,620 generations.

## Why this exists (E4.1 was the wrong test)

E4.1 surfaced the *same* constraint already in the user prompt, so its
near-ceiling compliance only showed the models obey explicit instructions — it
could not tell whether the reasoning-injected spec had any causal power of its
own. This isolates that power two ways: (a) inject a case-spec on a **neutral**
prompt that never mentions case, and (b) make the spec **contradict** a standing
system rule and see which the output follows.

Dimension: case (all-lowercase vs ALL-CAPS, unambiguously checkable). Fraction of
outputs in each form, per condition:

| condition | Qwen lower/UPPER | E2B lower/UPPER | E4B lower/UPPER |
|---|---|---|---|
| sys_upper_only | 0.00 / 0.80 | 0.00 / 0.94 | 0.00 / 0.99 |
| sys_lower_only | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 |
| **spec_upper_only** | 0.00 / **0.58** | 0.00 / **0.43** | 0.00 / **1.00** |
| **spec_lower_only** | **0.99** / 0.00 | **0.99** / 0.00 | **1.00** / 0.00 |
| sys_upper + spec_lower | 0.96 / 0.02 | 0.10 / 0.49 | 0.20 / 0.56 |
| sys_lower + spec_upper | 0.70 / 0.22 | 0.99 / 0.00 | 0.99 / 0.00 |

## Finding 1 — the reasoning-spec IS a causal control surface

This is the cleanest positive result for C1 the project has. On a neutral prompt
that never mentions case, injecting `case: lower` into the reasoning block makes
the output lowercase **99–100% on all three models** — a poem is otherwise
normally capitalised, so the spec *causes* the change. The `upper` direction
follows too, bounded by the model's ability to sustain all-caps at all
(spec_upper_only: E4B 1.00, Qwen 0.58, E2B 0.43).

So a spec placed in reasoning, on a dimension the prompt left unspecified,
controls the output. That is precisely the `[assumed]`-slot mechanism, and it
works — the first clean evidence of it. (E4.1 could not show this because its spec
was redundant with an explicit instruction.)

## Finding 2 — CORRECTED (see 0025): it is a directional bias, not authority

*The original claim here — "the system rule wins, the spec defers" — was wrong.*
Adding a contradicting spec **halves** system=UPPER compliance (E2B 0.94→0.49,
E4B 0.99→0.56) yet does nothing to system=lower (−0.01). Authority would be
symmetric; this asymmetry is a **bias toward the lower-effort form (lowercase)**.
The spec has large power when it points at the easy direction and little when it
points at the hard one. Original (superseded) reasoning kept below.

### (superseded) the spec is subordinate to an explicit system rule

When the spec contradicts a standing system rule, the system rule wins on both
Gemmas. system=UPPER + spec=lower → E2B 49% UPPER / E4B 56% UPPER (system holds,
spec pulls ~10–20% and muddies ~40% to mixed). system=lower + spec=UPPER → 99%
lower on both (system wins outright). The reasoning-spec does **not** override an
explicit instruction; it defers to it.

This is expected and arguably correct: the proposal's spec is meant to make the
*default* on an unspecified dimension explicit, not to beat an instruction the
user or system actually gave. A self-declared convention that could override the
system prompt would be a bug, not a feature.

## Finding 3 — all three are difficulty-ordered (not a two-regime split)

Qwen breaks the pattern. In *both* contradiction cells the output drifts toward
**lowercase regardless of which authority demanded what**: sys_upper+spec_lower →
96% lower, sys_lower+spec_upper → still 70% lower. The reason is in the controls:
Qwen cannot reliably sustain all-caps (sys_upper_only 0.80, spec_upper_only 0.58),
so whenever *anything* points at lowercase — the easy direction — that wins.

Two regimes:
- **E2B, E4B (authority-ordered):** contradictions resolve by *who asked* — the
  system rule beats the spec.
- **Qwen (capability-ordered):** contradictions resolve by *which output is
  easier to produce* — lowercase wins whoever asked.

This is the same execution-difficulty axis that governs every other Phase-0
result: for the weakest model, *what it can do* dominates *what it was told*.

## What this means for the proposal

**Reframes E4.1's pessimism.** E4.1 concluded "surfacing doesn't help override a
prior." The contradiction test shows *why*, and it is not that the spec is inert:
the spec is a genuine causal control surface (Finding 1), it is simply
**subordinate to explicit instructions** (Finding 2). E4.1's collision prompts
put the constraint in the user instruction, so the spec had nothing to add — the
instruction already governed.

**For C1:** positive. An injected spec controls unspecified dimensions ~100%. The
representational claim — the default becomes an addressable, causal token-level
object — is directly supported here for case.

**For training:** a caveat. If an *injected* spec already defers to an explicit
system rule, a *self-emitted* spec will need training to carry enough authority
to change behaviour on dimensions the model has a strong prior about. The spec
works where the model is neutral; it yields where an explicit signal exists.

## Caveats

- One dimension (case). Length/structure may order differently — worth repeating.
- The `upper` direction is capability-bounded on the small models, which confounds
  "authority" with "difficulty" in the upper-seeking cells; the `lower`-seeking
  cells are the clean ones.
- Injected (oracle) spec, not self-emitted. Temp 1.0, 90 samples/cell.
