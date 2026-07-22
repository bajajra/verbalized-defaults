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
from verbalized_defaults.spec_nl import format_spec_natural  # noqa: E402
from verbalized_defaults.spec_text import format_spec  # noqa: E402

# Factorial over three things E0.1 previously confounded:
#   notation  typed <spec> DSL  vs  plain-English requirement list
#   placement inside the reasoning block  vs  as a response header
#   hint      with a system prompt explaining the block  vs  without
# Without a system prompt the model has never seen this DSL, so a null result
# there measures "can it reverse-engineer an undocumented notation", not H0.
CONDITIONS = [
    "vanilla",
    "typed_think", "typed_think_sys", "typed_prefix_sys",
    "nl_think", "nl_think_sys", "nl_prefix_sys",
    # Model-agnostic placement: the spec lives in the system prompt. Needed
    # because Gemma has no <think>/</think> tokens, so the reasoning-block
    # placement -- the one that actually worked on Qwen -- does not transfer.
    # These two are the only cross-model comparable spec conditions.
    "typed_insys", "nl_insys",
    "vanilla_think_open",
]
DIAGNOSTIC_ONLY = {"vanilla_think_open"}
# The best case for H0: constraints stated in plain English, with the model
# explicitly told to follow them. If surfacing helps at all, it helps here.
BEST_CASE = "nl_think_sys"

SYS_TYPED = (
    "Before your answer you are given a <spec> block listing the output "
    "conventions your response must satisfy. Each line is `slot: value`. "
    "Follow every line of the spec exactly. Do not mention or repeat the spec "
    "in your answer."
)
SYS_NL = (
    "Before your answer you are given a list of requirements your response must "
    "satisfy. Follow every requirement exactly. Do not mention or repeat the "
    "requirements in your answer."
)
# Conditions whose *generated text* contains an open reasoning block that the
# model must close itself. The no-think template already closes it in the
# prompt, so its generation legitimately has no </think> -- do not count that as
# a failure (an earlier `endswith("think")` check wrongly matched
# "vanilla_nothink" and reported 40/40 unclosed).
THINKING_CONDITIONS = {"vanilla_think_open"}


def build_prompts(tok, user_prompt: str, typed: str | None,
                  natural: str | None) -> dict[str, str]:
    def tmpl(think: bool, system: str | None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else [])
        msgs = msgs + [{"role": "user", "content": user_prompt}]
        try:
            return tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True,
                                           enable_thinking=think)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True)

    out = {"vanilla": tmpl(False, None)}

    # Two different reasoning-channel conventions, both injectable:
    #   Qwen  -- template leaves "<think>" open; the model closes with "</think>"
    #   Gemma -- "<|think|>" in the system turn; the model emits
    #            "<|channel>thought ... <channel|>" then the answer
    # An earlier version only looked for "<think>" and wrongly concluded Gemma
    # had no reasoning channel, which silently dropped its strongest condition.
    t_think = tmpl(True, None)
    if "<think>" in t_think and "</think>" not in t_think:
        think_open, think_close = "", "\n</think>\n\n"
    elif "<|think|>" in t_think:
        think_open, think_close = "<|channel>thought\n", "\n<channel|>\n\n"
    else:
        think_open = think_close = None

    if think_open is not None:
        out["vanilla_think_open"] = t_think

    if not typed:
        return out

    out["typed_insys"] = tmpl(False, SYS_TYPED + "\n\n" + typed)
    out["typed_prefix_sys"] = tmpl(False, SYS_TYPED) + typed + "\n\n"
    if natural:
        out["nl_insys"] = tmpl(False, SYS_NL + "\n\n" + natural)
        out["nl_prefix_sys"] = tmpl(False, SYS_NL) + natural + "\n\n"
    if think_open is None:
        return out
    out["typed_think"] = tmpl(True, None) + think_open + typed + think_close
    out["typed_think_sys"] = tmpl(True, SYS_TYPED) + think_open + typed + think_close
    if natural:
        out["nl_think"] = tmpl(True, None) + think_open + natural + think_close
        out["nl_think_sys"] = tmpl(True, SYS_NL) + think_open + natural + think_close
    return out



def repetition_rate(text: str, n: int = 10) -> float:
    """Fraction of duplicated n-grams: a direct degeneracy measure.

    Truncation was previously used as a proxy for repetition, which conflates
    two different things (a long compliant answer also truncates). This measures
    looping directly: 0.0 = every n-gram unique, ->1.0 = heavily repetitive.
    """
    toks = text.split()
    if len(toks) < n * 2:
        return 0.0
    grams = [tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)]
    return round(1.0 - len(set(grams)) / len(grams), 4)


def extract_answer(text: str) -> tuple[str, bool]:
    """Return (scored answer, closed_think). Answer is whatever follows </think>."""
    for marker in ("</think>", "<channel|>"):
        if marker in text:
            return text.split(marker, 1)[1].lstrip(), True
    return text, False


