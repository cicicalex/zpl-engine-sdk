"""Tests for engine JSON normalization.

AUDIT 2026-05-13 (D3 + D4): p_output / deviation removed from public
ComputeResult to plug IP leak; tokens_remaining is now Optional. Test
updated to match the new public shape — wire response still carries
p_output / deviation, the normaliser just drops them.
"""

from zeropointlogic.engine_normalize import compute_result_from_engine_dict


def test_compute_result_from_engine_dict_snake_case():
    r = compute_result_from_engine_dict(
        {
            "ain": 0.81,
            "p_output": 0.52,   # ← still in wire response, dropped by normaliser
            "deviation": 0.01,  # ← same
            "status": "STABLE",
            "ain_status": "NEUTRAL",
            "tokens_used": 3,
            "compute_ms": 12.0,
        },
        matrix_size=4,
        samples=500,
    )
    assert r.ain == 0.81
    assert r.status == "STABLE"
    assert r.ain_status == "NEUTRAL"
    assert r.tokens_used == 3
    # tokens_remaining absent from input → None (was 0 pre-fix).
    assert r.tokens_remaining is None
    assert r.compute_ms == 12.0
    assert r.matrix_size == 4
    assert r.samples == 500
    # IP leak fields must NOT be on the public dataclass anymore.
    assert not hasattr(r, "p_output")
    assert not hasattr(r, "deviation")


def test_compute_result_from_engine_dict_with_tokens_remaining():
    r = compute_result_from_engine_dict(
        {
            "ain": 0.92,
            "status": "STABLE",
            "tokens_used": 1,
            "tokens_remaining": 4999,
        },
    )
    assert r.tokens_remaining == 4999


def test_status_and_ain_status_are_separate_enums():
    """The two status fields are different enums and never interchange.

    Pre-fix INHIBITED_HIGH / INHIBITED_LOW / ACTIVE were not accepted and
    were silently rewritten to "STABLE" — the opposite of what the engine
    reported.
    """
    for regime in ("STABLE", "ACTIVE", "INHIBITED_HIGH", "INHIBITED_LOW"):
        r = compute_result_from_engine_dict({"ain": 0.5, "status": regime, "tokens_used": 1})
        assert r.status == regime

    # Plain "INHIBITED" is not a valid value.
    bad = compute_result_from_engine_dict({"ain": 0.5, "status": "INHIBITED", "tokens_used": 1})
    assert bad.status == "STABLE"

    # A `status` value is not accepted as `ain_status` and vice versa.
    mixed = compute_result_from_engine_dict(
        {"ain": 0.5, "status": "CERTIFIED_NEUTRAL", "ain_status": "STABLE", "tokens_used": 1}
    )
    assert mixed.status == "STABLE"
    assert mixed.ain_status is None
