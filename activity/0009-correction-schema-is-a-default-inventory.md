# 0009 — Correction: the schema is a default inventory, not a constraint language

**Date:** 2026-07-21
**Status:** revises the framing and two conclusions of
[0008](0008-ifbench-coverage-and-ifstruct.md). 0008 is left intact; the reasoning
error is worth preserving alongside its fix.

## The error

0008 measured "what fraction of IFBench can schema v2 express?", got 10.5%, and
concluded (a) our schema is overfit to IFEval and (b) Gate 3 is close to
unwinnable because an oracle spec can only carry ~10–18% of IFBench.

Both conclusions rested on a category error: treating the typed schema as a
**universal constraint language** and its coverage as a quality metric.

## The correction

**A typed slot exists iff its dimension carries a latent default.**

That is the entire mechanism the project is built on: a default exists, it is
silent, an explicit instruction fights it and loses. The schema is therefore an
*inventory of default-bearing dimensions*, not a language for arbitrary
predicates.

A palindrome constraint has no default. The model carries no absorbed prior
about palindromicity that could silently win a fight. It exists only because the
prompt said so. The same goes for prime word lengths, syllable parity, stop-word
ratios and letter counts.

So low IFBench typed coverage is **not a defect in the schema** — it is a fact
about IFBench: it mostly tests arbitrary predicates rather than
convention-governed dimensions. The schema is doing exactly what it was designed
to do.

## Consequences implemented

**1. The `other` slot.** Constraints without defaults still have to be carried
into the spec — binding must not lose them, and multi-turn state must retain
them. They now live in `other`, with a load-bearing invariant:

| | `[given]` | `[assumed]` |
|---|---|---|
| typed slot (default-bearing) | yes | yes |
| `other` (no default) | yes | **never** |

An `[assumed]` entry in `other` is a category error — there is no prior to
assume — and both the validator and the parser reject it. `other` is excluded
from `R_exec` (no verifier), exactly as `register` already is, but it *is*
visible to binding.

Guardrail against dissolving C1: `other` is a **list of discrete restated
constraints**, not prose. If it were free text it would drift toward the
free-form-plan control (E1.2) that the typed spec is supposed to beat. A
constraint that *is* typeable belongs in its typed slot; putting it in `other`
should itself be an `R_bind` penalty (not yet implemented — `R_bind` does not
exist).

**2. The metrics changed.** "% expressible" measured the wrong thing. Replaced by:

- **Typed coverage** — has a slot ⇒ has a default ⇒ verifiable. IFEval 95.8%.
- **Binding coverage** — is the constraint carried into the spec at all?
  100% by construction, typed slots + `other`.

**3. Adapter routes untyped families into `other`.** Both `keywords:letter_frequency`
and every unrecognised id are now restated into `other` as `[given]`, so binding
never silently drops a constraint.

## What is retracted, and what stands

**Retracted:**

- "An oracle spec can carry at most ~10–18% of IFBench." False. With `other` it
  carries all of it.
- "Gate 3 is close to unwinnable." Overstated, and for the wrong reason.
- "Our schema is overfit to IFEval." Wrong framing — it is scoped to
  default-bearing dimensions, and IFEval simply contains more of them.

**Stands:**

- **57.3% of IFBench is Bucket C.** Still true and still the real limit on how
  much IFBench can move under this thesis — not because the spec cannot *express*
  those constraints, but because there is no default being overridden. Reporting
  **IFBench-A alongside the full set** remains right, now justified on
  mechanism rather than on expressiveness.

## The prediction this buys (better than a delta)

The reframing yields a differential prediction the E0.4 decomposition can test:

- On **IFEval**, the spec should help via **both** binding (registering the
  constraint) and default-override (beating the silent prior).
- On **IFBench**, there is mostly no default to override, so the spec should help
  via **binding only**, and barely move the Bucket-C families at all.

If spec-mediated gains on IFBench concentrate in binding-limited families and are
absent in Bucket C, that **confirms the mechanism** rather than merely reporting a
number. A weak IFBench result becomes a *predicted* outcome rather than a failure.

## Schema membership becomes empirical

The criterion "does this dimension carry a latent default?" is measurable, not a
matter of taste: Phase 0's default measurement fits per-dimension prior
distributions. A candidate dimension earns a slot if the model exhibits a stable
prior on it, and does not if there is nothing to measure.

This also **dissolves the integrity problem** flagged in 0008. Having seen
IFBench's family list, my judgement about which slots to add is contaminated —
but the probe adjudicates instead of me. Candidates worth testing, because they
plausibly *do* carry defaults: **nested list depth** (models default to flat or
one level), **emoji usage** (a strong register-conditioned prior), **indentation
style**, and **rhetorical shape**.

Schema v2's typed slots are **on standby** pending that measurement — deliberately
unchanged in this entry.

## Open items

- **IFBench id map.** The adapter speaks IFEval's id vocabulary only, so
  IFBench's `count:word_count_range` — a genuinely default-bearing dimension —
  falls through to `other` instead of occupying `length_words`. Fixing this adds
  no slot and no expressive power, only vocabulary, but it *does* use knowledge of
  IFBench's id names and is disclosed here as such. Pinned by a test.
- **Natural-language restatement for `other`.** Entries are currently structured
  restatements (`family(args)`). For oracle prefill on IFBench that is likely too
  machine-ish to surface the constraint usefully.
- Carried over: `forbidden` substring-vs-word-boundary default.
