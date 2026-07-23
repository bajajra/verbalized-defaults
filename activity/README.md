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

**Two reference documents, kept separate:**
- [findings.md](findings.md) — every measured number, with protocol and provenance. Data only.
- [conclusions.md](conclusions.md) — graded claims and interpretation, with all retractions in one table.

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
| 0011 | [ifeval-scoring-and-e01-pilot](0011-ifeval-scoring-and-e01-pilot.md) | IFEval scoring harness; first interpretable E0.1 — **oracle prefill is neutral-to-harmful**; 4 methodological traps fixed |
| 0012 | [e01-notation-matters-more-than-surfacing](0012-e01-notation-matters-more-than-surfacing.md) | **Surfacing works (+0.11, Gate 1 passes) but the typed DSL captures almost none of it** — direct challenge to C1 |
| 0013 | [notation-effect-replicated-two-models](0013-notation-effect-replicated-two-models.md) | **Retracts 0012's +0.11 (noise).** Proper 5-sample paired analysis: spec-vs-none inconclusive, but **NL beats typed significantly on both models** |
| 0014 | [e01-full-benchmark-both-models](0014-e01-full-benchmark-both-models.md) | **Definitive E0.1**: 541x4x7x2 models. NL beats typed on both (+0.038/+0.063); surfacing helps Gemma but not Qwen; placement *reverses* between models |
| 0015 | [e03-self-consistency-first-assumed-result](0015-e03-self-consistency-first-assumed-result.md) | **First `[assumed]` result**: model declares 4.5 conventions, obeys **47%**; length violated 94% of the time. Large RLVR headroom |
| 0016 | [quantitative-magnitude-and-qualitative-inventory](0016-quantitative-magnitude-and-qualitative-inventory.md) | Length miss **−26% median, 74% under-target**; qualitative inventory — model's natural vocabulary is stylistic, plus a self-imposed **content policy** with no slot |
| 0017 | [e03-three-models-family-beats-size](0017-e03-three-models-family-beats-size.md) | E2B control: **self-consistency ~0.45 on all 3 models**; length underproduction is a **family** effect (Qwen −26% vs Gemma-2B −5%), not size |
| 0018 | [e02-binding-and-per-slot-execution](0018-e02-binding-and-per-slot-execution.md) | Extractor de-biased (E4B cov +34%); **binding recall ~0.5**, `repeat_prompt` 0% on all 3; per-slot execution gradient language 100% → length 7-16% |
| 0019 | [correction-length-underproduction-is-universal](0019-correction-length-underproduction-is-universal.md) | **Retracts 0016+0017**: length underproduction is **universal (~30% on all 3)**, not Qwen-specific or family-driven — earlier result was a selection artefact |
