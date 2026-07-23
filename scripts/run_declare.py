"""Two-phase declare-then-answer generation, stored raw and complete.

Generation only. **No metric is computed or stored here** — everything derivable
(binding, self-consistency, scoring) is recomputed downstream from the stored
text, so a change in analysis code can never leave stale numbers on disk. That
rule exists because it was violated: frozen summaries silently went stale when
the extractor changed, and one comparison mixed two instrument versions.

Protocol (unchanged from run_spec_emission, which this supersedes):
  phase 1 — prompt ends with `<conventions>`; generation stops at the closing tag,
            so the declaration boundary is one WE control. Models do not reliably
            close their own reasoning blocks.
  phase 2 — the model's own declaration is fed back, the reasoning block is
            closed, and it writes the answer.

    uv run python scripts/run_declare.py --source ifeval --limit 300 --samples 3
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

from verbalized_defaults.ifeval_score import load_ifeval_rows  # noqa: E402
from verbalized_defaults.runstore import RunWriter  # noqa: E402

SYS_CUE = (
    "Before writing your answer, state the concrete conventions your response "
    "will follow. Give SPECIFIC VALUES, not vague advice. Cover: approximately "
    "how many words; how many paragraphs; whether you use bullet points and "
    "exactly how many; the capitalisation you use; the language you write in; "
    "and any requirement the request itself states. Also commit to the "
    "dimensions the request does NOT mention -- pick a definite value anyway. "
    "Write one convention per line, each with a number or a definite choice, "
    "for example 'About 400 words.' or 'Use 5 bullet points.' or 'Standard "
    "capitalization.'. Then write the response itself."
)
SOFT_CUE = (
    "Before writing your answer, think briefly about the conventions your "
    "response will follow -- how long it will be, how it will be structured and "
    "formatted, and how it will read. Include the conventions the request does "
    "not mention. Write one convention per line. Then write the response itself."
)
DECL_OPEN, DECL_CLOSE = "<conventions>", "</conventions>"
STOP = ["<|im_end|>", "<turn|>", "<end_of_turn>"]


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
        return c["text"], c.get("finish_reason"), d.get("usage")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {exc}", file=sys.stderr)
        return None, None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--source", choices=["ifeval", "genres"], default="ifeval")
    ap.add_argument("--cue", choices=["concrete", "soft"], default="concrete")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--decl-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--concurrency", type=int, default=48)
    # The GPU box is an rsync'd working copy with no commit history, so its own
    # git state is meaningless ("HEAD", always dirty). The authoritative code
    # version comes from the machine that launched the run and is passed in.
    ap.add_argument("--code-version", default=None,
                    help="git sha of the canonical repo that produced this code")
    a = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    cue = SYS_CUE if a.cue == "concrete" else SOFT_CUE

    if a.source == "ifeval":
        rows = load_ifeval_rows(limit=a.limit)
        items = [{"key": r.get("key"), "prompt": r["prompt"],
                  "instruction_id_list": r["instruction_id_list"],
                  "kwargs": r.get("kwargs")} for r in rows]
    else:
        spec = json.loads((ROOT / "data" / "genre_prompts.json").read_text())["genres"]
        items = [{"key": f"{g}:{i}", "prompt": p, "genre": g}
                 for g, ps in spec.items() for i, p in enumerate(ps)][: a.limit]

    def build(user_prompt: str) -> str:
        msgs = [{"role": "system", "content": cue},
                {"role": "user", "content": user_prompt}]
        try:
            s = tok.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True, enable_thinking=True)
        except TypeError:
            s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        if "<|think|>" in s and "<|channel>thought" not in s:
            s += "<|channel>thought\n"
        return s

    close_reasoning = "<channel|>" if "<|channel>thought" in build("x") else "</think>"

    run_id = a.run_id or (f"{time.strftime('%Y%m%d-%H%M%S')}-"
                          f"{a.source}-{a.cue}-{a.model.split('/')[-1]}")
    meta = {
        "script": "run_declare.py", "model": a.model, "url": a.url,
        "source": a.source, "cue": a.cue, "limit": a.limit, "samples": a.samples,
        "sampling": {"temperature": a.temperature, "top_p": a.top_p,
                     "max_tokens": a.max_tokens, "decl_tokens": a.decl_tokens},
        "n_items": len(items), "close_reasoning": close_reasoning,
        "cue_text": cue,
        "code_version": a.code_version,
    }

    p1, meta_rows = [], []
    for it in items:
        base = build(it["prompt"]) + DECL_OPEN + "\n"
        for s in range(a.samples):
            p1.append((a.url, a.model, base, a.decl_tokens, a.temperature,
                       a.top_p, s, STOP + [DECL_CLOSE]))
            meta_rows.append((it, base, s))
    print(f"run {run_id}\nphase 1: {len(p1)} declarations", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        decls = list(pool.map(call, p1))

    p2 = []
    for (it, base, s), (dtext, _f, _u) in zip(meta_rows, decls):
        prompt = base + (dtext or "").strip() + "\n" + DECL_CLOSE + "\n" + close_reasoning + "\n"
        p2.append((a.url, a.model, prompt, a.max_tokens, a.temperature, a.top_p, s, STOP))
    print(f"phase 2: {len(p2)} answers", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        answers = list(pool.map(call, p2))

    n_fail = 0
    with RunWriter(run_id, meta) as w:
        for (it, base, s), (dtext, dfin, dus), (atext, afin, aus) in zip(
                meta_rows, decls, answers):
            if dtext is None or atext is None:
                n_fail += 1
                continue
            w.write({
                "item_key": it["key"],
                "condition": f"{a.source}:{a.cue}",
                "sample": s,
                "genre": it.get("genre"),
                "instruction_id_list": it.get("instruction_id_list"),
                "kwargs": it.get("kwargs"),
                "user_prompt": it["prompt"],
                # phase-2 prompt is exactly:
                #   phase1_prompt + declaration + DECL_CLOSE + close_reasoning
                # so it is reconstructible from what is stored plus meta.json,
                # and is not duplicated here.
                "phase1_prompt": base,
                # FULL text, never truncated -- truncating answers at 2000 chars
                # made 30% of an earlier run unscoreable.
                "declaration": dtext,
                "answer": atext,
                "decl_finish_reason": dfin,
                "finish_reason": afin,
                "decl_usage": dus,
                "usage": aus,
            })
    print(f"failed requests: {n_fail}")
    print(f"stored: runs/{run_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
