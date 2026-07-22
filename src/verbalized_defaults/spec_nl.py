"""Render a Spec as plain English.

Exists to separate two things E0.1 previously conflated:

* **surfacing** -- does restating the constraints before generating help at all?
* **notation**  -- can the model actually read our typed `<spec>` DSL?

An untrained model has never seen `length_words: >=300 [given]`. If the typed
block underperforms, that could mean surfacing does not help (interesting) or
merely that the notation is unreadable (uninteresting). Running the same
constraints in both renderings tells the two apart.

Deliberately plain and imperative -- no cleverness, no restating the task, just
the constraints the spec encodes.
"""
from __future__ import annotations

from .schema import LengthConstraint, Spec

_UNIT_NOUN = {"words": "words", "sentences": "sentences", "paragraphs": "paragraphs"}


def _count_phrase(c: LengthConstraint, noun: str) -> str:
    if c.op == "eq":
        return f"Write exactly {c.value} {noun}."
    if c.op == "min":
        return f"Write at least {c.value} {noun}."
    if c.op == "max":
        return f"Write no more than {c.value} {noun}."
    return f"Write between {c.lo} and {c.hi} {noun}."


def _markup_phrase(name: str, c: LengthConstraint) -> str:
    what = {
        "highlights": "sections wrapped in *asterisks*",
        "placeholders": "square-bracket placeholders like [this]",
        "caps_words": "words in ALL CAPITAL LETTERS",
    }[name]
    if c.op == "min":
        return f"Include at least {c.value} {what}."
    if c.op == "max":
        return f"Include no more than {c.value} {what}."
    if c.op == "eq":
        return f"Include exactly {c.value} {what}."
    return f"Include between {c.lo} and {c.hi} {what}."


def format_spec_natural(spec: Spec, bullet: str = "- ") -> str:
    """Render the constraints in a Spec as a plain-English requirement list."""
    lines: list[str] = []

    for slot, noun in (("length_words", "words"), ("length_sentences", "sentences"),
                       ("length_paragraphs", "paragraphs")):
        c = getattr(spec, slot)
        if c is not None:
            lines.append(_count_phrase(c, _UNIT_NOUN[noun]))

    if spec.case == "lower":
        lines.append("Write your entire response in lowercase letters only. "
                     "Do not use any capital letters anywhere.")
    elif spec.case == "upper":
        lines.append("Write your entire response in CAPITAL LETTERS only.")
    elif spec.case == "title":
        lines.append("Write your response in Title Case.")

    if spec.structure is not None:
        s = spec.structure
        if s.kind == "bullets":
            lines.append(f"Use exactly {s.count} bullet points in total across the "
                         "whole response.")
        elif s.kind == "sections":
            sep = f' separated by "{s.splitter}"' if s.splitter else ""
            lines.append(f"Organise the response into exactly {s.count} sections{sep}.")
        elif s.kind == "responses":
            sep = s.splitter or "******"
            lines.append(f"Give exactly {s.count} different responses, separated by "
                         f'"{sep}" and nothing else.')
        elif s.kind == "json":
            lines.append("Output valid JSON and nothing else.")
        elif s.kind == "table":
            lines.append("Present the response as a markdown table.")
        elif s.kind == "prose":
            lines.append("Write in plain prose with no bullet points and no headings.")

    if spec.delimiters:
        for d in spec.delimiters:
            lines.append(f'Use the exact separator "{d}".')

    if spec.must_include:
        for k in spec.must_include:
            if k.max_count is not None and k.min_count == 0:
                lines.append(f'Use the word "{k.text}" no more than {k.max_count} times.')
            elif k.min_count > 1:
                lines.append(f'Use the exact word "{k.text}" at least {k.min_count} times.')
            else:
                lines.append(f'Include the exact word "{k.text}".')

    if spec.forbidden:
        for w in spec.forbidden:
            if w == ",":
                lines.append("Do not use any commas anywhere in your response.")
            else:
                lines.append(f'Do not use the word "{w}" anywhere in your response.')

    if spec.markup is not None:
        for name, c in spec.markup.dimensions():
            lines.append(_markup_phrase(name, c))

    if spec.wrappers is not None:
        w = spec.wrappers
        if w.quotes:
            lines.append("Wrap your entire response in double quotation marks.")
        if w.title:
            lines.append("Include a title wrapped in double angle brackets, like "
                         "<<Title Here>>.")
        if w.start:
            lines.append(f'Begin your response with exactly: "{w.start}".')
        if w.end:
            lines.append(f'End your response with exactly: "{w.end}".')

    if spec.positional is not None:
        p = spec.positional
        lines.append(f'Paragraph {p.paragraph} must begin with the word "{p.first_word}".')

    if spec.response_options:
        opts = " or ".join(f'"{o}"' for o in spec.response_options)
        lines.append(f"Your answer must be exactly one of: {opts}.")

    if spec.language is not None:
        lines.append(f"Write the entire response in this language code: {spec.language}.")

    if spec.response_boundary is not None:
        lines.append("Begin your response by repeating the request exactly, with no "
                     "preamble before it.")

    if spec.other:
        lines.extend(f"Satisfy this requirement: {o}" for o in spec.other)

    return "\n".join(bullet + ln for ln in lines)
