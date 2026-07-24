# 0023 — 16-agent checker audit

**Date:** 2026-07-23
**Method:** the 2,880 E4.1 generations were split into 16 shards (~180 each) and
given to 16 parallel subagents. Each judged, per item, whether the answer
satisfied the explicit requirement, compared that to the programmatic checker's
verdict, and reported disagreements. The main context read only the returned
per-shard summaries.

Subagent judgments are used below as *signals* pointing at where the checker may
be wrong. The quantitative impact is measured programmatically, not by summing
the subagents' counts.

## What the subagents reported

All 16 shards reported the same result:

| checker | reported outcome |
|---|---|
| case (lowercase) | no disagreements; verdicts matched independent uppercase scans |
| length | no disagreements; verdicts matched word_count vs threshold |
| bullets | verdicts matched, except two items using unicode glyphs `☞` (U+261E) and `⚫` (U+26AB) as list markers, which the counter scored 0 |
| postscript (`ps_recase`) | systematic disagreement: the checker detected a postscript only via the literal substring `"p.s"`, and reported FAIL on lowercase answers whose postscript used `ps.`, `ps:`, `ps`, or `postscript:` |

Reported disagreement counts per shard ranged 3–8, concentrated in `ps_recase`.
One shard reported a false-PASS (an incidental `p.s.` inside a planning bullet
where no note was written); the rest were false-FAILs.

## Programmatic verification (the reliable number)

For every `ps_recase` generation (n=540 across the three models), the old checker
(literal `"p.s"` substring + lowercase) was compared to the fixed checker
(`has_postscript` + lowercase):

| | count | share of 540 |
|---|---:|---:|
| verdict unchanged | 438 | 81% |
| FAIL → PASS (blind spot false-FAILs, now fixed) | 92 | 17% |
| PASS → FAIL (incidental `"p.s"` now rejected) | 10 | 2% |
| **total verdicts changed** | **102** | **19%** |

So the old checker was wrong on ~19% of `ps_recase` items: 92 false-FAILs (the
reported blind spot) and 10 false-PASSes (incidental substring matches the
line-anchored fix now rejects). case, length and bullets verdicts were unaffected.

## Effect on the E4.1 numbers

`ps_recase` is where 0022 had reported significant surfacing effects. Recomputed
with the fixed checker:

| ps_recase, Δ vs vanilla | before fix | after fix |
|---|---|---|
| E2B oracle_declare | +0.20 (sig) | +0.00 |
| E4B oracle_declare | −0.15 (sig) | −0.02 (ns) |
| E4B self_declare | −0.13 (sig) | +0.00 (ns) |
| Qwen self_declare | — | −0.13 (sig) |

Vanilla ps_recase rates after the fix: Qwen 0.78→0.93, E2B 0.70→0.98, E4B
0.97→1.00. The two significant Gemma effects reported in 0022 do not survive the
fix; the surviving significant ps_recase effect is Qwen self_declare −0.13. This
is the correction applied to 0022 Finding 3.

## The fix

`has_postscript()` in `verifiers/keywords.py`: line-anchored, accepts `p.s.`,
`p.s`, `ps.`, `ps:`, `ps `, `p. s.`, `postscript`; rejects in-word matches
(`psychology`, `maps`, `ps4`) and non-line-initial matches (the `-` before `p.s.`
in a planning bullet). `count_bullets` gained the unicode bullet glyphs
`‣ ⁃ ▪ ▫ ◦ ● ○ ◉ ⚫ ◆ ◇`. 76 tests pass.

## Observations

- case, length, and bullets were checked against independent judgment on 2,880
  real generations and matched (bullets except the two glyph cases). The
  postscript check was the only systematic error.
- The postscript error was not caught by the unit tests, which used `p.s.` — the
  one form the old checker handled.

## Process notes

- The harness blocked subagent report-file writes; agents returned findings as
  text. All 16 returned.
- Wall-clock ~4–6 minutes; ~1.4M subagent tokens total.
