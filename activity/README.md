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
| 0005 | [spec-parser-and-ifeval-parity](0005-spec-parser-and-ifeval-parity.md) | Canonical `<spec>` grammar + parser; measured 0 mismatches vs IFEval on 412 samples |
| 0006 | [ifeval-adapter-and-schema-coverage](0006-ifeval-adapter-and-schema-coverage.md) | Metadata→Spec adapter; **only 59.5% of IFEval prompts fully expressible** — affects E0.1 |
| 0007 | [schema-v2-benchmark-snapshot](0007-schema-v2-benchmark-snapshot.md) | Schema v2 (15 slots): coverage **59.5% → 93.5%** of prompts; the frozen benchmark snapshot |
| 0008 | [ifbench-coverage-and-ifstruct](0008-ifbench-coverage-and-ifstruct.md) | Schema expresses **95.8% of IFEval but 10.5% of IFBench**; 57% of IFBench is Bucket C — Gate 3 needs rethinking. IFStruct reviewed, not adopted |
| 0009 | [correction-schema-is-a-default-inventory](0009-correction-schema-is-a-default-inventory.md) | **Corrects 0008**: a slot exists iff the dimension has a latent default. Adds `other` ([given]-only). Retracts the IFBench coverage conclusions |
| 0010 | [prior-inventory-and-server](0010-prior-inventory-and-server.md) | Decoupled vLLM server; first prior inventory for Qwen3.5-2B — **defaults are genre-conditioned and aggregates hide them**; emoji + nesting earn slots |
