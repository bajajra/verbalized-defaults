"""How often did the model's declared spec CONTRADICT the asked constraint?

Three outcomes per required slot (value-aware, from binding.py):
  correct     declared a value that satisfies the instruction
  CONTRADICT  declared a value that would NOT satisfy it (asked lower, said upper;
              asked >=300, said 150)  <- the "spec contradicts instruction" case
  missing     did not declare that slot at all (omission, not contradiction)

    uv run python scripts/analyze_e04_contradictions.py e04-qwen e04-e2b e04-e4b
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.binding import binding_status  # noqa: E402
from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402
from verbalized_defaults.runstore import read_run  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402


def _fmt(v) -> str:
    if v is None:
        return "-"
    for attr in ("op", "kind", "describe"):
        if hasattr(v, attr):
            try:
                return v.describe() if attr == "describe" else str(getattr(v, attr))
            except Exception:  # noqa: BLE001
                pass
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    ap.add_argument("--examples", type=int, default=4)
    a = ap.parse_args()

    for rid in a.run_ids:
        meta, records = read_run(rid)
        tot = collections.Counter()          # correct / contradict / missing
        by_slot = collections.defaultdict(collections.Counter)
        examples = []
        n_rec = n_with_contra = 0

        for r in records:
            iids = r.get("instruction_id_list") or []
            if not iids:
                continue
            n_rec += 1
            req = spec_from_ifeval(iids, r.get("kwargs")).spec
            decl = extract_spec(r.get("declaration") or "").spec
            ok, wrong, missing = binding_status(req, decl)
            for s in ok:
                tot["correct"] += 1
                by_slot[s]["correct"] += 1
            for s in missing:
                tot["missing"] += 1
                by_slot[s]["missing"] += 1
            for s in wrong:
                tot["contradict"] += 1
                by_slot[s]["contradict"] += 1
            if wrong:
                n_with_contra += 1
                if len(examples) < a.examples:
                    s = sorted(wrong)[0]
                    examples.append((s, _fmt(getattr(req, s)), _fmt(getattr(decl, s))))

        declared = tot["correct"] + tot["contradict"]
        total = declared + tot["missing"]
        print(f"\n{'=' * 60}\n{rid}   model={meta.get('model')}   records={n_rec}")
        print(f"  required constraint-slots: {total}")
        print(f"    declared & correct   : {tot['correct']:4d}  ({tot['correct']/total:.0%})")
        print(f"    declared & CONTRADICT: {tot['contradict']:4d}  ({tot['contradict']/total:.0%} of all; "
              f"{tot['contradict']/declared:.0%} of DECLARED)")
        print(f"    not declared         : {tot['missing']:4d}  ({tot['missing']/total:.0%})")
        print(f"  responses with >=1 contradicting declaration: "
              f"{n_with_contra}/{n_rec} ({n_with_contra/n_rec:.0%})")
        print(f"  contradictions by slot:")
        for s, c in sorted(by_slot.items(), key=lambda kv: -kv[1]["contradict"]):
            if c["contradict"]:
                d = c["correct"] + c["contradict"]
                print(f"    {s:20s} {c['contradict']:3d} contradicting "
                      f"({c['contradict']/d:.0%} of its declarations)")
        print("  example contradictions (slot: asked -> declared):")
        for s, asked, got in examples:
            print(f"    {s}: {asked!r} -> {got!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
