"""Recompute E0.3 headline metrics from stored runs, using the CURRENT extractor.

Run outputs freeze whatever extractor existed at generation time. When the
extractor changes — as it did after finding it was format-biased toward one model
family — every stored summary becomes stale, and comparing a fresh number against
a frozen one silently mixes two instruments.

This re-derives everything from the stored declarations and answers, so all
models are scored by the same version. Generation is never repeated; only
measurement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import count_words  # noqa: E402
from verbalized_defaults.spec_extract import extract_spec  # noqa: E402
from verbalized_defaults.verifiers import verify_spec  # noqa: E402


def recompute(path: str) -> dict | None:
    slots, cov, cons, qual = [], [], [], 0
    no_decl = 0
    lerr: list[float] = []
    n = 0
    try:
        fh = open(path, encoding="utf-8")
    except FileNotFoundError:
        return None
    for line in fh:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        n += 1
        ex = extract_spec(d.get("reasoning") or "")
        ns = len(ex.spec.provenance)
        slots.append(ns)
        qual += len(ex.unextracted)
        if ex.extracted or ex.unextracted:
            cov.append(ex.coverage)
        if ns == 0:
            no_decl += 1
            continue
        answer = d.get("answer") or ""
        rep = verify_spec(answer, ex.spec)
        if rep.hard_results:
            cons.append(rep.score)
        lw = ex.spec.length_words
        if lw is not None:
            target = lw.value if lw.value is not None else (lw.lo + lw.hi) / 2
            if target:
                lerr.append((count_words(answer) - target) / target)
    if not n:
        return None
    lerr.sort()
    out = {
        "n": n,
        "no_decl": round(no_decl / n, 3),
        "slots": round(statistics.mean(slots), 2),
        "cov": round(statistics.mean(cov), 3) if cov else None,
        "selfcons": round(statistics.mean(cons), 3) if cons else None,
        "perfect": round(sum(1 for c in cons if c == 1.0) / len(cons), 3) if cons else None,
        "qual_per_resp": round(qual / n, 1),
    }
    if lerr:
        out["len_median"] = round(lerr[len(lerr) // 2], 3)
        out["len_under"] = round(sum(1 for x in lerr if x < 0) / len(lerr), 2)
        out["len_absmean"] = round(statistics.mean(abs(x) for x in lerr), 3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    d = pathlib.Path(a.data)

    runs = [
        ("Qwen3.5-2B  concrete", "e03_qwen_concrete.jsonl", "e03_qwen_concrete.json"),
        ("Gemma E2B   concrete", "e03_e2b_concrete.jsonl", "e03_e2b_concrete.json"),
        ("Gemma E4B   concrete", "e03_e4b_concrete.jsonl", "e03_e4b_concrete.json"),
        ("Qwen3.5-2B  soft", "e03_qwen_soft.jsonl", "e03_qwen_soft.json"),
        ("Gemma E2B   soft", "e03_e2b_soft.jsonl", "e03_e2b_soft.json"),
        ("Gemma E4B   soft", "e03_e4b_soft.jsonl", "e03_e4b_soft.json"),
    ]
    hdr = ("model / cue", "nodecl", "slots", "cov", "selfcons", "perfect",
           "lenmed", "under", "qual/r")
    print(f"{hdr[0]:22s}{hdr[1]:>8s}{hdr[2]:>7s}{hdr[3]:>7s}{hdr[4]:>10s}"
          f"{hdr[5]:>9s}{hdr[6]:>9s}{hdr[7]:>7s}{hdr[8]:>8s}")
    print("-" * 88)
    for label, raw, summary in runs:
        new = recompute(str(d / raw))
        if not new:
            continue
        try:
            old = json.loads((d / summary).read_text())
        except FileNotFoundError:
            old = {}
        def f(v, w=7, p=3):
            return f"{v:{w}.{p}f}" if isinstance(v, (int, float)) else " " * (w - 1) + "-"
        print(f"{label:22s}{f(new['no_decl'],8,2)}{f(new['slots'],7,2)}"
              f"{f(new['cov'])}{f(new['selfcons'],10)}{f(new['perfect'],9)}"
              f"{f(new.get('len_median'),9,2)}{f(new.get('len_under'),7,2)}"
              f"{f(new['qual_per_resp'],8,1)}")
        if old:
            print(f"{'  (before fix)':22s}{f(old.get('no_declaration_rate'),8,2)}"
                  f"{f(old.get('mean_slots_declared'),7,2)}"
                  f"{f(old.get('mean_extraction_coverage'))}"
                  f"{f(old.get('mean_self_consistency'),10)}"
                  f"{f(old.get('self_consistency_perfect_rate'),9)}"
                  f"{f((old.get('length_error') or {}).get('median_rel_error'),9,2)}"
                  f"{f((old.get('length_error') or {}).get('frac_under'),7,2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
