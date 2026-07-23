"""E0.2 binding analysis: does the model register what the prompt actually asked?

Binding is the first half of C2's factorization. The prompt states constraints;
the model declares its conventions; binding asks whether the declaration captured
them. A constraint that never reaches the declaration is the taxonomy's "never
registered" failure — and no amount of execution skill can recover it.

Scored against the adapter's ground truth (benchmark metadata, never a model):

    recall     = |declared ∩ required| / |required|   -- did it register them?
    precision  = |declared ∩ required| / |declared|   -- or did it invent slots?

Per-family recall is the actionable output: it says *which* constraint types go
missing, which is what a binding reward would have to fix.

Re-extracts from stored declarations so it reflects the current extractor.
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

from verbalized_defaults.ifeval_adapter import spec_from_ifeval  # noqa: E402
from verbalized_defaults.ifeval_score import load_ifeval_rows  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    rows = {r.get("key"): r for r in load_ifeval_rows()}

    for f in a.files:
        name = pathlib.Path(f).stem.replace("e02_", "")
        recalls, precisions, extras = [], [], []
        fam_hit: collections.Counter = collections.Counter()
        fam_tot: collections.Counter = collections.Counter()
        slot_miss: collections.Counter = collections.Counter()
        try:
            fh = open(f, encoding="utf-8")
        except FileNotFoundError:
            continue
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            row = rows.get(d.get("key"))
            if not row:
                continue
            truth = spec_from_ifeval(row["instruction_id_list"], row.get("kwargs")).spec
            want = {s for s in truth.provenance if s != "other"}
            if not want:
                continue
            got = set(extract_spec(d.get("reasoning") or "").spec.provenance)
            hit = want & got
            recalls.append(len(hit) / len(want))
            if got:
                precisions.append(len(hit) / len(got))
            extras.append(len(got - want))
            for s in want - got:
                slot_miss[s] += 1
            # per instruction family: was the slot it maps to registered?
            for iid in row["instruction_id_list"]:
                one = spec_from_ifeval([iid], [dict(zip(row["instruction_id_list"],
                                                        row.get("kwargs") or []))
                                               .get(iid, {})]).spec
                need = {s for s in one.provenance if s != "other"}
                if not need:
                    continue
                fam_tot[iid] += 1
                if need <= got:
                    fam_hit[iid] += 1

        if not recalls:
            print(f"\n### {name}: no scorable rows")
            continue
        print(f"\n### {name}   n={len(recalls)}")
        print(f"  binding recall    {statistics.mean(recalls):.3f}")
        print(f"  binding precision {statistics.mean(precisions):.3f}"
              if precisions else "  binding precision  n/a")
        print(f"  extra slots/resp  {statistics.mean(extras):.2f}"
              "   (declared but not required -- assumed defaults, not errors)")
        print(f"  {'most-missed slot':22s}{'missed':>8s}")
        for s, n in slot_miss.most_common(6):
            print(f"  {s:22s}{n:8d}")
        print(f"  {'constraint family':44s}{'recall':>8s}")
        for iid, tot in fam_tot.most_common(10):
            print(f"  {iid:44s}{fam_hit[iid] / tot:8.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
