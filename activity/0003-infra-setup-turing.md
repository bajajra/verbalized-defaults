# 0003 — Infrastructure setup on turing (RTX 5090)

**Date:** 2026-07-21

## Context

Standing up the first real working environment: a uv-managed Python project on
the training box, with vLLM available for the Phase-0 probes (which are all
inference) and later for best-of-n generation and GRPO rollouts.

## Machine

```
host      bajajra-turing (192.168.1.220)
os        Linux x86_64
gpu       NVIDIA GeForce RTX 5090, 32607 MiB
driver    595.71.05
```

## What was installed

- **uv 0.11.31** (`~/.local/bin/uv`) — all package management goes through uv.
- Project at **`~/workspace/verbalized-defaults/`**, created with
  `uv init --package`, pinned to **Python 3.12** via `.python-version`.
  (The system Python is 3.14.4, too new for the ML stack.)
- Runtime deps: `nltk`, `langdetect`, `immutabledict` (the same libraries IFEval
  uses, so our metrics can match its tokenization), plus NLTK `punkt`/`punkt_tab` data.
- Dev deps: `pytest`.
- **vLLM 0.25.0**, which resolved a Blackwell-capable stack without needing a
  custom index (flashinfer, tokenspeed-triton, nvidia cuda libs).

## Verification

```
torch:           2.11.0+cu130
vllm:            0.25.0
cuda available:  True
device:          NVIDIA GeForce RTX 5090
capability:      (12, 0)      # sm_120 Blackwell
```

The capability check matters: a torch build without sm_120 kernels would import
and report CUDA fine, then fail or silently fall back at kernel launch. This
confirms the Blackwell path is real.

## Workflow decision

**The local git repo is canonical; turing is a working copy.**
Code is authored and committed in the local repo
(`github.com/bajajra/verbalized-defaults`), then pushed to turing with rsync and
executed there:

```bash
rsync -a src/   192.168.1.220:workspace/verbalized-defaults/src/
rsync -a tests/ 192.168.1.220:workspace/verbalized-defaults/tests/
ssh 192.168.1.220 'cd workspace/verbalized-defaults && uv run pytest -q'
```

This keeps version control and the design docs on the Mac while the GPU box stays
a disposable execution environment.

## Observations

- The long vLLM install was backgrounded on the remote with `nohup` + a log file
  rather than held open over SSH, so it survives connection drops. Worth reusing
  for any long-running job.
- Running `uv run` concurrently with an in-flight `uv add` risks a project-lock
  clash; use `.venv/bin/python` directly if something must run during an install.

## Open items

- vLLM has been imported but not yet used to serve a model; the first real load
  (Qwen3.5-2B) will be the actual test of the Blackwell inference path.
- No equivalent environment on `spark` yet — needed before it can serve as the
  judge / rollout host.
