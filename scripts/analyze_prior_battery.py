"""E4.1 analysis: override rate per prior per condition, with paired CIs.

The thesis prediction: on collision prompts, surfacing the default (declaring the
constraint) helps the model override its prior, so oracle_declare and
self_declare beat vanilla. If they do not, declaring a default does not help win
the silent fight — the sharpest possible negative for the whole project.

    uv run python scripts/analyze_prior_battery.py <run_id>
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.runstore import read_run, verify_run  # noqa: E402
from verbalized_defaults.verifiers.case import check_case  # noqa: E402
from verbalized_defaults.verifiers.keywords import has_postscript  # noqa: E402
from verbalized_defaults.verifiers.structure import count_bullets  # noqa: E402


def satisfied(check: dict, answer: str) -> bool:
    """Did the answer OVERRIDE the prior, i.e. satisfy the explicit constraint?"""
    if check.get("case") == "lower" and not check_case(answer, "lower").ok:
        return False
    if "must_include_ci" in check and not has_postscript(answer):
        return False
    if "structure_bullets" in check and count_bullets(answer) != check["structure_bullets"]:
        return False
    if "length_words_min" in check and count_words(answer) < check["length_words_min"]:
        return False
    return True


def paired_boot(a: dict, b: dict, iters=10000, seed=0):
    keys = sorted(set(a) & set(b))
    diffs = [a[k] - b[k] for k in keys]
    if not diffs:
        return None
    rng = random.Random(seed)
    n = len(diffs)
    ms = sorted(statistics.mean(diffs[rng.randrange(n)] for _ in range(n))
                for _ in range(iters))
    return statistics.mean(diffs), ms[int(0.025 * iters)], ms[int(0.975 * iters)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    a = ap.parse_args()

    meta, records = read_run(a.run_id)
    v = verify_run(a.run_id)
    # per (condition, prior): item_key -> mean override rate over samples
    cell = collections.defaultdict(lambda: collections.defaultdict(list))
    priors, conds = set(), set()
    for r in records:
        ok = satisfied(r["check"], r.get("answer") or "")
        cell[(r["condition"], r["prior"])][r["item_key"]].append(ok)
        priors.add(r["prior"])
        conds.add(r["condition"])

    def rate(cond, prior):
        d = {k: statistics.mean(v) for k, v in cell[(cond, prior)].items()}
        return d

    order = ["vanilla", "oracle_declare", "self_declare"]
    conds = [c for c in order if c in conds]
    priors = sorted(priors)

    print(f"{a.run_id}   model={meta.get('model')}   integrity ok={v['ok']}")
    print(f"\n{'prior':22s}" + "".join(f"{c:>16s}" for c in conds))
    print("-" * (22 + 16 * len(conds)))
    for prior in priors:
        rates = {c: rate(c, prior) for c in conds}
        base = statistics.mean(rates["vanilla"].values()) if rates["vanilla"] else float("nan")
        cells = []
        for c in conds:
            r = statistics.mean(rates[c].values()) if rates[c] else float("nan")
            cells.append(f"{r:.2f}")
        print(f"{prior:22s}" + "".join(f"{x:>16s}" for x in cells))

    print(f"\n--- override lift vs vanilla (paired bootstrap) ---")
    for cond in conds:
        if cond == "vanilla":
            continue
        print(f"\n  {cond}:")
        for prior in priors:
            res = paired_boot(rate(cond, prior), rate("vanilla", prior))
            if not res:
                continue
            pt, lo, hi = res
            sig = "yes" if (lo > 0 or hi < 0) else "no"
            print(f"    {prior:22s} {pt:+.3f}  [{lo:+.3f}, {hi:+.3f}]  {sig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
