"""Which won — the system rule or the reasoning-spec?

For each condition, classify every output as all-lowercase / ALL-CAPS / mixed,
then read the contradiction cells directly.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.runstore import read_run, verify_run  # noqa: E402
from verbalized_defaults.verifiers.case import check_case  # noqa: E402


def classify(ans: str) -> str:
    lo = check_case(ans, "lower").ok
    up = check_case(ans, "upper").ok
    if lo and not up:
        return "lower"
    if up and not lo:
        return "upper"
    if lo and up:
        return "empty"
    return "mixed"


ORDER = ["sys_upper_only", "sys_lower_only", "spec_upper_only", "spec_lower_only",
         "sys_upper_spec_lower", "sys_lower_spec_upper"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    a = ap.parse_args()
    meta, records = read_run(a.run_id)
    v = verify_run(a.run_id)
    cells = collections.defaultdict(collections.Counter)
    for r in records:
        cells[r["condition"]][classify(r["answer"])] += 1

    print(f"{a.run_id}   model={meta.get('model')}   ok={v['ok']}\n")
    print(f"{'condition':22s}{'n':>4s}{'lower':>8s}{'UPPER':>8s}{'mixed':>8s}")
    print("-" * 50)
    for c in ORDER:
        d = cells[c]
        n = sum(d.values())
        if not n:
            continue
        print(f"{c:22s}{n:4d}{d['lower']/n:8.2f}{d['upper']/n:8.2f}"
              f"{(d['mixed']+d['empty'])/n:8.2f}")

    def frac(cond, key):
        d = cells[cond]
        n = sum(d.values())
        return d[key] / n if n else float("nan")

    print("\n--- CONTRADICTION cells: which authority won? ---")
    print(f"  system=UPPER, spec=lower : output lower (SPEC won) {frac('sys_upper_spec_lower','lower'):.2f}"
          f" | UPPER (SYSTEM won) {frac('sys_upper_spec_lower','upper'):.2f}")
    print(f"  system=lower, spec=UPPER : output UPPER (SPEC won) {frac('sys_lower_spec_upper','upper'):.2f}"
          f" | lower (SYSTEM won) {frac('sys_lower_spec_upper','lower'):.2f}")

    print("\n--- does each authority work ALONE? ---")
    print(f"  system rule alone: UPPER {frac('sys_upper_only','upper'):.2f} | "
          f"lower {frac('sys_lower_only','lower'):.2f}")
    print(f"  spec alone:        UPPER {frac('spec_upper_only','upper'):.2f} | "
          f"lower {frac('spec_lower_only','lower'):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
