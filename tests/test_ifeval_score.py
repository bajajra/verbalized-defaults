"""Validate the IFEval scoring harness against the benchmark's own checkers.

These tests guard the thing that would be most damaging to get wrong: if the
scorer does not discriminate, every downstream benchmark number is noise.
Skips cleanly when the reference package has not been downloaded.
"""
import pytest

from verbalized_defaults.ifeval_score import (
    ReferenceMissingError,
    aggregate,
    load_ifeval_rows,
    response_variants,
    score_prompt,
)


@pytest.fixture(scope="module")
def rows():
    try:
        return load_ifeval_rows()
    except ReferenceMissingError as exc:
        pytest.skip(str(exc))


def test_dataset_loads(rows):
    assert len(rows) == 541
    assert {"prompt", "instruction_id_list", "kwargs"} <= set(rows[0])


def test_scorer_discriminates_lowercase(rows):
    row = next(r for r in rows
               if r["instruction_id_list"] == ["change_case:english_lowercase"])
    good = score_prompt(row["prompt"], row["instruction_id_list"], row.get("kwargs"),
                        "this response is entirely lowercase and nothing else.")
    bad = score_prompt(row["prompt"], row["instruction_id_list"], row.get("kwargs"),
                       "This Response Has Capitals And Must Fail.")
    assert good.strict_all is True
    assert bad.strict_all is False


def test_empty_response_never_passes(rows):
    row = rows[0]
    s = score_prompt(row["prompt"], row["instruction_id_list"], row.get("kwargs"), "")
    assert s.strict_all is False


def test_loose_is_never_stricter_than_strict(rows):
    """Loose tries extra variants, so it can only ever be >= strict."""
    resp = "**Bold opener**\nthis is the actual answer, all lowercase here.\n"
    for row in rows[:60]:
        s = score_prompt(row["prompt"], row["instruction_id_list"], row.get("kwargs"), resp)
        for st, lo in zip(s.strict_each, s.loose_each):
            assert not (st and not lo), f"{row['instruction_id_list']}: strict passed but loose failed"


def test_loose_forgives_markdown_asterisks(rows):
    """The canonical reason loose exists: bold markup around a correct answer."""
    row = next(r for r in rows
               if r["instruction_id_list"] == ["change_case:english_lowercase"])
    s = score_prompt(row["prompt"], row["instruction_id_list"], row.get("kwargs"),
                     "*this is lowercase but wrapped in asterisks*")
    assert s.loose_all is True


def test_response_variants_shape():
    v = response_variants("a\nb\nc")
    assert len(v) == 8
    assert "a\nb\nc" in v


def test_aggregate_math():
    rows_ = [
        type("S", (), {"strict_all": True, "loose_all": True,
                       "strict_each": [True, True], "loose_each": [True, True],
                       "instruction_ids": ["x", "y"]})(),
        type("S", (), {"strict_all": False, "loose_all": True,
                       "strict_each": [True, False], "loose_each": [True, True],
                       "instruction_ids": ["x", "y"]})(),
    ]
    agg = aggregate(rows_)
    assert agg["n_prompts"] == 2
    assert agg["prompt_strict"] == 0.5
    assert agg["prompt_loose"] == 1.0
    assert agg["instruction_strict"] == 0.75
    assert agg["per_family"]["y"]["strict_acc"] == 0.5
