"""Measure how much of IFEval our frozen 12-slot schema can express.

Runs the adapter over every IFEval row and reports the mapped / partial /
unmapped split, per instruction type and in aggregate, plus how many prompts are
*fully* expressible (every one of their constraints mapped cleanly).

This number matters: it bounds what an oracle-prefill probe (E0.1) can possibly
demonstrate, and it tells us which schema gaps would justify a new slot.

    uv run python scripts/measure_schema_coverage.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parent.parent / "reference" / "ifeval_input_data.jsonl"


def main() -> int:
    if not DATA.exists():
        print(f"missing {DATA}; run scripts/fetch_ifeval_reference.py", file=sys.stderr)
        return 1

    status: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    reasons: dict[str, str] = {}
    totals = collections.Counter()
    prompts_full = prompts_total = 0

    for line in DATA.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        res = spec_from_ifeval(row["instruction_id_list"], row.get("kwargs"))
        prompts_total += 1
        if not res.partial and not res.unmapped:
            prompts_full += 1
        for iid in res.mapped:
            status[iid]["mapped"] += 1
            totals["mapped"] += 1
        for iid, why in res.partial:
            status[iid]["partial"] += 1
            totals["partial"] += 1
            reasons.setdefault(iid, why)
        for iid, why in res.unmapped:
            status[iid]["unmapped"] += 1
            totals["unmapped"] += 1
            reasons.setdefault(iid, why)

    grand = sum(totals.values())
    print(f"IFEval rows: {prompts_total}   instruction instances: {grand}\n")
    header = f"{'instruction id':52s} {'mapped':>7s} {'partial':>8s} {'unmapped':>9s}"
    print(header)
    print("-" * len(header))
    for iid in sorted(status):
        c = status[iid]
        print(f"{iid:52s} {c['mapped']:7d} {c['partial']:8d} {c['unmapped']:9d}")

    print("\n--- aggregate (instruction instances) ---")
    for key in ("mapped", "partial", "unmapped"):
        print(f"{key:9s} {totals[key]:5d}  ({100.0 * totals[key] / grand:5.1f}%)")

    print(f"\nprompts fully expressible: {prompts_full}/{prompts_total} "
          f"({100.0 * prompts_full / prompts_total:.1f}%)")

    print("\n--- why not mapped ---")
    for iid in sorted(reasons):
        print(f"  {iid:52s} {reasons[iid]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
