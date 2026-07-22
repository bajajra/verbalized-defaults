"""Default-measurement probe: the prior inventory.

Generates unconstrained responses across genres and measures, per dimension,
what the model fills in when the prompt specifies nothing. Two purposes:

1. **`defaults.json`** -- calibrated values for the `[assumed]` slots in SFT data.
2. **Schema adjudication** -- a dimension earns a typed slot iff the model shows a
   *stable prior* on it. This probe is what decides membership, replacing my
   (IFBench-contaminated) judgement. Candidate dimensions not currently in the
   schema are measured alongside the real ones precisely so they can be judged on
   evidence: nesting depth, emoji, indentation, preamble.

Methodology note -- **truncation censors length**. If a generation stops because
it hit `max_tokens`, its length reflects our cap, not the model's prior. Such
samples are recorded and excluded from length statistics rather than silently
biasing them downward.

Talks HTTP to a running vLLM server (see scripts/serve.sh); imports no vLLM.

    uv run python scripts/measure_defaults.py --samples 3 --max-tokens 1536
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from verbalized_defaults.metrics import (  # noqa: E402
    count_paragraphs,
    count_sentences,
    count_words,
    split_paragraphs,
)
from verbalized_defaults.verifiers.markup import (  # noqa: E402
    count_caps_words,
    count_highlights,
    count_placeholders,
)
from verbalized_defaults.verifiers.structure import count_bullets, count_headers  # noqa: E402
from verbalized_defaults.verifiers.wrappers import has_title  # noqa: E402

# --- candidate dimensions (not in schema v2; measured to adjudicate) ---------
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿]"
)
_NESTED_BULLET_RE = re.compile(r"^(?P<indent>[ \t]+)[-*+•]\s+\S", re.MULTILINE)
_INDENTED_LINE_RE = re.compile(r"^[ \t]+\S", re.MULTILINE)
_PREAMBLE_RE = re.compile(
    r"^\s*(sure|certainly|of course|absolutely|here(?:'s| is)|happy to|great question|i'd be happy)",
    re.IGNORECASE,
)


def max_bullet_nesting(text: str) -> int:
    """0 = no bullets, 1 = flat bullets, 2+ = nested."""
    if count_bullets(text) == 0:
        return 0
    depths = [1]
    for m in _NESTED_BULLET_RE.finditer(text):
        indent = m.group("indent").replace("\t", "    ")
        depths.append(1 + len(indent) // 2)
    return max(depths)


def measure(text: str) -> dict:
    paragraphs = split_paragraphs(text)
    upper = sum(1 for c in text if c.isupper())
    lower = sum(1 for c in text if c.islower())
    return {
        # --- schema v2 dimensions ---
        "words": count_words(text),
        "sentences": count_sentences(text),
        "paragraphs": count_paragraphs(text),
        "bullets": count_bullets(text),
        "headers": count_headers(text),
        "highlights": count_highlights(text),
        "placeholders": count_placeholders(text),
        "caps_words": count_caps_words(text),
        "has_title": int(has_title(text)),
        "uppercase_ratio": round(upper / max(1, upper + lower), 4),
        "quoted_whole": int(text.strip().startswith('"') and text.strip().endswith('"')),
        # --- candidate dimensions (NOT in the schema; being adjudicated) ---
        "emoji": len(_EMOJI_RE.findall(text)),
        "max_nesting": max_bullet_nesting(text),
        "indented_lines": len(_INDENTED_LINE_RE.findall(text)),
        "has_preamble": int(bool(_PREAMBLE_RE.match(text))),
        "mean_sentence_words": round(
            count_words(text) / max(1, count_sentences(text)), 2),
        "mean_paragraph_words": round(
            count_words(text) / max(1, len(paragraphs)), 2),
    }


def generate(args_tuple) -> dict | None:
    url, model, genre, prompt, idx, max_tokens, temp = args_tuple
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "max_tokens": max_tokens,
        "seed": idx,
    }).encode()
    req = urllib.request.Request(
        f"{url}/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            d = json.loads(resp.read())
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {genre}[{idx}] failed: {exc}", file=sys.stderr)
        return None
    choice = d["choices"][0]
    text = choice["message"].get("content") or ""
    if not text.strip():
        return None
    row = {"genre": genre, "prompt": prompt, "sample": idx,
           "truncated": choice.get("finish_reason") == "length"}
    row.update(measure(text))
    return row


def summarise(rows: list[dict], keys: list[str]) -> dict:
    """Median + IQR per dimension. IQR/median is the stability signal."""
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if k in r]
        if not vals:
            continue
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        q1 = vals_sorted[n // 4]
        q3 = vals_sorted[(3 * n) // 4]
        med = statistics.median(vals_sorted)
        out[k] = {"median": med, "q1": q1, "q3": q3, "n": n,
                  "dispersion": round((q3 - q1) / med, 3) if med else None}
    return out


LENGTH_KEYS = {"words", "sentences", "paragraphs", "mean_sentence_words", "mean_paragraph_words"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=1536)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--out", default=str(ROOT / "data" / "defaults.json"))
    ap.add_argument("--raw", default=str(ROOT / "data" / "defaults_raw.jsonl"))
    a = ap.parse_args()

    spec = json.loads((ROOT / "data" / "genre_prompts.json").read_text())["genres"]
    jobs = [(a.url, a.model, g, p, i, a.max_tokens, a.temperature)
            for g, prompts in spec.items() for p in prompts for i in range(a.samples)]
    print(f"{len(jobs)} generations ({len(spec)} genres x prompts x {a.samples} samples)")

    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        rows = [r for r in pool.map(generate, jobs) if r]
    print(f"got {len(rows)} responses")

    trunc = [r for r in rows if r["truncated"]]
    clean = [r for r in rows if not r["truncated"]]
    print(f"truncated (excluded from length stats): {len(trunc)}/{len(rows)}")

    with open(a.raw, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    dims = [k for k in rows[0] if k not in {"genre", "prompt", "sample", "truncated"}]
    per_genre = {}
    for g in spec:
        g_all = [r for r in rows if r["genre"] == g]
        g_clean = [r for r in clean if r["genre"] == g]
        if not g_all:
            continue
        stats = summarise(g_clean or g_all, [d for d in dims if d in LENGTH_KEYS])
        stats.update(summarise(g_all, [d for d in dims if d not in LENGTH_KEYS]))
        per_genre[g] = stats

    overall = summarise(clean, [d for d in dims if d in LENGTH_KEYS])
    overall.update(summarise(rows, [d for d in dims if d not in LENGTH_KEYS]))

    payload = {"model": a.model, "n_responses": len(rows), "n_truncated": len(trunc),
               "temperature": a.temperature, "max_tokens": a.max_tokens,
               "overall": overall, "per_genre": per_genre}
    pathlib.Path(a.out).write_text(json.dumps(payload, indent=2))

    print(f"\n{'dimension':22s} {'median':>9s} {'IQR':>13s} {'disp':>7s}")
    print("-" * 55)
    for k, s in overall.items():
        print(f"{k:22s} {s['median']:9.2f} {str(s['q1']) + '-' + str(s['q3']):>13s} "
              f"{s['dispersion'] if s['dispersion'] is not None else 'n/a':>7}")
    print(f"\nwrote {a.out} and {a.raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
