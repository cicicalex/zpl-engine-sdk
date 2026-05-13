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
            "ain_status": "STABLE",
            "tokens_used": 3,
            "compute_ms": 12.0,
        },
        matrix_size=4,
        samples=500,
    )
    assert r.ain == 0.81
    assert r.status == "STABLE"
    assert r.ain_status == "STABLE"
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
