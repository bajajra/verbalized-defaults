#!/usr/bin/env bash
# Launch the vLLM OpenAI-compatible server.
#
# Server/client are deliberately decoupled: the engine loads once and stays warm,
# probe clients are plain HTTP with no vLLM import, and requests can be issued
# concurrently. This is also the shape the RL phase needs later (rollouts served
# from one box while another trains).
#
# LD_LIBRARY_PATH note: torchcodec (pulled in by vLLM for video) probes FFmpeg 8
# first and needs libavdevice.so.62, which this host does not ship -- it has only
# a partial FFmpeg 8. Without the lib, torchcodec enters an unbounded
# load/retry loop and `from vllm import LLM` hangs forever rather than failing.
# PyNvVideoCodec (already a vLLM dependency) bundles the complete FFmpeg 8 set,
# so pointing at it fixes the import in ~3.5s. Do not "fix" this by uninstalling
# torchcodec: `uv run` re-syncs and would silently undo it.
set -euo pipefail

cd "$(dirname "$0")/.."
VENV="$PWD/.venv"
export LD_LIBRARY_PATH="$VENV/lib/python3.12/site-packages/PyNvVideoCodec:${LD_LIBRARY_PATH:-}"
# The engine JIT-compiles kernels in subprocesses and invokes `ninja` by name,
# so the venv's bin must be on PATH or engine init dies with FileNotFoundError.
export PATH="$VENV/bin:$PATH"

MODEL="${MODEL:-Qwen/Qwen3.5-2B}"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-8192}"
GPU_UTIL="${GPU_UTIL:-0.85}"

echo "serving $MODEL on :$PORT (max_len=$MAX_LEN, gpu_util=$GPU_UTIL)"
exec "$VENV/bin/vllm" serve "$MODEL" \
  --port "$PORT" \
  --max-model-len "$MAX_LEN" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --dtype bfloat16
