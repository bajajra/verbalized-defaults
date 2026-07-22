# 0002 — Dataset landscape and prompt-volume targets

**Date:** 2026-07-21

## Context

Selecting data sources for the pools defined in the experiment design §3
(U = unconstrained, K = constrained, M = multi-turn), plus the datasets needed to
reproduce the mandatory head-to-head baselines. All repository IDs below were
verified rather than recalled.

## Verified datasets, by the job they do

### 1. Eval-only — decontaminate against these, never train on them

| Dataset | Repo | Role |
|---|---|---|
| IFEval | `google/IFEval` | seen-family eval |
| IFBench (single-turn) | `allenai/IFBench_test` | **primary OOD eval** — 58 unseen constraints, ~300 prompts |
| IFBench (multi-turn) | `allenai/IFBench_multi-turn` | multi-turn OOD |
| Multi-IF | `facebook/Multi-IF` | multi-turn drift eval (cc-by-nc-2.0, research only) |

### 2. Baseline reproduction — the pre-registered head-to-heads

| Dataset | Repo | Defends |
|---|---|---|
| RLCF / WildChecklists (130k) | `viswavi/wildchecklists` | E3.5 checklist-reward baseline |
| UltraIF | `kkk-an/UltraIF-dpo-20k` | E3.6 decomposition baseline |
| RLVR-IFeval | `allenai/RLVR-IFeval` | E2.2d Tülu-3-style direct prompt-constraint RLVR |

### 3. Prompt pools and seed constraint data

| Dataset | Repo | Use |
|---|---|---|
| WildChat-1M | `allenai/WildChat-1M` | U pool — **decontamination critical**: IFBench is carved from held-out WildChat |
| LMSYS-Chat-1M | `lmsys/lmsys-chat-1m` | U pool (first turns) |
| No Robots | `HuggingFaceH4/no_robots` | K base tasks |
| Tülu-3 persona IF | `allenai/tulu-3-sft-personas-instruction-following` | closest match to the "Tülu-3 IF-data style" composition; ~30k, IFEval-taxonomy constraints |
| Tülu-3 persona IF (pref) | `allenai/tulu-3-pref-personas-instruction-following` | DPO-pair seed for D3-dpo |
| Suri | `chtmp223/suri` | 20k long-form (2k–5k word) multi-constraint — targets A1 length, the hardest gap |
| Conifer | `ConiferLM/Conifer` | multi-constraint, includes multi-turn |
| AutoIF | `Post-training-Data-Flywheel/AutoIF-instruct-61k` | execution-feedback seed / prompt source |

Also noted: the **IF-RLVR training toolkit** (29 extra hand-annotated constraints
with verifier functions, on the `allenai/IFBench` GitHub) is a ready-made
expansion for the constraint-family generator — provided IFBench's own 58
families stay held out. Related paper worth reading for D3-dpo:
"Replay Failures as Successes" (arXiv 2512.23457), which mines a model's own
failures for RL, the same mechanism as our prior-default rejected samples.

## Key caveat

None of the public IF datasets ship constraints paired with verifiers matched to
IFEval's *literal* metric. They are usable as **prompt pools, baselines and
references**, but gold `[given]`-slot labels must come from our own constraint
generator with our own literal verifiers — otherwise we reintroduce the Bucket-B
failure of training against a checker that disagrees with the benchmark.

## Prompt-volume targets

Unique prompts to source, consolidated from experiment design §3.1 and §3.5:

| Stage | Set | Unique prompts |
|---|---|---|
| Phase 0 | defaults measurement | 2k U (20 genres × 100) |
| Phase 0 | calibration probe (E0.3) | 1k U |
| Phase 0 | E0.1/2/4 | 0 new (run on IFEval + IFBench) |
| Phase 1 | D1 (constrained) | 30k K |
| Phase 1 | D2 (assumed-slot) | 15k U |
| Phase 1 | controls | 0 new (reuse D1/D2, stripped/paraphrased) |
| Phase 2–3 | GRPO stream | ~0 new (resamples K+U) |
| Phase 4 | D3-int | 6k → 24k examples |
| Phase 4 | D3-dpo | ~12k pairs (partly from existing failure dumps) |
| Phase 5 | D4 | 8k conversations |

**≈60k unique prompts** for the full program, from a curated raw pool of
~100k U + 60k K (the surplus is decontamination and stratification attrition).

Two multipliers dominate actual cost, and neither is prompt count:

1. **Generation.** Every gold response is best-of-n (n≤8) against the verifier
   suite, so ~57k verified responses implies roughly **300–450k generations**.
   The bottleneck is inference + verification throughput.
2. **RLVR rollouts.** ~8k GRPO steps × group-8 ≈ 64k rollouts, resampled from a
   fixed bank of ~10–20k prompts. No new gold completions needed.

## Lean path

Only **~3k curated prompts** (2k defaults + 1k calibration) plus the existing
benchmarks are needed to run all of Phase 0 and reach **Gate 1**. If oracle-prefill
lift is <2pt, H0 is falsified before a single training prompt is curated.

## Observation worth acting on

The headline risk in the taxonomy is the IFBench generalization collapse, and that
is **not** fixed by more prompts — it is fixed by breadth of the **~120 constraint
families (84 train / 36 held-out)**. If effort has to be rationed, spend it on the
constraint generator, not on pushing prompt counts higher.
