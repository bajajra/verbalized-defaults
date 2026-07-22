# Verbalized Defaults

Teach a small instruction-tuned model to emit a **typed spec of output
conventions** before generating, so that SFT-absorbed latent defaults become
explicit, verifiable, trainable tokens instead of a silent fight against explicit
instructions.

> Nearly every real instruction-following failure is an explicit instruction
> losing a silent fight against a latent default — essays stopping at ~40
> sentences, poems auto-capitalising, "P.S." never recased, a global count
> applied per-unit. The model cannot override, verify, or even notice a variable
> that exists only as a distributional tendency.

The model declares the resolved value of every convention-governed dimension —
including the ones nobody asked about — tagging each as `[given]` (read from the
prompt) or `[assumed]` (its own default, now stated). It is then rewarded
separately for **binding** (reading the prompt into the spec) and **execution**
(obeying the spec).

## Repository layout

```
src/verbalized_defaults/    verifier suite: frozen slot schema + per-slot checkers
tests/                      metric-parity pins and taxonomy-anchored failure cases
activity/                   running log of experiments, decisions, observations
```

The research design documents (proposal and experiment design) and the empirical
failure taxonomy live outside this repository. `activity/` records what was
actually done and found — start there.

## The verifier suite

`verify_spec(text, spec)` returns a `SpecReport` exposing:

| Property | Purpose |
|---|---|
| `.ok` | hard gate — every gold training example must pass all its verifiers |
| `.score` | dense `R_exec` reward signal in `[0, 1]` |
| `.failures()` | per-slot diagnostics for interleaved verification / patching |

Metrics are pinned to **IFEval parity** by design: words are `\w+` regex tokens
(not whitespace-split), sentences use the Punkt tokenizer, paragraphs split on a
blank line. Divergence here would mean training against a checker that disagrees
with the benchmark. See
[activity/0004](activity/0004-verifier-suite-v0.md) for the parity findings.

## Development

Package management is via [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q
```

This repository is canonical; the GPU box is a working copy. To run on the
training machine:

```bash
rsync -a src/ tests/ <host>:workspace/verbalized-defaults/
ssh <host> 'cd workspace/verbalized-defaults && uv run pytest -q'
```
