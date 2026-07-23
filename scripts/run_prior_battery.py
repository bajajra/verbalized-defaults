"""E4.1 runner: does surfacing a default help the model override it?

Three conditions per prompt, on the collision battery:

  vanilla        the instruction alone. Does the prior win?
  oracle_declare the explicit constraint injected into the reasoning channel as a
                 plain-English convention. Does surfacing help override the prior?
  self_declare   the model states its own conventions first (concrete cue), then
                 answers. Does the model's OWN surfacing help? -- closest to the
                 trained system.

Generation only; stored to the runstore. Scoring is downstream.

    uv run python scripts/run_prior_battery.py --model Qwen/Qwen3.5-2B --samples 4
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

SELF_CUE = (
    "Before writing your answer, state the concrete conventions your response "
    "will follow -- length, capitalisation, structure, and any requirement the "
    "request states. One per line. Then write the response itself."
)
STOP = ["<|im_end|>", "<turn|>", "<end_of_turn>"]
DECL_OPEN, DECL_CLOSE = "<conventions>", "</conventions>"


def render_constraint(check: dict) -> str:
    """Plain-English restatement of the explicit constraint, for oracle_declare."""
    lines = []
    if check.get("case") == "lower":
        lines.append("Write the entire response in lowercase. Do not use any "
                     "capital letters anywhere, including proper nouns and any "
                     "postscript marker.")
    if "must_include_ci" in check:
        lines.append("Include a postscript, written in lowercase.")
    if "structure_bullets" in check:
        lines.append(f"Include exactly {check['structure_bullets']} bullet points "
                     "in total across the whole response.")
    if "length_words_min" in check:
        lines.append(f"Write at least {check['length_words_min']} words.")
    return "\n".join(f"- {ln}" for ln in lines)


def call(job):
    url, model, prompt, max_tokens, temp, top_p, seed, stop = job
    body = json.dumps({"model": model, "prompt": prompt, "temperature": temp,
                       "top_p": top_p, "max_tokens": max_tokens, "seed": seed,
                       "stop": stop}).encode()
    req = urllib.request.Request(f"{url}/v1/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            d = json.loads(resp.read())
        c = d["choices"][0]
        return c["text"], c.get("finish_reason")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {exc}", file=sys.stderr)
        return None, None


def split_answer(text: str) -> str:
    for m in ("</think>", "<channel|>"):
        if m in text:
            return text.split(m, 1)[1].lstrip()
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--code-version", default=None)
    a = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    battery = [json.loads(l) for l in open(ROOT / "data" / "prior_battery.jsonl")]

    def tmpl(user, think, system=None):
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": user}]
        try:
            s = tok.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True, enable_thinking=think)
        except TypeError:
            s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        if "<|think|>" in s and "<|channel>thought" not in s:
            s += "<|channel>thought\n"
        return s

    probe = tmpl("x", True)
    close = "<channel|>" if "<|channel>thought" in probe else "</think>"

    # build phase-1 (self_declare needs a declaration first); others are one-shot
    jobs, meta = [], []
    for it in battery:
        constraint_nl = render_constraint(it["check"])
        for s in range(a.samples):
            # vanilla
            jobs.append((a.url, a.model, tmpl(it["prompt"], False), a.max_tokens,
                         a.temperature, a.top_p, s, STOP))
            meta.append((it, "vanilla", s))
            # oracle_declare: constraint restated inside a closed reasoning block
            od = tmpl(it["prompt"], True) + constraint_nl + "\n" + close + "\n\n"
            jobs.append((a.url, a.model, od, a.max_tokens, a.temperature, a.top_p, s, STOP))
            meta.append((it, "oracle_declare", s))

    print(f"one-shot conditions: {len(jobs)} generations", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        oneshot = list(pool.map(call, jobs))

    # self_declare: phase 1 elicit, phase 2 answer
    p1, p1meta = [], []
    for it in battery:
        base = tmpl(it["prompt"], True, SELF_CUE) + DECL_OPEN + "\n"
        for s in range(a.samples):
            p1.append((a.url, a.model, base, 512, a.temperature, a.top_p, s,
                       STOP + [DECL_CLOSE]))
            p1meta.append((it, base, s))
    print(f"self_declare phase 1: {len(p1)}", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        decls = list(pool.map(call, p1))
    p2 = []
    for (it, base, s), (dt, _f) in zip(p1meta, decls):
        p2.append((a.url, a.model, base + (dt or "").strip() + "\n" + DECL_CLOSE
                   + "\n" + close + "\n", a.max_tokens, a.temperature, a.top_p, s, STOP))
    print(f"self_declare phase 2: {len(p2)}", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        answers = list(pool.map(call, p2))

    run_id = a.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-e41-{a.model.split('/')[-1]}"
    m = {"script": "run_prior_battery.py", "model": a.model, "samples": a.samples,
         "sampling": {"temperature": a.temperature, "top_p": a.top_p,
                      "max_tokens": a.max_tokens},
         "n_prompts": len(battery), "code_version": a.code_version}
    with RunWriter(run_id, m) as w:
        for (it, cond, s), (text, fin) in zip(meta, oneshot):
            if text is None:
                continue
            w.write({"item_key": it["key"], "prior": it["prior"], "condition": cond,
                     "sample": s, "check": it["check"], "user_prompt": it["prompt"],
                     "answer": split_answer(text), "finish_reason": fin})
        for (it, base, s), (dt, _df), (text, fin) in zip(p1meta, decls, answers):
            if text is None:
                continue
            w.write({"item_key": it["key"], "prior": it["prior"],
                     "condition": "self_declare", "sample": s, "check": it["check"],
                     "user_prompt": it["prompt"], "declaration": dt,
                     "answer": text, "finish_reason": fin})
    print(f"stored runs/{run_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
