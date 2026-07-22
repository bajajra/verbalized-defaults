"""E0.2 / E0.3 -- make the model DECLARE its own conventions, then check it.

Everything before this point handed the model a spec. This is the first
experiment where the model produces one, which is what the trained system must
actually do. Two questions, one run:

* **E0.2 binding** (--source ifeval): does the declaration capture the
  constraints the prompt actually stated? Scored against the adapter's ground
  truth. This is the "never registered" rate the taxonomy predicted.
* **E0.3 calibration** (--source genres): on prompts that constrain nothing, the
  model declares its own *defaults* -- then we check whether the response obeys
  them. **This is the first `[assumed]` measurement in the project.** The design
  gates RLVR on it: if self-consistency is already very high, the R_exec signal
  on assumed slots is thin and should not be built.

The declaration is elicited in the reasoning channel by a system-prompt cue, and
is requested in **plain English**, not the typed DSL -- E0.1 showed the DSL costs
4-6 points to read, and there is no reason to expect it is easier to write. The
typed Spec is *derived* from the English by ``spec_extract`` (the hybrid), so
verification stays mechanical.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402
from verbalized_defaults.ifeval_score import load_ifeval_rows  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402
from verbalized_defaults.verifiers import verify_spec  # noqa: E402

# The cue. Deliberately asks for the unspecified dimensions too -- that is where
# the latent defaults live and the whole point of the project.
# The cue. An earlier, softer version ("think about the conventions your response
# will follow") produced only *qualitative* style guidance -- "be clear and
# direct", "keep sentences relatively short", "maintain an objective tone" --
# which is a genuine verbalized default but carries no value a verifier can
# check (extraction coverage 2%). Asking for concrete values is fair: the
# proposal's spec holds point values, so eliciting them is the interface being
# tested, not a thumb on the scale.
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


# Two controlled phases instead of one free-running generation.
#
# Letting the model open its own reasoning block and close it does not work:
# Qwen writes "Thinking Process: ..." as plain prose and never emits </think>,
# so an 83% no-declaration rate in the first smoke test was an artefact of
# unparseable output, not of the model failing to declare. Instead we bound the
# declaration with a delimiter WE control and stop on it, then feed the model's
# own declaration back to it and generate the answer. Deterministic, works
# identically on both model families, and mirrors what a trained model would do:
# emit the spec, then honour it.
DECL_OPEN = "<conventions>"
DECL_CLOSE = "</conventions>"


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--source", choices=["ifeval", "genres"], default="genres")
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=3072)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--out", default=str(ROOT / "data" / "spec_emission.json"))
    ap.add_argument("--raw", default=str(ROOT / "data" / "spec_emission.jsonl"))
    a = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)

    if a.source == "ifeval":
        rows = load_ifeval_rows(limit=a.limit)
        items = [{"key": r.get("key"), "prompt": r["prompt"], "row": r} for r in rows]
    else:
        spec = json.loads((ROOT / "data" / "genre_prompts.json").read_text())["genres"]
        items = [{"key": f"{g}:{i}", "prompt": p, "genre": g, "row": None}
                 for g, ps in spec.items() for i, p in enumerate(ps)][: a.limit]

    def build(user_prompt: str) -> str:
        msgs = [{"role": "system", "content": SYS_CUE},
                {"role": "user", "content": user_prompt}]
        try:
            s = tok.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True, enable_thinking=True)
        except TypeError:
            s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        # Gemma needs the thought channel opened explicitly; Qwen's template
        # already leaves <think> open.
        if "<|think|>" in s and "<|channel>thought" not in s:
            s += "<|channel>thought\n"
        return s

    probe = build("x")
    close_reasoning = "<channel|>" if "<|channel>thought" in probe else "</think>"

    STOP = ["<|im_end|>", "<turn|>", "<end_of_turn>"]

    # phase 1 -- elicit the declaration, bounded by our own close marker
    p1_jobs, meta = [], []
    for it in items:
        base = build(it["prompt"]) + DECL_OPEN + "\n"
        for s in range(a.samples):
            p1_jobs.append((a.url, a.model, base, 512, a.temperature, a.top_p, s,
                            STOP + [DECL_CLOSE]))
            meta.append((it, base, s))
    print(f"phase 1: {len(p1_jobs)} declarations", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        decls = list(pool.map(call, p1_jobs))

    # phase 2 -- give the model back its OWN declaration, then let it answer
    p2_jobs = []
    for (it, base, s), (dtext, _f) in zip(meta, decls):
        decl = (dtext or "").strip()
        prompt = base + decl + "\n" + DECL_CLOSE + "\n" + close_reasoning + "\n"
        p2_jobs.append((a.url, a.model, prompt, a.max_tokens, a.temperature,
                        a.top_p, s, STOP))
    print(f"phase 2: {len(p2_jobs)} answers", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        answers = list(pool.map(call, p2_jobs))

    declared_n, cov, consist, no_decl = [], [], [], 0
    bind_recall, bind_extra = [], []
    slot_freq: Counter = Counter()
    raw_fh = open(a.raw, "w")
    for (it, _base, _s), (dtext, _df), (atext, finish) in zip(meta, decls, answers):
        if dtext is None or atext is None:
            continue
        reasoning = dtext.strip()
        answer = atext.strip()
        ex = extract_spec(reasoning)
        n_slots = len(ex.spec.provenance)
        if not reasoning or n_slots == 0:
            no_decl += 1
        declared_n.append(n_slots)
        if ex.extracted or ex.unextracted:
            cov.append(ex.coverage)
        for s_ in ex.spec.provenance:
            slot_freq[s_] += 1

        rec = {"key": it["key"], "genre": it.get("genre"),
               "declared_slots": n_slots, "coverage": round(ex.coverage, 3),
               "n_lines": len(ex.extracted) + len(ex.unextracted),
               "finish_reason": finish,
               "reasoning": reasoning[:2000], "answer": answer[:2000],
               "unextracted": ex.unextracted[:8]}

        if n_slots:
            rep = verify_spec(answer, ex.spec)
            if rep.hard_results:
                consist.append(rep.score)
                rec["self_consistency"] = round(rep.score, 3)
                rec["failed_slots"] = [r.slot for r in rep.failures()]

        if it["row"] is not None:
            truth = spec_from_ifeval(it["row"]["instruction_id_list"],
                                     it["row"].get("kwargs")).spec
            want = set(truth.provenance); got = set(ex.spec.provenance)
            if want:
                bind_recall.append(len(want & got) / len(want))
                bind_extra.append(len(got - want))
                rec["bind_want"] = sorted(want); rec["bind_got"] = sorted(got)
        raw_fh.write(json.dumps(rec) + "\n")
    raw_fh.close()

    def mean(x):
        return round(statistics.mean(x), 4) if x else None

    out = {
        "model": a.model, "source": a.source, "n": len(declared_n),
        "no_declaration_rate": round(no_decl / max(1, len(declared_n)), 4),
        "mean_slots_declared": mean(declared_n),
        "mean_extraction_coverage": mean(cov),
        "mean_self_consistency": mean(consist),
        "self_consistency_perfect_rate":
            round(sum(1 for c in consist if c == 1.0) / len(consist), 4) if consist else None,
        "binding_recall": mean(bind_recall),
        "mean_extra_slots": mean(bind_extra),
        "slot_frequency": dict(slot_freq.most_common()),
    }
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2))

    print("\n=== spec emission ===")
    for k in ("n", "no_declaration_rate", "mean_slots_declared",
              "mean_extraction_coverage", "mean_self_consistency",
              "self_consistency_perfect_rate", "binding_recall", "mean_extra_slots"):
        if out.get(k) is not None:
            print(f"  {k:32s} {out[k]}")
    print(f"  slots declared: {out['slot_frequency']}")
    print(f"\nwrote {a.out} and {a.raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
