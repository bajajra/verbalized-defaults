"""Recompute E0.3 self-consistency and the length triangle from untruncated runs.

The original E0.3 stored answers capped at 2000 chars, which truncated 24-80% of
them and deflated every length-derived metric. These runstore runs hold full
text, so this recomputes cleanly and prints the truncation-artefact gap.

    uv run python scripts/recompute_e03_genre.py e03b-qwen-concrete ...
"""
from __future__ import annotations

import argparse
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.runstore import read_run, verify_run  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402
from verbalized_defaults.verifiers import verify_spec  # noqa: E402


def analyse(run_id: str) -> dict:
    meta, records = read_run(run_id)
    cons, lerr, hit_cap = [], [], 0
    slot_acc: dict[str, list[bool]] = {}
    n = 0
    for r in records:
        n += 1
        ans = r.get("answer") or ""
        if len(ans) >= 3999:  # runstore does not cap; this would be a real limit
            hit_cap += 1
        spec = extract_spec(r.get("declaration") or "").spec
        if not spec.provenance:
            continue
        rep = verify_spec(ans, spec)
        if rep.hard_results:
            cons.append(rep.score)
        for res in rep.hard_results:
            slot_acc.setdefault(res.slot, []).append(res.ok)
        lw = spec.length_words
        if lw is not None:
            tgt = lw.value if lw.value is not None else (lw.lo + lw.hi) / 2
            if tgt:
                lerr.append((count_words(ans) - tgt) / tgt)
    lerr.sort()
    return {
        "model": meta.get("model"), "n": n, "answers_at_cap": hit_cap,
        "self_cons": round(statistics.mean(cons), 3) if cons else None,
        "len_median": round(lerr[len(lerr) // 2], 3) if lerr else None,
        "len_under": round(sum(1 for x in lerr if x < 0) / len(lerr), 2) if lerr else None,
        "slot_acc": {s: round(sum(v) / len(v), 3) for s, v in sorted(slot_acc.items())},
    }


# truncated originals (0018/0019) for side-by-side
OLD = {
    "Qwen/Qwen3.5-2B": {"self_cons": 0.468, "len_median": -0.31, "len_under": 0.82,
                        "length_words": 0.075},
    "unsloth/gemma-4-E2B-it-NVFP4": {"self_cons": 0.376, "len_median": -0.30,
                                     "len_under": 0.79, "length_words": 0.125},
    "unsloth/gemma-4-E4B-it-NVFP4": {"self_cons": 0.436, "len_median": -0.29,
                                     "len_under": 0.90, "length_words": 0.124},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_ids", nargs="+")
    a = ap.parse_args()
    print(f"{'model':32s}{'self-cons':>18s}{'len median':>20s}{'len_words acc':>20s}")
    print(f"{'':32s}{'trunc -> full':>18s}{'trunc -> full':>20s}{'trunc -> full':>20s}")
    print("-" * 92)
    for rid in a.run_ids:
        v = verify_run(rid)
        r = analyse(rid)
        o = OLD.get(r["model"], {})
        m = r["model"].split("/")[-1]
        sc = f"{o.get('self_cons','?')} -> {r['self_cons']}"
        lm = f"{o.get('len_median','?'):+} -> {r['len_median']:+}" if r['len_median'] is not None else "-"
        la = f"{o.get('length_words','?')} -> {r['slot_acc'].get('length_words','-')}"
        print(f"{m:32s}{sc:>18s}{lm:>20s}{la:>20s}")
        print(f"    integrity ok={v['ok']}  answers hitting a real 4000-char length: {r['answers_at_cap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
