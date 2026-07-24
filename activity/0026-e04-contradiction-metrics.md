# 0026 — E0.4: how often the declaration contradicts the ask

**Date:** 2026-07-23
Sub-analysis of the E0.4 runs (`e04-*`), refining the A/B/C triangle (0025).

A required constraint the prompt states can go three ways in the model's
declaration (value-aware, `binding.py`):

| | Qwen | E2B | E4B |
|---|---:|---:|---:|
| declared & correct | 33% | 48% | 45% |
| declared & **contradict** (value would not satisfy the ask) | **13%** | 9% | 10% |
| not declared (omission) | 54% | 43% | 45% |
| contradict as % of *declared* | **28%** | 17% | 18% |
| responses with ≥1 contradiction | 18% | 13% | 14% |

**Contradiction is the minority outcome.** Omission (~half) and correct
declaration dominate; the model actively declares an opposing value 9–13% of the
time, rising as the model weakens.

**Note on the setup:** in E0.4 the constraints are in the *user* prompt; the
system prompt is only the "declare your conventions" cue and carries no constraint
to contradict. So "spec contradicts instruction" here means the declared value
opposes the user-stated constraint, not a system-prompt rule (that is the
contradiction test, 0024).

**By slot:** contradictions cluster on hard dimensions — structure (36–49%),
length_sentences (40–59%), must_include (up to 40% on E4B). `case` is 15% (Qwen)
vs 5% (E4B): the genuine "latent default (`standard`) wins the declaration"
signal, concentrated in the weakest model, consistent with 0025.

**Caveat:** `structure` and `length_sentences` contradictions are partly an
adapter representation mismatch (a declared "3 paragraphs" extracts as
`paragraphs`/`prose` where the ask was `sections`), so those rows are upper
bounds on genuine contradiction.
