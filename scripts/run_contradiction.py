"""Contradiction test: when the system prompt and the reasoning-spec disagree,
which one does the output follow?

E4.1 was flawed: it surfaced the SAME constraint already in the user prompt, so
the near-ceiling compliance only shows the model obeys explicit instructions and
says nothing about whether the reasoning-spec has causal power. This isolates
that power by making the spec CONTRADICT a standing rule.

Dimension: case (cleanest binary — all-lowercase vs ALL-CAPS, unambiguously
checkable). Neutral task (a short poem), never mentions case.

Six conditions:
  sys_upper_only     system says ALL CAPS, no spec            -> does the rule work?
  sys_lower_only     system says all lowercase, no spec       -> does the rule work?
  spec_upper_only    no system rule, reasoning-spec = UPPER   -> does the spec alone work?
  spec_lower_only    no system rule, reasoning-spec = lower   -> does the spec alone work?
  sys_upper_spec_lower  system ALL CAPS  +  reasoning-spec lower  -> CONTRADICTION
  sys_lower_spec_upper  system lowercase +  reasoning-spec UPPER  -> CONTRADICTION

The two contradiction cells are the point: output all-caps => the standing rule
won; output all-lowercase => the reasoning-spec won.

    uv run python scripts/run_contradiction.py --model Qwen/Qwen3.5-2B --samples 6
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.runstore import RunWriter  # noqa: E402

TOPICS = ["the sea in winter", "a city at dawn", "an old train", "falling snow",
          "the moon over water", "a crowded market", "autumn leaves",
          "a mountain village", "a river in spring", "a quiet harbour",
          "the first frost", "a summer storm", "an empty street",
          "a field of wheat", "the northern lights"]

SYS_UPPER = "Always write your entire response in ALL CAPITAL LETTERS."
SYS_LOWER = "Always write your entire response in all lowercase letters, with no capital letters at all."
SPEC_UPPER = "case: upper -- I will write the entire response in ALL CAPITAL LETTERS."
SPEC_LOWER = "case: lower -- I will write the entire response in all lowercase, no capitals."
STOP = ["<|im_end|>", "<turn|>", "<end_of_turn>"]

# condition -> (system_text, spec_text)  ; spec None means no reasoning injection
CONDITIONS = {
    "sys_upper_only": (SYS_UPPER, None),
    "sys_lower_only": (SYS_LOWER, None),
    "spec_upper_only": (None, SPEC_UPPER),
    "spec_lower_only": (None, SPEC_LOWER),
    "sys_upper_spec_lower": (SYS_UPPER, SPEC_LOWER),
    "sys_lower_spec_upper": (SYS_LOWER, SPEC_UPPER),
}


def call(job):
    url, model, prompt, mt, temp, top_p, seed = job
    body = json.dumps({"model": model, "prompt": prompt, "temperature": temp,
                       "top_p": top_p, "max_tokens": mt, "seed": seed,
                       "stop": STOP}).encode()
    req = urllib.request.Request(f"{url}/v1/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            d = json.loads(resp.read())
        c = d["choices"][0]
        return c["text"], c.get("finish_reason")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {exc}", file=sys.stderr)
        return None, None


def split_answer(text):
    for m in ("</think>", "<channel|>"):
        if m in text:
            return text.split(m, 1)[1].lstrip()
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--code-version", default=None)
    a = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)

    def build(topic, system, spec):
        user = f"Write a four-line poem about {topic}."
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": user}]
        think = spec is not None
        try:
            s = tok.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True, enable_thinking=think)
        except TypeError:
            s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        if "<|think|>" in s and "<|channel>thought" not in s:
            s += "<|channel>thought\n"
        if spec is not None:
            close = "<channel|>" if "<|channel>thought" in s else "</think>"
            s += f"<conventions>\n{spec}\n</conventions>\n{close}\n\n"
        return s

    jobs, meta = [], []
    for topic in TOPICS:
        for cond, (system, spec) in CONDITIONS.items():
            p = build(topic, system, spec)
            for s in range(a.samples):
                jobs.append((a.url, a.model, p, a.max_tokens, a.temperature, a.top_p, s))
                meta.append((topic, cond, s))
    print(f"{len(jobs)} generations ({len(CONDITIONS)} conditions)", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        out = list(pool.map(call, jobs))

    run_id = a.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-contra-{a.model.split('/')[-1]}"
    m = {"script": "run_contradiction.py", "model": a.model, "samples": a.samples,
         "sampling": {"temperature": a.temperature, "top_p": a.top_p,
                      "max_tokens": a.max_tokens},
         "conditions": {k: {"system": v[0], "spec": v[1]} for k, v in CONDITIONS.items()},
         "code_version": a.code_version}
    with RunWriter(run_id, m) as w:
        for (topic, cond, s), (text, fin) in zip(meta, out):
            if text is None:
                continue
            w.write({"item_key": f"{topic}", "condition": cond, "sample": s,
                     "answer": split_answer(text), "finish_reason": fin})
    print(f"stored runs/{run_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
