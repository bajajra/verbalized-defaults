# 0010 — First prior inventory for Qwen3.5-2B (and a decoupled server)

**Date:** 2026-07-21
**Result:** 180 unconstrained generations across 20 genres. **Defaults are
strongly genre-conditioned and the global aggregate hides them completely.**
Two candidate dimensions (emoji, nesting depth) are empirically default-bearing
and earn typed slots; the `response_boundary` slot turns out to be nearly
irrelevant for this model.

## Infrastructure: server/client decoupled

Generation now runs against a persistent vLLM OpenAI-compatible server
(`scripts/serve.sh`) with clients speaking plain HTTP. The engine loads once and
stays warm, requests go out concurrently, and — importantly — **probe scripts
import no vLLM at all**, so engine-level breakage is confined to one process.
This is also the shape the RL phase needs (rollouts served from one box while
another trains).

Two startup failures worth recording, both non-obvious:

1. **`from vllm import LLM` hung forever.** Not slow — hung. `torchcodec` (pulled
   in by vLLM for video) probes FFmpeg 8 first and needs `libavdevice.so.62`,
   which this host lacks; it ships only a *partial* FFmpeg 8 (`libavutil.so.60`
   present). Missing that library, torchcodec enters an unbounded load/retry
   loop instead of failing. `PyNvVideoCodec` — already a vLLM dependency —
   bundles the complete FFmpeg 8 set, so putting it on `LD_LIBRARY_PATH` fixes
   the import in **3.5s**. Do *not* fix this by uninstalling torchcodec: `uv run`
   re-syncs and silently undoes it.
   *Diagnostic note:* a plain `import vllm` succeeds, so testing that misleads —
   only `from vllm import LLM` touches the video path.
2. **Engine init died on missing `ninja`** (needed for JIT kernel compilation).
   `uv add ninja`, plus putting the venv's `bin` on `PATH` in the launch script,
   because the engine invokes `ninja` by name from subprocesses.

Also: `rsync -a` faithfully copies the *source* file mode, so it silently
un-executables scripts. The exec bit is now set on the committed file.

## Methodology: truncation censors length

If a generation stops at `max_tokens`, its length reflects our cap, not the
model's prior. The probe records `finish_reason` and excludes truncated samples
from all length statistics rather than letting them bias the medians downward.
At `max_tokens=1536`, 3/180 were truncated.

## The headline: defaults are genre-conditioned, and aggregates lie

| dimension | overall median | what the per-genre view shows |
|---|---:|---|
| words | 556 | **136 (apology_note) → 818 (report)** — a 6× spread |
| bullets | 3.5 | **0** for essay/story/poem/email/dialogue/news, **27** for faq |
| headers | 4 | 0 for narrative genres, 11 for report |
| highlights (`**bold**`) | 23.5 | 0 for essay/poem, **82** for faq |
| emoji | **0** | **0 in 12 genres, but 6 (social_post), 5 (recipe), 4 (review)** |
| max_nesting | 1 (flat) | **3** for faq/howto/recipe |
| has_preamble | 0 | **only recipe** (9/9 responses) |

The emoji row is the clearest lesson: the global median is **0**, which reads as
"no prior at all", yet emoji appear in **8 of 20 genres** and are the *norm* in
social posts and recipes. A global default inventory would have concluded the
dimension does not exist. **Defaults must be fitted per genre** — which is what
the experiment design already specified, now empirically justified rather than
assumed.

This also directly confirms the taxonomy's A1 mechanism on a new model: the
genre's natural-length prior is real and strong (6× spread across genres), which
is exactly the prior that an explicit length instruction has to fight.

## Schema adjudication (the point of the probe)

Applying the agreed criterion — *a dimension earns a typed slot iff the model
shows a stable prior on it* — measured on our own authored genre prompts, not on
any benchmark:

| candidate | verdict | evidence |
|---|---|---|
| **emoji** | **earns a slot** | strongly register-conditioned: median 6 in social_post, 5 in recipe, 0 in 12 genres |
| **nesting depth** | **earns a slot** | median 3 in faq/howto/recipe, 0–1 elsewhere; "flat" is a real default that "use sub-bullets" would fight |
| indentation | no | 0 everywhere, no genre variation — a "never" prior with nothing to steer |
| preamble | **weak for this model** | present only in recipe; Qwen3.5-2B essentially does not preamble |

**Disclosure (per the rule set in [0009](0009-correction-schema-is-a-default-inventory.md)):**
`format:emoji` and `format:sub-bullets` are both IFBench families, so these two
additions **do overlap the held-out OOD eval**. The justification here is
empirical — the model's own measured priors on our own prompts — rather than
"IFBench has it", but the overlap is real and is stated rather than buried.

**`response_boundary` is much less load-bearing than assumed.** It was designed
around Gemma's inline-thinking pollution; Qwen3.5-2B has a separate reasoning
channel and produced a preamble in only one genre. The slot stays (it is still
`[given]`-drivable, and IFStruct's "commentary rules" show the convention is
real), but it should not be treated as a headline mechanism for this model.

## Status

Schema v2's typed slots remain **on standby** — this entry records the verdict
and the evidence; it does not implement the two new slots.

## Open items

- Implement `emoji` and `nesting` (likely as a `markup` dimension and a
  `structure` field respectively) → schema v3, with the IFBench overlap disclosed.
- Scale the probe: 180 generations over 3 samples is a pilot. The design calls
  for 2k stratified prompts × 3 samples for calibrated `defaults.json` values.
- Dispersion is reported as IQR/median, which is undefined when the median is 0 —
  so "always zero" dimensions show `n/a` rather than "strong never-prior". Needs a
  better stability statistic before these numbers drive slot decisions at scale.
- Carried over: `forbidden` substring-vs-word-boundary default.
