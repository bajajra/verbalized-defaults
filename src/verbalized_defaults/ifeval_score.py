"""Score responses with IFEval's OWN checkers.

Deliberately delegates to the benchmark's `instructions_registry` rather than
reusing our verifier suite. Our verifiers exist to *train* against; the reported
benchmark numbers must be the benchmark's own, or a verifier bug would silently
become a headline result. (Our suite is separately pinned to IFEval's metrics by
tests/test_ifeval_parity.py -- that is a parity check, not a substitute.)

Implements both IFEval accuracies:

* **strict**  -- the response as written satisfies the instruction.
* **loose**   -- any of IFEval's response variants satisfies it (first/last line
  removed, markdown asterisks stripped, and combinations). This exists because
  models often wrap an otherwise-correct answer in a preamble or bold markup.

Requires the reference package: `uv run python scripts/fetch_ifeval_reference.py`.
"""
from __future__ import annotations

import functools
import pathlib
import sys
from dataclasses import dataclass, field

REFERENCE_DIR = pathlib.Path(__file__).resolve().parents[2] / "reference"


class ReferenceMissingError(RuntimeError):
    pass


@functools.lru_cache(maxsize=1)
def _registry():
    pkg = REFERENCE_DIR / "instruction_following_eval"
    if not (pkg / "instructions_registry.py").exists():
        raise ReferenceMissingError(
            f"IFEval reference not found at {pkg}. "
            "Run: uv run python scripts/fetch_ifeval_reference.py"
        )
    if str(REFERENCE_DIR) not in sys.path:
        sys.path.insert(0, str(REFERENCE_DIR))
    from instruction_following_eval import instructions_registry  # type: ignore

    return instructions_registry


def response_variants(response: str) -> list[str]:
    """IFEval's loose-match variants, reproduced exactly."""
    r = response.split("\n")
    remove_first = "\n".join(r[1:]).strip()
    remove_last = "\n".join(r[:-1]).strip()
    remove_both = "\n".join(r[1:-1]).strip()
    revised = response.replace("*", "")
    revised_remove_first = remove_first.replace("*", "")
    revised_remove_last = remove_last.replace("*", "")
    revised_remove_both = remove_both.replace("*", "")
    return [response, revised, remove_first, remove_last, remove_both,
            revised_remove_first, revised_remove_last, revised_remove_both]


@dataclass
class PromptScore:
    key: object
    strict_all: bool
    loose_all: bool
    strict_each: list[bool] = field(default_factory=list)
    loose_each: list[bool] = field(default_factory=list)
    instruction_ids: list[str] = field(default_factory=list)


def score_prompt(prompt: str, instruction_id_list: list[str],
                 kwargs_list, response: str, key=None) -> PromptScore:
    """Score one response against one IFEval row's instructions."""
    reg = _registry()
    kwargs_list = kwargs_list or [{} for _ in instruction_id_list]
    variants = [v for v in response_variants(response)]

    strict_each, loose_each = [], []
    for idx, iid in enumerate(instruction_id_list):
        cls = reg.INSTRUCTION_DICT[iid]
        instruction = cls(iid)
        kw = {k: v for k, v in (kwargs_list[idx] or {}).items() if v is not None}
        instruction.build_description(**kw)
        args = instruction.get_instruction_args()
        if args and "prompt" in args:
            instruction.build_description(prompt=prompt)

        strict = bool(response.strip()) and instruction.check_following(response)
        strict_each.append(strict)

        loose = False
        for v in variants:
            if v.strip() and instruction.check_following(v):
                loose = True
                break
        loose_each.append(loose)

    return PromptScore(
        key=key,
        strict_all=all(strict_each),
        loose_all=all(loose_each),
        strict_each=strict_each,
        loose_each=loose_each,
        instruction_ids=list(instruction_id_list),
    )


def aggregate(scores: list[PromptScore]) -> dict:
    """Prompt-level and instruction-level accuracy, plus a per-family table."""
    n = len(scores)
    if n == 0:
        return {}
    inst_strict = [s for sc in scores for s in sc.strict_each]
    inst_loose = [s for sc in scores for s in sc.loose_each]

    per_family: dict[str, dict] = {}
    for sc in scores:
        for iid, st, lo in zip(sc.instruction_ids, sc.strict_each, sc.loose_each):
            d = per_family.setdefault(iid, {"n": 0, "strict": 0, "loose": 0})
            d["n"] += 1
            d["strict"] += int(st)
            d["loose"] += int(lo)
    for d in per_family.values():
        d["strict_acc"] = round(d["strict"] / d["n"], 4)
        d["loose_acc"] = round(d["loose"] / d["n"], 4)

    return {
        "n_prompts": n,
        "prompt_strict": round(sum(s.strict_all for s in scores) / n, 4),
        "prompt_loose": round(sum(s.loose_all for s in scores) / n, 4),
        "instruction_strict": round(sum(inst_strict) / len(inst_strict), 4),
        "instruction_loose": round(sum(inst_loose) / len(inst_loose), 4),
        "per_family": per_family,
    }


def load_ifeval_rows(limit: int | None = None) -> list[dict]:
    import json

    path = REFERENCE_DIR / "ifeval_input_data.jsonl"
    if not path.exists():
        raise ReferenceMissingError(
            f"{path} missing. Run: uv run python scripts/fetch_ifeval_reference.py")
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows
