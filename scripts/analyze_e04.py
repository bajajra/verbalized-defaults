"""E0.4 — the C2 diagnostic: does registering a constraint predict satisfying it?

Binding (E0.2) and execution (E0.3) have so far been measured on *different*
prompt sets, so they could not be combined. This joins them on the **same
constraint instance**: for each individual IFEval constraint, was it registered
in the model's declaration, and did the answer then satisfy it?

    P(pass)            overall satisfaction
    P(pass | bind✓)    registered -> complied?     = execution quality
    P(pass | bind✗)    not registered -> complied? = the unrecoverable floor

The gap between the conditionals is what a binding reward could recover. Read
per family, not just in aggregate: the two stages fail on different families, so
an aggregate number averages away the diagnostic.

    uv run python scripts/analyze_e04.py <run_id> [<run_id> ...]
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
from verbalized_defaults.ifeval_score import score_prompt  # noqa: E402
from verbalized_defaults.runstore import read_run, verify_run  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402


def analyse(run_id: str):
    meta, records = read_run(run_id)
    # (bound, passed) counts, overall and per family
    tot = collections.Counter()
    per_fam: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    n_rows = 0

    for r in records:
        iids = r.get("instruction_id_list")
        if not iids:
            continue
        n_rows += 1
        declared_spec = extract_spec(r.get("declaration") or "").spec
        score = score_prompt(r["user_prompt"], iids, r.get("kwargs"),
                             r.get("answer") or "")
        kwargs_by_iid = dict(zip(iids, r.get("kwargs") or [{}] * len(iids)))

        for iid, passed in zip(iids, score.strict_each):
            req = spec_from_ifeval([iid], [kwargs_by_iid.get(iid, {})]).spec
            need = {s for s in req.provenance if s != "other"}
            if not need:
                continue  # untyped family (Bucket C) -- binding is undefined
            # Value-aware: a slot declared with the WRONG value is not bound.
            # Slot-presence alone counted 33.5% wrong-valued slots as bound and
            # inverted this entire diagnostic.
            ok, wrong, missing = binding_status(req, declared_spec)
            bound = bool(ok) and not wrong and not missing
            cell = ("bind_ok" if bound else "bind_miss") + ("_pass" if passed else "_fail")
            tot[cell] += 1
            per_fam[iid][cell] += 1
    return meta, n_rows, tot, per_fam


def rates(c: collections.Counter) -> tuple[float, float, float, int, int]:
    ok = c["bind_ok_pass"] + c["bind_ok_fail"]
    miss = c["bind_miss_pass"] + c["bind_miss_fail"]
    n = ok + miss
    p_all = (c["bind_ok_pass"] + c["bind_miss_pass"]) / n if n else float("nan")
    p_ok = c["bind_ok_pass"] / ok if ok else float("nan")
    p_miss = c["bind_miss_pass"] / miss if miss else float("nan")
    return p_all, p_ok, p_miss, ok, miss


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    ap.add_argument("--min-n", type=int, default=20)
    a = ap.parse_args()

    for rid in a.run_ids:
        v = verify_run(rid)
        meta, n_rows, tot, per_fam = analyse(rid)
        model = meta.get("model", "?")
        print(f"\n{'=' * 78}\n{rid}   model={model}   rows={n_rows}")
        print(f"integrity: {v['rows']} rows, {v['duplicate_keys']} dupes, "
              f"{v['hit_token_limit']} hit token limit, ok={v['ok']}")

        p_all, p_ok, p_miss, n_ok, n_miss = rates(tot)
        print(f"\n  constraint instances: {n_ok + n_miss}  "
              f"(bound {n_ok}, missed {n_miss}, binding recall {n_ok / (n_ok + n_miss):.3f})")
        print(f"  P(pass)          {p_all:.3f}")
        print(f"  P(pass | bind OK) {p_ok:.3f}   <- execution quality")
        print(f"  P(pass | bind MISS) {p_miss:.3f} <- unrecoverable floor")
        print(f"  lift from binding  {p_ok - p_miss:+.3f}")

        # The pooled conditional is confounded: binding rate correlates with
        # family difficulty, so families that are never bound may also be the
        # ones satisfied by default. Stratify -- compute the lift WITHIN each
        # family and aggregate that instead (Simpson's paradox otherwise).
        lifts, weights = [], []
        for iid, c in per_fam.items():
            _pa, po, pm, no, nm = rates(c)
            if no >= 5 and nm >= 5:
                lifts.append(po - pm)
                weights.append(no + nm)
        if lifts:
            wmean = sum(l * w for l, w in zip(lifts, weights)) / sum(weights)
            pos = sum(1 for l in lifts if l > 0)
            print(f"\n  --- stratified (within-family, both cells n>=5) ---")
            print(f"  families usable: {len(lifts)}   positive lift: {pos}/{len(lifts)}")
            print(f"  weighted mean within-family lift: {wmean:+.3f}")
            print(f"  median within-family lift:        "
                  f"{sorted(lifts)[len(lifts) // 2]:+.3f}")

        print(f"\n  {'family':46s}{'n':>5s}{'bind':>7s}{'P|ok':>7s}{'P|miss':>8s}")
        print("  " + "-" * 72)
        for iid, c in sorted(per_fam.items(),
                             key=lambda kv: -(sum(kv[1].values()))):
            pa, po, pm, no, nm = rates(c)
            n = no + nm
            if n < a.min_n:
                continue
            print(f"  {iid:46s}{n:5d}{no / n:7.2f}"
                  f"{po if po == po else float('nan'):7.2f}"
                  f"{pm if pm == pm else float('nan'):8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