def call(job):
    url, model, prompt, max_tokens, temp, stop, top_p, seed = job
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
    # Single-sample runs at temp 1.0 were NOT reproducible: identical configs
    # moved every condition by 0.02-0.07 between runs, larger than the effects
    # being measured. Multiple samples per prompt are mandatory, not optional.
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--conditions", default="",
                    help="comma-separated subset of CONDITIONS to run")
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
        has_spec = bool(res.spec.provenance)
        spec_block = format_spec(res.spec) if has_spec else None
        nl_block = format_spec_natural(res.spec) if has_spec else None
        prompts = build_prompts(tok, row["prompt"], spec_block, nl_block or None)
        wanted = [c.strip() for c in a.conditions.split(",") if c.strip()] or CONDITIONS
        for cond in wanted:
            if cond not in prompts:
                continue
            for s in range(a.samples):
                jobs.append((a.url, a.model, prompts[cond], a.max_tokens,
                             a.temperature, ["<|im_end|>", "<turn|>", "<end_of_turn>"], a.top_p, s))
                meta.append((row, cond, s))
    print(f"{len(jobs)} generations across {len(CONDITIONS)} conditions "
          f"({untyped_rows} rows carry >=1 untyped constraint in `other`)")

    # Stream results to disk as they arrive. The previous version buffered
    # everything and wrote once at the end, so a crash at hour two lost the
    # entire run and there was no way to watch progress.
    results = []
    raw_fh = open(a.raw, "w")
    done = 0
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        for (row, cond, sample), (text, finish) in zip(meta, pool.map(call, jobs)):
            results.append((text, finish))
            done += 1
            if text is not None:
                answer, closed = extract_answer(text)
                raw_fh.write(json.dumps({
                    "key": row.get("key"), "condition": cond, "sample": sample,
                    "instruction_ids": row["instruction_id_list"],
                    "closed_think": closed, "finish_reason": finish,
                    "repetition": repetition_rate(answer),
                    "answer": answer[:4000],
                }) + "\n")
            if done % 500 == 0:
                raw_fh.flush()
                print(f"  {done}/{len(jobs)} ({done/len(jobs):.0%})", flush=True)
    raw_fh.close()

    by_cond: dict[str, list] = {c: [] for c in CONDITIONS}
    unclosed = Counter()
    truncated = Counter()
    rep_by_cond: dict[str, list] = {c: [] for c in CONDITIONS}
    scored = []
    for (row, cond, sample), (text, finish) in zip(meta, results):
        if text is None:
            continue
        answer, closed = extract_answer(text)
        if cond in THINKING_CONDITIONS and not closed:
            unclosed[cond] += 1
        if finish == "length":
            truncated[cond] += 1
        rep_by_cond[cond].append(repetition_rate(answer))
        s = score_prompt(row["prompt"], row["instruction_id_list"],
                         row.get("kwargs"), answer, key=row.get("key"))
        by_cond[cond].append(s)
        scored.append((row.get("key"), cond, sample, s.strict_all, s.loose_all))
    # fold the strict/loose verdicts back into the streamed raw file
    lines = [json.loads(x) for x in open(a.raw, encoding="utf-8")]
    for ln, (_k, _c, _s, st, lo) in zip(lines, scored):
        ln["strict"], ln["loose"] = st, lo
    with open(a.raw, "w") as fh:
        for ln in lines:
            fh.write(json.dumps(ln) + "\n")

    summary = {c: aggregate(v) for c, v in by_cond.items() if v}
    import statistics as _st
    rep_summary = {c: {
        "mean": round(_st.mean(v), 4),
        "frac_over_0.3": round(sum(x > 0.3 for x in v) / len(v), 4),
    } for c, v in rep_by_cond.items() if v}
    payload = {"model": a.model, "n_rows": len(rows), "temperature": a.temperature,
               "repetition": rep_summary,
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
    print(f"\n--- degeneracy: duplicated 10-gram rate (temp={a.temperature}) ---")
    for c in CONDITIONS:
        if c in rep_summary:
            r = rep_summary[c]
            print(f"  {c:20s} mean {r['mean']:.4f}   looping(>0.3) {r['frac_over_0.3']:6.1%}")

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
    for cond in CONDITIONS:
        if cond in ("vanilla",) or cond in DIAGNOSTIC_ONLY or cond not in summary:
            continue
        star = "  <== best case for H0" if cond == BEST_CASE else ""
        print(f"  {cond:18s} - vanilla : "
              f"strict {delta(cond, 'vanilla', 'prompt_strict'):+.4f}   "
              f"loose {delta(cond, 'vanilla', 'prompt_loose'):+.4f}{star}")
    print("  gate: >=+0.05 proceed | <+0.02 H0 falsified, pivot to execution")
    if unclosed:
        print(f"\n  NOTE unclosed <think> blocks: {dict(unclosed)} "
              "(answer fell back to full text)")
    print(f"\nwrote {a.out} and {a.raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
