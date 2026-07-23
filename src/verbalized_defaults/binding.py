"""Value-aware binding: did the declaration capture the constraint's *value*?

An earlier definition counted a constraint as bound whenever the matching slot
appeared in the declaration, regardless of what it said. Measured against real
runs, **33.5% of such "bound" slots carried the wrong value** — the prompt asked
for 300 words and the model declared 450, which is not binding, it is a miss with
extra steps. length_words was 78% wrong, must_include 93% wrong.

That flaw inverted the headline: it inflated binding recall, and it poisoned
`P(pass | bind✓)` with constraints bound to the *wrong* target, which then fail
execution. E0.4 came out with binding *negatively* associated with passing.

The definition used here: **would a response that exactly hits the declared value
satisfy the required constraint?** That is the question binding is supposed to
answer, and it is neither exact-equality (too strict — "about 320" does capture
">= 300") nor mere slot presence (too lenient).
"""
from __future__ import annotations

from .schema import LengthConstraint, Spec

_LENGTH_SLOTS = ("length_words", "length_sentences", "length_paragraphs")


def _length_target(c: LengthConstraint) -> float | None:
    if c.value is not None:
        return float(c.value)
    if c.lo is not None and c.hi is not None:
        return (c.lo + c.hi) / 2.0
    return None


def slot_agrees(slot: str, required: Spec, declared: Spec) -> bool:
    """Does `declared`'s value for `slot` capture what `required` demands?"""
    want = getattr(required, slot, None)
    got = getattr(declared, slot, None)
    if want is None:
        return True
    if got is None:
        return False

    if slot in _LENGTH_SLOTS:
        target = _length_target(got)
        # A declaration hitting its own stated target must satisfy the demand.
        return target is not None and want.satisfied_by(round(target))

    if slot == "must_include":
        need = {k.text.lower() for k in want}
        have = {k.text.lower() for k in got}
        return need <= have

    if slot == "forbidden":
        return {w.lower() for w in want} <= {w.lower() for w in got}

    if slot == "structure":
        if want.kind != got.kind:
            return False
        return want.count is None or want.count == got.count

    if slot == "wrappers":
        return all(getattr(got, f) == getattr(want, f)
                   for f in ("quotes", "title") if getattr(want, f))

    if slot == "markup":
        for name, c in want.dimensions():
            g = getattr(got, name, None)
            if g is None:
                return False
            t = _length_target(g)
            if t is None or not c.satisfied_by(round(t)):
                return False
        return True

    if slot in ("case", "language", "person"):
        return str(want).lower() == str(got).lower()

    if slot == "response_options":
        return bool(set(want) & set(got))

    # positional, delimiters, response_boundary: presence is the best available test
    return True


def binding_status(required: Spec, declared: Spec) -> tuple[set[str], set[str], set[str]]:
    """-> (bound_correctly, declared_but_wrong_value, not_declared)."""
    ok, wrong, missing = set(), set(), set()
    for slot in required.provenance:
        if slot == "other":
            continue
        if getattr(declared, slot, None) is None:
            missing.add(slot)
        elif slot_agrees(slot, required, declared):
            ok.add(slot)
        else:
            wrong.add(slot)
    return ok, wrong, missing
