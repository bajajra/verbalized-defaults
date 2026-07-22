"""Break an E0.1 run down by constraint load and by constraint family.

The headline number ("does surfacing help") averages over a very heterogeneous
set of prompts. Two decompositions are cheap and answer sharper questions:

1. **By constraint count.** If surfacing works by *binding* -- getting the
   constraint registered before generation -- the benefit should grow with how
   many constraints there are to track. A flat profile argues against binding
   being the mechanism.

2. **By constraint family.** The taxonomy predicts different failure modes are
   binding-limited vs execution-limited. Surfacing can only help the former: it
   puts the constraint in tokens, it does not make the model better at counting.
   Families that move are binding-limited; families that do not are execution-
   limited and need a different fix.

All comparisons are paired on the prompt and bootstrapped.

    uv run python scripts/analyze_e01_breakdown.py data/e01_qwen_final.jsonl \
        --condition nl_think_sys
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics


def load(path: str):
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    ids: dict = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        per[d["condition"]][d["key"]].append(bool(d["strict"]))
        ids[d["key"]] = d["instruction_ids"]
    rates = {c: {k: statistics.mean(v) for k, v in kv.items()} for c, kv in per.items()}
    return rates, ids


def boot(diffs: list[float], iters: int = 5000, seed: int = 0):
    if not diffs:
        return None
    point = statistics.mean(diffs)
    rng = random.Random(seed)
    n = len(diffs)
    ms = sorted(statistics.mean(diffs[rng.randrange(n)] for _ in range(n))
                for _ in range(iters))
    return point, ms[int(0.025 * iters)], ms[int(0.975 * iters)], n


def report(title: str, groups: dict[str, list[float]], min_n: int = 15):
    print(f"\n--- {title} ---")
    print(f"{'group':34s}{'n':>6s}{'Δstrict':>10s}{'95% CI':>20s}{'sig':>5s}")
    print("-" * 75)
    for name, diffs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(diffs) < min_n:
            continue
        r = boot(diffs)
        if not r:
            continue
        point, lo, hi, n = r
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        print(f"{name:34s}{n:6d}{point:+10.3f}{f'[{lo:+.3f}, {hi:+.3f}]':>20s}{sig:>5s}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--condition", default="nl_think_sys")
    ap.add_argument("--baseline", default="vanilla")
    a = ap.parse_args()

    rates, ids = load(a.raw)
    if a.condition not in rates or a.baseline not in rates:
        print(f"missing condition; have {sorted(rates)}")
        return 1
    cond, base = rates[a.condition], rates[a.baseline]
    keys = sorted(set(cond) & set(base))
    print(f"{a.condition} vs {a.baseline}   ({len(keys)} prompts)")

    # 1. by number of constraints in the prompt
    by_count: dict[str, list[float]] = collections.defaultdict(list)
    for k in keys:
        n = len(ids[k])
        label = f"{n} constraint" + ("s" if n != 1 else "")
        by_count[label].append(cond[k] - base[k])
    report("by constraint count (does binding load matter?)", by_count, min_n=10)

    # 2. by constraint family (a prompt contributes to each family it contains)
    by_family: dict[str, list[float]] = collections.defaultdict(list)
    for k in keys:
        for iid in set(ids[k]):
            by_family[iid].append(cond[k] - base[k])
    report("by constraint family (binding- vs execution-limited)", by_family)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
