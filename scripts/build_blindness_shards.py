"""Shard every E4.1 generation for an independent human/LLM audit of the checkers.

The programmatic override-checkers (case, bullets, postscript, length) may have
blind spots, exactly as the extractor did. This emits every generation with the
explicit requirement, the full answer, the checker's verdict, and the measured
values, sharded N ways for parallel judging.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.runstore import read_run  # noqa: E402
from verbalized_defaults.verifiers.case import check_case  # noqa: E402
from verbalized_defaults.verifiers.structure import count_bullets  # noqa: E402

REQUIREMENT = {
    "poem_lowercase": "The ENTIRE response must be lowercase — no capital letters "
                      "anywhere, including the first letter of poem lines.",
    "proper_noun_lowercase": "The ENTIRE response must be lowercase — including "
                             "place names and proper nouns.",
    "ps_recase": "The response must be entirely lowercase AND must contain a "
                 "postscript, whose marker is also lowercase (e.g. 'p.s.').",
    "global_bullets": "The response must contain EXACTLY 3 bullet points in total "
                      "across the whole poem (not 3 per stanza).",
    "length_2x": "The response must be at least {target} words long.",
}


def measure(prior: str, check: dict, ans: str) -> dict:
    up = sum(1 for c in ans if c.isupper())
    first_up = next((f"...{ans[max(0,i-15):i+10]!r}..." for i, c in enumerate(ans)
                     if c.isupper()), None)
    m = {"word_count": count_words(ans), "uppercase_chars": up,
         "first_uppercase": first_up, "bullet_count": count_bullets(ans),
         "has_ps_substring": "p.s" in ans.lower()}
    # the checker's verdict (mirrors analyze_prior_battery.satisfied)
    ok = True
    if check.get("case") == "lower" and not check_case(ans, "lower").ok:
        ok = False
    if "must_include_ci" in check and check["must_include_ci"] not in ans.lower():
        ok = False
    if "structure_bullets" in check and count_bullets(ans) != check["structure_bullets"]:
        ok = False
    if "length_words_min" in check and count_words(ans) < check["length_words_min"]:
        ok = False
    m["checker_verdict"] = "PASS" if ok else "FAIL"
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=16)
    ap.add_argument("--out", default=str(ROOT / "blindness"))
    ap.add_argument("--max-answer-chars", type=int, default=3000)
    a = ap.parse_args()
    outdir = pathlib.Path(a.out)
    outdir.mkdir(exist_ok=True)

    items = []
    for rid in ("e41-qwen", "e41-e2b", "e41-e4b"):
        meta, recs = read_run(rid)
        model = meta["model"].split("/")[-1]
        for r in recs:
            ans = r.get("answer") or ""
            check = r["check"]
            req = REQUIREMENT[r["prior"]]
            if "{target}" in req:
                req = req.format(target=check.get("length_words_min"))
            items.append({
                "id": f"{model}|{r['item_key']}|{r['condition']}|s{r['sample']}",
                "prior": r["prior"],
                "requirement": req,
                "instruction_given_to_model": r["user_prompt"],
                "answer": ans[:a.max_answer_chars],
                "answer_truncated_for_display": len(ans) > a.max_answer_chars,
                "measured": measure(r["prior"], check, ans),
            })

    # round-robin shard so every shard sees every prior/model/condition
    shards = [[] for _ in range(a.shards)]
    for i, it in enumerate(items):
        shards[i % a.shards].append(it)
    for i, sh in enumerate(shards):
        (outdir / f"shard_{i:02d}.json").write_text(json.dumps(sh, indent=1))
    print(f"{len(items)} generations -> {a.shards} shards in {outdir}")
    print(f"per shard: ~{len(items) // a.shards}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
