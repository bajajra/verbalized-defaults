"""Per-slot accuracy for E0.3: which self-declared conventions does a model keep?

The headline self-consistency number averages over very different slots. This
breaks it down: for each slot, how often it was declared, and how often the
response then satisfied it. That ordering is the diagnostic — it separates
dimensions the model can execute from dimensions it can only talk about.

Re-extracts from stored declarations, so it always reflects the current
extractor rather than whatever was frozen into the run's output file.

    uv run python scripts/analyze_e03_slots.py data/e03_qwen_concrete.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.spec_extract import extract_spec  # noqa: E402
from verbalized_defaults.verifiers import verify_spec  # noqa: E402


def analyse(path: str):
    declared: collections.Counter = collections.Counter()
    satisfied: collections.Counter = collections.Counter()
    scores: list[float] = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        ex = extract_spec(d.get("reasoning") or "")
        if not ex.spec.provenance:
            continue
        rep = verify_spec(d.get("answer") or "", ex.spec)
        hard = rep.hard_results
        if not hard:
            continue
        scores.append(rep.score)
        for r in hard:
            declared[r.slot] += 1
            if r.ok:
                satisfied[r.slot] += 1
    return declared, satisfied, scores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    for f in a.files:
        name = pathlib.Path(f).stem.replace("e03_", "")
        try:
            declared, satisfied, scores = analyse(f)
        except FileNotFoundError:
            continue
        if not scores:
            print(f"\n### {name}: no scorable declarations")
            continue
        print(f"\n### {name}   n={len(scores)}   "
              f"self-consistency {statistics.mean(scores):.3f}")
        print(f"  {'slot':20s}{'declared':>10s}{'kept':>7s}{'accuracy':>10s}")
        print("  " + "-" * 45)
        for slot, n in declared.most_common():
            acc = satisfied[slot] / n
            flag = "  <-- worst" if acc < 0.25 and n >= 10 else ""
            print(f"  {slot:20s}{n:10d}{satisfied[slot]:7d}{acc:10.1%}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
