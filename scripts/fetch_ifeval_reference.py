"""Download the official IFEval reference implementation + prompts.

Used only by the parity harness (tests/test_ifeval_parity.py), which diffs our
metric primitives against IFEval's own code on real prompt text. The downloaded
files are third-party (Apache-2.0, google-research) and are NOT vendored into
this repository -- they land in reference/, which is gitignored.

    uv run python scripts/fetch_ifeval_reference.py
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

REFERENCE_DIR = pathlib.Path(__file__).resolve().parent.parent / "reference"

SOURCES = {
    "instructions_util.py": (
        "https://raw.githubusercontent.com/google-research/google-research/"
        "master/instruction_following_eval/instructions_util.py"
    ),
    "ifeval_input_data.jsonl": (
        "https://raw.githubusercontent.com/google-research/google-research/"
        "master/instruction_following_eval/data/input_data.jsonl"
    ),
}


def main() -> int:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, url in SOURCES.items():
        dest = REFERENCE_DIR / name
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            dest.write_bytes(data)
            print(f"ok   {name}  ({len(data):,} bytes)")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
