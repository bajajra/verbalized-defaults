"""Paired analysis of an E0.1 run, with bootstrap CIs.

Written because single-sample runs proved irreproducible: identical configs at
temp 1.0 moved every condition by 0.02-0.07 between runs, larger than the effects
under test. Two things fix that, and both are done here:

1. **Average over samples per prompt.** Each (prompt, condition) gets a pass
   *rate* in [0,1] rather than a coin flip, which is far lower variance.
2. **Pair on the prompt.** Conditions see identical prompts, so the paired delta
   cancels per-prompt difficulty -- much tighter than comparing two marginals.

Reports a bootstrap CI over prompts. A lift whose CI spans 0 is not a finding.

    uv run python scripts/analyze_e01.py data/e01_raw.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics


def load(path: str):
    """-> {condition: {key: mean pass rate over samples}} for strict and loose."""
    acc: dict[str, dict] = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        acc[d["condition"]][d["key"]].append((bool(d["strict"]), bool(d["loose"])))
    strict, loose, nsamp = {}, {}, {}
    for cond, per_key in acc.items():
        strict[cond] = {k: statistics.mean(s for s, _ in v) for k, v in per_key.items()}
        loose[cond] = {k: statistics.mean(l for _, l in v) for k, v in per_key.items()}
        nsamp[cond] = statistics.mean(len(v) for v in per_key.values())
    return strict, loose, nsamp


def paired_bootstrap(a: dict, b: dict, iters: int = 10000, seed: int = 0):
    """Bootstrap the paired mean difference a-b over shared prompts."""
    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    diffs = [a[k] - b[k] for k in keys]
    point = statistics.mean(diffs)
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(iters):
        means.append(statistics.mean(diffs[rng.randrange(n)] for _ in range(n)))
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters)]
    return point, lo, hi, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--baseline", default="vanilla")
    a = ap.parse_args()

    strict, loose, nsamp = load(a.raw)
    base = a.baseline
    if base not in strict:
        print(f"baseline {base!r} not in file; have {sorted(strict)}")
        return 1

    print(f"samples per prompt: "
          f"{ {c: round(v, 1) for c, v in sorted(nsamp.items())} }\n")
    print(f"{'condition':20s}{'strict':>9s}{'loose':>9s}"
          f"{'Δstrict':>10s}{'95% CI':>20s}{'sig':>5s}")
    print("-" * 74)
    for cond in sorted(strict):
        s_mean = statistics.mean(strict[cond].values())
        l_mean = statistics.mean(loose[cond].values())
        if cond == base:
            print(f"{cond:20s}{s_mean:9.3f}{l_mean:9.3f}{'(baseline)':>10s}")
            continue
        res = paired_bootstrap(strict[cond], strict[base])
        if not res:
            continue
        point, lo, hi, n = res
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        print(f"{cond:20s}{s_mean:9.3f}{l_mean:9.3f}{point:+10.3f}"
              f"{f'[{lo:+.3f}, {hi:+.3f}]':>20s}{sig:>5s}")

    print("\nΔ is the paired mean difference vs baseline, bootstrapped over prompts.")
    print("A CI spanning 0 means the lift is not distinguishable from noise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
