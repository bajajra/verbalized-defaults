# 0023 — 16-agent checker audit: a blind spot that faked two of E4.1's results

**Date:** 2026-07-23
**Method:** 2,880 E4.1 generations sharded 16 ways; 16 parallel subagents each
independently judged ~180 verbatim answers against the explicit requirement,
compared to the programmatic checker, and reported disagreements. Main context
read only the reports, never the raw generations.

## What the audit found — unanimous across all 16 shards

| checker | verdict | evidence |
|---|---|---|
| **case** (lowercase) | **trustworthy** | independent ASCII+Unicode uppercase scans matched on every item; all FAILs were genuine capitals |
| **length** | **trustworthy** | every verdict consistent with word_count vs threshold |
| **bullets** | **trustworthy** | correct on `- * •`; ignores `*italics*`, `**bold**`, `***`, blockquotes, numbered lists (defensible). Rare exotic-glyph misses (`☞`, em-dash leaders) |
| **postscript** (`ps_recase`) | **SYSTEMATIC BLIND SPOT** | detected a postscript only by the literal substring `"p.s"`, false-FAILing every valid lowercase `ps.`, `ps:`, `ps`, `postscript:` |

~82 disagreements across 14 detailed shards, **all in `ps_recase`**, ~99%
one-directional false-FAIL. One false-PASS (shard 12): an incidental `p.s.` inside
a meta planning bullet where no note was written.

## The blind spot faked two of E4.1's three significant results

`ps_recase` is exactly where 0022 reported significant surfacing effects. The
blind spot deflated the pass rate unevenly, because surfacing changed which
postscript marker the model used — and the checker only saw one marker.

| ps_recase | before (buggy) | after (fixed) |
|---|---|---|
| E2B oracle_declare vs vanilla | **+0.20** (sig, "surfacing helps") | +0.00 (ceiling, no effect) |
| E4B oracle_declare vs vanilla | **−0.15** (sig, "surfacing hurts") | −0.02 (ns) |
| E4B self_declare vs vanilla | −0.13 (sig) | +0.00 (ns) |

**Both headline ps_recase effects were artefacts.** The E2B "+0.20 help" was the
buggy checker under-counting vanilla; the E4B "−0.15 harm" was surfacing pushing
the model toward `ps:` markers the checker missed. With the audited detector,
`ps_recase` is at ceiling on both Gemmas — no effect either way.

Vanilla ps_recase rates rose once the false-FAILs were removed: Qwen 0.78→0.93,
E2B 0.70→0.98, E4B 0.97→1.00.

## E4.1 finding 3, corrected

The only surviving significant `ps_recase` effect is **self_declare hurting on
Qwen (0.93 → 0.80, −0.13)**. So across the whole battery, surfacing a default:

- **helped override a prior significantly: 0 times** (the E2B +0.20 is gone),
- **hurt significantly: 1 time** (Qwen self_declare on ps_recase),
- was null everywhere else.

**This makes E4.1 more negative for the thesis, not less.** The one apparent
positive evaporated under audit. Inference-time surfacing does not help models
override their priors on this battery, and occasionally distracts the weakest model.

## The fix

`has_postscript()` in `verifiers/keywords.py`: line-anchored, accepts
`p.s.` / `p.s` / `ps.` / `ps:` / `ps ` / `p. s.` / `postscript`, rejects in-word
matches (`psychology`, `maps`, `ps4`) and the meta-bullet false-PASS (the `-`
before `p.s.` breaks the line anchor). `count_bullets` gained the unambiguous
unicode bullets `‣ ⁃ ▪ ▫ ◦`; the `☞` dingbat is left out as too ambiguous. 76
tests still pass.

## Why this matters beyond E4.1

Three programmatic checkers were **validated by independent judgment** (case,
length, bullets) and one was caught faking results. The blind spot was invisible
to unit tests because the tests used `"p.s."` — the one form the checker handled.
**Only adversarial audit against real, varied model output found it**, which is
the general lesson: a rule tested on canonical inputs is untested on the inputs
models actually produce.

## Process notes

- The harness blocks subagent report-file writes, so agents returned findings as
  text; several fell back to a shell redirect to also write the file. Both worked;
  I read the returned text.
- 16 agents × ~180 items completed in ~4–6 minutes wall-clock, ~1.4M subagent
  tokens total, with zero pollution of the main context beyond the compact
  per-shard summaries.
