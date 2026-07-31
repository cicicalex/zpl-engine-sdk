"""The two most opposite matrices must not arrive as the same object.

AUDIT 2026-07-31: the engine was swept over 3..=100. At every even dimension
the four family bits for an all-zeros matrix are identical to those for an
all-ones matrix - 49 of 49 even dimensions, none of the 49 odd ones. Every paid
ceiling except Pro's 25 is even: 16, 32, 48, 64, 100.

The engine now returns input_ones / cells / degenerate so the caller can tell
them apart. These tests pin the mapping, and pin the trap in it: 0 is a real
count, not a missing value.
"""

from zeropointlogic.engine_normalize import analyze_result_from_engine_dict


def _payload(**over):
    base = {
        "n": 16,
        "families": [
            {"family": i, "bit": 0, "tie_broken": False} for i in range(4)
        ],
        "ones": 0,
        "unanimous": True,
        "tokens_used": 5,
    }
    base.update(over)
    return base


class TestDegenerateFields:
    def test_all_zeros_and_all_ones_do_not_collapse(self):
        """Same verdict, different answer - which is the whole point."""
        zeros = analyze_result_from_engine_dict(
            _payload(input_ones=0, cells=256, degenerate=True)
        )
        ones = analyze_result_from_engine_dict(
            _payload(input_ones=256, cells=256, degenerate=True)
        )
        # The families are byte-identical here on purpose - that is the case
        # being defended against.
        assert zeros.families == ones.families, "fixture must share a verdict"
        assert zeros != ones, (
            "an all-zeros and an all-ones matrix produced an identical result "
            "object - the caller cannot tell them apart"
        )
        assert zeros.input_ones == 0
        assert ones.input_ones == 256

    def test_zero_is_a_count_not_a_missing_value(self):
        r = analyze_result_from_engine_dict(
            _payload(input_ones=0, cells=256, degenerate=True)
        )
        assert r.input_ones == 0, "an all-zeros matrix must report 0, not None"
        assert r.input_ones is not None, "0 must not be confused with absent"
        assert r.degenerate is True

    def test_absent_fields_stay_none_on_an_older_engine(self):
        """An engine predating the sweep sends none of the three."""
        r = analyze_result_from_engine_dict(_payload())
        assert r.input_ones is None, "absent must not be coerced to 0"
        assert r.cells is None
        assert r.degenerate is None

    def test_a_structured_matrix_is_not_degenerate(self):
        r = analyze_result_from_engine_dict(
            _payload(input_ones=128, cells=256, degenerate=False)
        )
        assert r.degenerate is False
        assert 0 < r.input_ones < r.cells
