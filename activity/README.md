# Activity log

Running record of experiments, decisions, observations and results for the
Verbalized Defaults project. One markdown file per activity, numbered in
chronological order. Design documents (the proposal and experiment design) live
outside this repo; this folder records what was actually *done* and *found*.

Convention for each entry:

- **Context** — why this was done, what it unblocks.
- **What was done** — concrete actions, versions, commands.
- **Observations / results** — including negative results and surprises.
- **Decisions** — anything a future session must not silently revert.
- **Open items** — what this entry deliberately left unresolved.

| # | Entry | Summary |
|---|---|---|
| 0001 | [model-and-compute-plan](0001-model-and-compute-plan.md) | Compute reality (5090 + DGX Spark) forces a small-model study; Qwen3.5-2B chosen as primary subject |
| 0002 | [dataset-landscape](0002-dataset-landscape.md) | Verified HF datasets mapped to experiment roles; prompt-volume targets per phase |
| 0003 | [infra-setup-turing](0003-infra-setup-turing.md) | uv project on the 5090 box, vLLM 0.25.0 + Blackwell stack verified |
| 0004 | [verifier-suite-v0](0004-verifier-suite-v0.md) | First verifier suite, IFEval metric parity, 21 tests green |
