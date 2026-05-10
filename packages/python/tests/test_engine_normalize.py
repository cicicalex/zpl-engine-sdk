"""Tests for engine JSON normalization."""

from zeropointlogic.engine_normalize import compute_result_from_engine_dict


def test_compute_result_from_engine_dict_snake_case():
    r = compute_result_from_engine_dict(
        {
            "ain": 0.81,
            "p_output": 0.52,
            "deviation": 0.01,
            "status": "STABLE",
            "ain_status": "STABLE",
            "tokens_used": 3,
            "compute_ms": 12.0,
        },
        matrix_size=4,
        samples=500,
    )
    assert r.ain == 0.81
    assert r.p_output == 0.52
    assert r.status == "STABLE"
    assert r.ain_status == "STABLE"
    assert r.tokens_used == 3
    assert r.tokens_remaining == 0
    assert r.compute_ms == 12.0
    assert r.matrix_size == 4
    assert r.samples == 500
