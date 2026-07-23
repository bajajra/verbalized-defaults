"""The A/B/C triangle from E0.4: instruction said A, model declared B, output was C.

The contradiction test injected an oracle spec -- artificial. This uses the
model's OWN declaration: for every case and length constraint the prompt stated
(A), what the model verbalised in reasoning (B), and what it actually produced
(C). The joint (A,B,C) shows where the silent fight actually happens:

  A=B=C            registered right, executed right
  A=B, B!=C        registered right, EXECUTION failed
  A!=B             BINDING failed (declared something other than asked)

    uv run python scripts/analyze_e04_triangle.py e04-qwen e04-e2b e04-e4b
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.runstore import read_run  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402
from verbalized_defaults.verifiers.case import check_case  # noqa: E402

CASE_INSTR = {"change_case:english_lowercase": "lower",
              "change_case:english_capital": "upper"}


def out_case(ans: str) -> str:
    lo, up = check_case(ans, "lower").ok, check_case(ans, "upper").ok
    return "lower" if lo and not up else "upper" if up and not lo else "mixed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    a = ap.parse_args()

    for rid in a.run_ids:
        meta, records = read_run(rid)
        case_tri = collections.Counter()   # (A, B, C)
        len_tri = collections.Counter()    # (declared vs instr, output vs instr, output vs declared)
        for r in records:
            iids = r.get("instruction_id_list") or []
            decl = extract_spec(r.get("declaration") or "").spec
            ans = r.get("answer") or ""
            kw = dict(zip(iids, r.get("kwargs") or [{}] * len(iids)))

            for iid in iids:
                if iid in CASE_INSTR:
                    A = CASE_INSTR[iid]
                    B = decl.case or "not-declared"
                    C = out_case(ans)
                    case_tri[(A, B, C)] += 1
                if iid == "length_constraints:number_words":
                    req = extract_spec.__self__ if False else None  # noqa
                    from verbalized_defaults.ifeval_adapter import spec_from_ifeval
                    r_c = spec_from_ifeval([iid], [kw[iid]]).spec.length_words
                    d_c = decl.length_words
                    actual = count_words(ans)
                    B_ok = d_c is not None and r_c.satisfied_by(
                        round(d_c.value if d_c.value is not None else (d_c.lo + d_c.hi) / 2))
                    C_ok = r_c.satisfied_by(actual)
                    label = ("declared-satisfies-A: " + ("Y" if B_ok else "N" if d_c is not None else "no-decl"),
                             "output-satisfies-A: " + ("Y" if C_ok else "N"))
                    len_tri[label] += 1

        print(f"\n{'=' * 66}\n{rid}   model={meta.get('model')}")
        print("\n--- CASE triangle (instruction A / declared B / output C) ---")
        total = sum(case_tri.values())
        print(f"{'A (asked)':10s}{'B (declared)':16s}{'C (did)':10s}{'n':>5s}{'%':>7s}")
        for (A, B, C), n in sorted(case_tri.items(), key=lambda x: -x[1]):
            tag = ""
            if A == B == C:
                tag = "  aligned+obeyed"
            elif A == B and B != C:
                tag = "  EXEC fail (declared right, did wrong)"
            elif A != B:
                tag = "  BIND fail (declared != asked)"
            print(f"{A:10s}{B:16s}{C:10s}{n:5d}{100*n/total:7.1f}{tag}")

        if len_tri:
            print("\n--- LENGTH triangle (does declaration satisfy A? does output?) ---")
            lt = sum(len_tri.values())
            for k, n in sorted(len_tri.items(), key=lambda x: -x[1]):
                print(f"  {k[0]:24s} {k[1]:20s} {n:4d}  ({100*n/lt:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
