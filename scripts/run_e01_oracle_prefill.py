"""E0.1 -- oracle spec prefill on IFEval. The Gate 1 measurement.

Question: if the model were handed a *perfect* spec of the prompt's constraints,
how much better would it follow them? That upper-bounds how much of instruction
following is a *surfacing* problem (H0) rather than an execution problem.

Four conditions, so each prefill mode is compared against its OWN matched
baseline -- otherwise a thinking-vs-not difference would be confounded with the
spec effect:

    vanilla_nothink   template(enable_thinking=False)
    vanilla_think     template(enable_thinking=True)
    spec_think        (a) spec prefilled INSIDE the reasoning block
    spec_prefix       (b) spec prefilled as a response header, no-think

The oracle spec comes from `ifeval_adapter` (benchmark metadata, never a model).
Scoring uses IFEval's own checkers via `ifeval_score`.

Because the spec sits in the *prompt* in both modes, it never appears in the
generated text, so nothing has to be stripped before scoring. For the thinking
conditions the scored answer is whatever follows `</think>`.

    uv run python scripts/run_e01_oracle_prefill.py --limit 120
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402
from verbalized_defaults.ifeval_score import (  # noqa: E402
    aggregate,
    load_ifeval_rows,
    score_prompt,
)
from verbalized_defaults.spec_text import format_spec  # noqa: E402

CONDITIONS = ["vanilla", "vanilla_think_open", "spec_think", "spec_prefix"]
# Excluded from the Gate 1 comparison (see build_prompts).
DIAGNOSTIC_ONLY = {"vanilla_think_open"}
# Conditions whose *generated text* contains an open reasoning block that the
# model must close itself. The no-think template already closes it in the
# prompt, so its generation legitimately has no </think> -- do not count that as
# a failure (an earlier `endswith("think")` check wrongly matched
# "vanilla_nothink" and reported 40/40 unclosed).
THINKING_CONDITIONS = {"vanilla_think_open"}


def build_prompts(tok, user_prompt: str, spec_block: str | None) -> dict[str, str]:
    msgs = [{"role": "user", "content": user_prompt}]

    def tmpl(think: bool) -> str:
        try:
            return tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True,
                                           enable_thinking=think)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True)

    out = {
        "vanilla": tmpl(False),
        # Diagnostic only, excluded from the Gate 1 comparison: with the block
        # left open this model writes its reasoning as plain prose and never
        # emits </think>, so the reasoning pollutes the scored answer. Kept to
        # document that failure rather than hide it.
        "vanilla_think_open": tmpl(True),
    }
    if spec_block:
        # (a) spec inside a reasoning block that WE close, so the model emits
        # only the answer and the spec can never pollute the scored output.
        out["spec_think"] = tmpl(True) + spec_block + "\n</think>\n\n"
        # (b) spec as a visible response header, no-think.
        out["spec_prefix"] = tmpl(False) + spec_block + "\n\n"
    return out


def extract_answer(text: str) -> tuple[str, bool]:
    """Return (scored answer, closed_think). Answer is whatever follows </think>."""
    if "</think>" in text:
        return text.split("</think>", 1)[1].lstrip(), True
    return text, False


def call(job):
    url, model, prompt, max_tokens, temp, stop, top_p = job
    body = json.dumps({"model": model, "prompt": prompt, "temperature": temp,
                       "top_p": top_p, "max_tokens": max_tokens, "seed": 0,
                       "stop": stop}).encode()
    req = urllib.request.Request(f"{url}/v1/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            d = json.loads(resp.read())
        c = d["choices"][0]
        return c["text"], c.get("finish_reason")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! request failed: {exc}", file=sys.stderr)
        return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=2048)
    # Greedy decoding is NOT safe here: at temperature 0 this model falls into
    # verbatim repetition loops that blow the token budget, which inflated
    # truncation in the spec conditions and corrupted an earlier run. Qwen's
    # documented recommendation is sampling, so that is the default.
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--out", default=str(ROOT / "data" / "e01_results.json"))
    ap.add_argument("--raw", default=str(ROOT / "data" / "e01_raw.jsonl"))
    a = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)

    rows = load_ifeval_rows(limit=a.limit)
    print(f"IFEval rows: {len(rows)}  model: {a.model}")

    # Build the oracle spec per row, and record how much of it is typed.
    jobs, meta = [], []
    untyped_rows = 0
    for row in rows:
        res = spec_from_ifeval(row["instruction_id_list"], row.get("kwargs"))
        if res.unmapped:
            untyped_rows += 1
        spec_block = format_spec(res.spec) if res.spec.provenance else None
        prompts = build_prompts(tok, row["prompt"], spec_block)
        for cond in CONDITIONS:
            if cond not in prompts:
                continue
            jobs.append((a.url, a.model, prompts[cond], a.max_tokens,
                         a.temperature, ["<|im_end|>", "<turn|>"], a.top_p))
            meta.append((row, cond))
    print(f"{len(jobs)} generations across {len(CONDITIONS)} conditions "
          f"({untyped_rows} rows carry >=1 untyped constraint in `other`)")

    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        results = list(pool.map(call, jobs))

    by_cond: dict[str, list] = {c: [] for c in CONDITIONS}
    unclosed = Counter()
    truncated = Counter()
    raw_fh = open(a.raw, "w")
    for (row, cond), (text, finish) in zip(meta, results):
        if text is None:
            continue
        answer, closed = extract_answer(text)
        if cond in THINKING_CONDITIONS and not closed:
            unclosed[cond] += 1
        if finish == "length":
            truncated[cond] += 1
        s = score_prompt(row["prompt"], row["instruction_id_list"],
                         row.get("kwargs"), answer, key=row.get("key"))
        by_cond[cond].append(s)
        raw_fh.write(json.dumps({
            "key": row.get("key"), "condition": cond,
            "instruction_ids": row["instruction_id_list"],
            "strict": s.strict_all, "loose": s.loose_all,
            "closed_think": closed, "finish_reason": finish,
            "answer": answer[:4000],
        }) + "\n")
    raw_fh.close()

    summary = {c: aggregate(v) for c, v in by_cond.items() if v}
    payload = {"model": a.model, "n_rows": len(rows), "temperature": a.temperature,
               "max_tokens": a.max_tokens,
               "unclosed_think": dict(unclosed), "truncated": dict(truncated),
               "conditions": summary}
    pathlib.Path(a.out).write_text(json.dumps(payload, indent=2))

    print(f"\n{'condition':18s} {'n':>5s} {'strict':>8s} {'loose':>8s} "
          f"{'inst-strict':>12s} {'trunc':>6s}")
    print("-" * 62)
    for c in CONDITIONS:
        s = summary.get(c)
        if not s:
            continue
        print(f"{c:18s} {s['n_prompts']:5d} {s['prompt_strict']:8.4f} "
              f"{s['prompt_loose']:8.4f} {s['instruction_strict']:12.4f} "
              f"{truncated[c]:6d}")

    def delta(a_, b_, k):
        if a_ in summary and b_ in summary:
            return summary[a_][k] - summary[b_][k]
        return float("nan")

    # Truncation is a validity threat, not a footnote: a condition that runs out
    # of budget mid-reasoning scores ~0 for reasons unrelated to instruction
    # following, so an unbalanced truncation rate invalidates the comparison.
    print("\n--- truncation check (validity gate) ---")
    worst = 0.0
    for c in CONDITIONS:
        if c not in summary:
            continue
        rate = truncated[c] / max(1, summary[c]["n_prompts"])
        if c not in DIAGNOSTIC_ONLY:
            worst = max(worst, rate)
        flag = "  <-- HIGH" if rate > 0.10 else ""
        print(f"  {c:18s} {truncated[c]:4d} ({rate:5.1%}){flag}")
    if worst > 0.10:
        print("  !! comparison is CONFOUNDED by truncation; raise --max-tokens "
              "and re-run before reading any lift below as a Gate 1 result.")

    print("\n--- GATE 1 (oracle-prefill lift, prompt-strict) ---")
    for label, cond in (("(a) spec_think ", "spec_think"),
                        ("(b) spec_prefix", "spec_prefix")):
        print(f"  {label} - vanilla : "
              f"strict {delta(cond, 'vanilla', 'prompt_strict'):+.4f}   "
              f"loose {delta(cond, 'vanilla', 'prompt_loose'):+.4f}")
    print("  gate: >=+0.05 proceed | <+0.02 H0 falsified, pivot to execution")
    if unclosed:
        print(f"\n  NOTE unclosed <think> blocks: {dict(unclosed)} "
              "(answer fell back to full text)")
    print(f"\nwrote {a.out} and {a.raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
