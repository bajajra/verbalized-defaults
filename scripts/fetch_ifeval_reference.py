"""Download the official IFEval reference implementation + prompts.

Used by the parity harness (tests/test_ifeval_parity.py) and by the scoring
harness (verbalized_defaults.ifeval_score), which runs IFEval's *own* checkers so
our reported prompt-strict/loose numbers are the benchmark's numbers, not a
reimplementation.

The checker modules import each other as a package
(`from instruction_following_eval import instructions_util`), so they are laid
down as a real package directory with an __init__.py rather than loose files.

The downloaded files are third-party (Apache-2.0, google-research) and are NOT
vendored into this repository -- they land in reference/, which is gitignored.

    uv run python scripts/fetch_ifeval_reference.py
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

REFERENCE_DIR = pathlib.Path(__file__).resolve().parent.parent / "reference"
PKG_DIR = REFERENCE_DIR / "instruction_following_eval"

_BASE = ("https://raw.githubusercontent.com/google-research/google-research/"
         "master/instruction_following_eval/")

# package modules -> destination inside the package dir
PKG_SOURCES = {
    "instructions_util.py": _BASE + "instructions_util.py",
    "instructions.py": _BASE + "instructions.py",
    "instructions_registry.py": _BASE + "instructions_registry.py",
}

# standalone data files -> reference/
DATA_SOURCES = {
    "ifeval_input_data.jsonl": _BASE + "data/input_data.jsonl",
}


def _get(url: str, dest: pathlib.Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"ok   {dest.name}  ({len(data):,} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {dest.name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, url in PKG_SOURCES.items():
        failures += not _get(url, PKG_DIR / name)
    for name, url in DATA_SOURCES.items():
        failures += not _get(url, REFERENCE_DIR / name)

    init = PKG_DIR / "__init__.py"
    init.write_text("")
    print(f"ok   {init.relative_to(REFERENCE_DIR)} (created)")

    # Back-compat shim: the parity test historically looked for this path.
    legacy = REFERENCE_DIR / "instructions_util.py"
    if (PKG_DIR / "instructions_util.py").exists() and not legacy.exists():
        legacy.write_text((PKG_DIR / "instructions_util.py").read_text())
        print("ok   instructions_util.py (legacy copy)")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
