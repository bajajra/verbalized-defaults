# 0020 — E0.4: the C2 diagnostic, and two instrument failures found on the way

> **PARTIALLY SUPERSEDED.** The "33.5% wrong-value" figure is corrected to 17.6% ([0021]/[0023]). The value-aware C2 diagnostic and the Simpson-stratified conditional stand.

**Date:** 2026-07-23
**Runs:** `e04-qwen`, `e04-e2b`, `e04-e4b` — 300 IFEval prompts × 3 samples ×
3 models = **2,700 generations**, all integrity-verified (0 dupes, 0 truncation).
Phase 0 is now complete.

## What E0.4 asks

Binding (E0.2) and execution (E0.3) had been measured on *different* prompt sets,
so they could not be combined. E0.4 joins them on the **same constraint
instance**: was this specific constraint registered, and did the answer satisfy it?

## Instrument failure 1 — binding was not value-aware

The original definition counted a constraint as bound whenever the matching slot
appeared in the declaration. Measured against real runs:

| slot | declared, correct value | declared, **wrong value** |
|---|---:|---:|
| length_words | 22 | **77 (78%)** |
| must_include | 4 | **55 (93%)** |
| length_sentences | 23 | 44 (66%) |
| structure | 65 | 51 (44%) |
| **all slots** | 492 | **248 (33.5%)** |

A prompt asking for 300 words and a declaration saying 450 was scored as *bound*.
That is not binding; it is a miss with extra steps.

Consequences, both severe:

1. **Binding recall was overstated.** Value-aware recall is **0.324 / 0.476 /
   0.443** (Qwen / E2B / E4B) against the 0.485 / 0.540 / 0.559 reported in 0018.
2. **The diagnostic inverted.** With slot-presence binding, E4B showed binding
   *negatively* associated with passing (lift **−0.105**) — because "bound"
   was contaminated with "bound to the wrong target", which then fails execution.

Fixed in `binding.py`. The definition used: **would a response that exactly hits
the declared value satisfy the required constraint?** Neither exact equality (too
strict — "about 320" does capture "≥300") nor slot presence (too lenient).

## Instrument failure 2 — the pooled conditional is confounded

With value-aware binding the inversion disappeared, but the pooled result was
~zero on all three models. That is Simpson's paradox: **binding rate correlates
with family difficulty.** Families that are almost never bound
(`postscript` 0.02, `end_checker` 0.00, `highlighted_sections` 0.00) are also
families that pass at 0.93–1.00 *without* being bound — they are satisfied by
default. Pooling them against hard, always-bound families
(`number_paragraphs` bind 0.76 / pass 0.28) cancels the effect.

Stratifying within family is required. Both numbers are reported below.

## Results

| model | binding recall | P(pass) | P(pass\|bind✓) | P(pass\|bind✗) | pooled lift | **stratified lift** | families + |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-2B | 0.324 | 0.493 | 0.488 | 0.495 | −0.007 | **+0.102** | **10/14** |
| Gemma E2B | 0.476 | 0.822 | 0.833 | 0.812 | +0.021 | +0.005 | 7/15 |
| Gemma E4B | 0.443 | 0.782 | 0.779 | 0.784 | −0.005 | −0.010 | 6/14 |

**On the weakest model, registering a constraint correctly predicts satisfying it
by ~10 points, in 10 of 14 families. On the two stronger models there is no
association at all.**

The likely reason is a **ceiling effect**: E2B and E4B satisfy ~80% of constraints
regardless of whether they declared them, leaving little room for binding to
explain variance. Qwen sits at 0.49 and has room.

## What this means for C2

C2 claims binding and execution are separable stages that deserve separate
rewards. E0.4 gives that **partial and model-dependent support**:

- **Supporting:** binding recall is low everywhere (0.32–0.48), so roughly half to
  two-thirds of constraints never get correctly registered — a large, addressable
  failure mode that `R_bind` targets directly and that no execution reward can fix.
- **Supporting:** on Qwen the two stages are measurably distinct (+0.102).
- **Not supporting:** on E2B/E4B, correct binding does not predict passing. If
  binding does not gate execution on the models we would train, a separate
  `R_bind` may buy less than the design assumes.

**The honest reading is that E0.4 does not settle C2.** It shows the stages are
separable *in principle* and measurable *in practice*, but the causal claim —
that fixing binding fixes downstream compliance — is only visible on the weakest
model, and is correlational even there. Binding correctly and passing may both be
driven by a third factor (the model simply understood the constraint), which this
design cannot separate.

## Caveats

- **Correlational, not causal.** No intervention on binding was performed.
- Per-family cells are small (both cells n≥5; 14–15 usable families).
- IFEval only; the stronger models are near ceiling here, which is exactly the
  regime where this diagnostic is least informative. A harder eval would test it
  better.

## Storage: runs are now immutable and complete

All three runs use the new `runstore` (`runs/<run_id>/`), which exists because
earlier data could not be trusted:

- **Full text, never truncated** — 30% of the previous E0.2 answers hit a
  2000-char cap and were unscoreable, which is why E0.4 required regeneration.
- **No metrics stored** — everything derivable is recomputed downstream, so an
  analysis change cannot leave stale numbers on disk.
- **Self-describing** — model, sampling parameters, code version, host, timestamps.
  Note the GPU box is an rsync'd copy with no git history, so the authoritative
  `code_version` is passed in from the canonical repo.
- **Immutable** — writing an existing run id raises rather than overwriting evidence.
- **`verify_run()`** — row counts, duplicate keys, empty records, token-limit hits.

## Process note — the same bug, a third time

`pgrep -f "bin/vllm serve"` matched **its own command string** again, so `kill`
took out the shell before the server. This is the third occurrence, and it was
already written into conclusions.md as a rule after the second. Pattern-matching
on a process name is not safe from a shell whose command line contains that
pattern. Now killing by **port owner**:

```bash
PID=$(ss -lptnH "sport = :$P" | grep -oP "pid=\K[0-9]+" | head -1)
```

## Open items

- Re-run E0.2's headline with value-aware binding (0018's recall figures are
  superseded by the table above but its per-family numbers are not yet redone).
- Delete `data/*.json` pre-fix summaries.
- E4.1 prior-targeted battery — still the sharpest untested claim.
