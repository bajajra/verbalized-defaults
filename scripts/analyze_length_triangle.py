"""The length triangle: instruction target -> declared target -> actual output.

Three numeric quantities exist for every length constraint, and the interesting
question is how they relate, not just whether the middle one "matches" the first.

    instruction   what the prompt demanded      (e.g. >= 300 words)
    declared      what the model said it'd do   (e.g. "about 450 words")
    actual        what it actually wrote        (e.g. 380 words)

Questions this answers:
  1. Does the declaration predict the output at all? (correlation)
  2. Does the model undershoot its OWN declared target? (declared -> actual)
  3. Does declaring ABOVE the requirement act as a buffer against undershoot,
     so an "over-declared" target is adaptive rather than an error?

    uv run python scripts/analyze_length_triangle.py e04-qwen e04-e2b e04-e4b
"""
from __future__ import annotations

import argparse
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402
from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.runstore import read_run  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402


def _target(c) -> float | None:
    if c is None:
        return None
    if c.value is not None:
        return float(c.value)
    if c.lo is not None and c.hi is not None:
        return (c.lo + c.hi) / 2.0
    return None


def collect(run_id: str):
    """-> list of (instr_constraint, declared_target, actual_words)."""
    _meta, records = read_run(run_id)
    rows = []
    for r in records:
        iids = r.get("instruction_id_list") or []
        kw = dict(zip(iids, r.get("kwargs") or [{}] * len(iids)))
        if "length_constraints:number_words" not in iids:
            continue
        req = spec_from_ifeval(["length_constraints:number_words"],
                               [kw["length_constraints:number_words"]]).spec.length_words
        decl = extract_spec(r.get("declaration") or "").spec.length_words
        rows.append((req, _target(decl), count_words(r.get("answer") or "")))
    return rows


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    a = ap.parse_args()

    for rid in a.run_ids:
        rows = collect(rid)
        declared = [(req, d, act) for (req, d, act) in rows if d is not None]
        n_all, n_decl = len(rows), len(declared)
        print(f"\n{'=' * 70}\n{rid}   length_words instances: {n_all}  "
              f"(declared a value: {n_decl})")
        if n_decl < 5:
            print("  too few declared to analyse")
            continue

        d_vals = [d for _, d, _ in declared]
        a_vals = [act for _, _, act in declared]

        # 1. does declaration predict output?
        print(f"  corr(declared, actual):        {pearson(d_vals, a_vals):+.3f}")

        # 2. output vs the model's OWN declared target
        rel = [(act - d) / d for _, d, act in declared if d]
        rel.sort()
        print(f"  actual vs declared:  median {rel[len(rel) // 2]:+.1%}   "
              f"under-own-target {sum(1 for x in rel if x < 0) / len(rel):.0%}")

        # 3. the buffer hypothesis, on 'at least' constraints
        atleast = [(req, d, act) for (req, d, act) in declared if req.op == "min"]
        if atleast:
            declared_above = [(req, d, act) for (req, d, act) in atleast if d > req.value]
            declared_at = [(req, d, act) for (req, d, act) in atleast if d <= req.value]

            def passrate(g):
                return (sum(1 for req, _, act in g if req.satisfied_by(act)) / len(g)
                        if g else float("nan"))

            print(f"  '>= N' constraints: {len(atleast)}")
            print(f"    declared a BUFFER (target > N):  {len(declared_above):3d}  "
                  f"pass {passrate(declared_above):.0%}")
            print(f"    declared AT/below N:             {len(declared_at):3d}  "
                  f"pass {passrate(declared_at):.0%}")
            if declared_above:
                buf = [(d - req.value) / req.value for req, d, _ in declared_above]
                buf.sort()
                print(f"    median buffer declared:          "
                      f"+{buf[len(buf) // 2]:.0%} above the requirement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
