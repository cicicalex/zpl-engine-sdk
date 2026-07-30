"""Tests for engine JSON normalization.

AUDIT 2026-05-13 (D3 + D4): p_output / deviation removed from public
ComputeResult to plug what was believed to be an IP leak.

AUDIT 2026-07-30: reversed. The engine's own HTTP response serialises both to
every caller holding a key, so neither was ever secret — they were hidden only
from people reading through a client. The owner's position, asked directly: the
calculation stays secret, the numbers it produces do not. The assertions below
were pinning the old decision and are updated rather than deleted, so the
reversal is visible in the history instead of looking like drift.
"""

from zeropointlogic.engine_normalize import compute_result_from_engine_dict


def test_compute_result_from_engine_dict_snake_case():
    r = compute_result_from_engine_dict(
        {
            "ain": 0.81,
            "p_output": 0.52,
            "deviation": 0.01,
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
    # These reach the caller now. p_output is the engine's measurement —
    # output balance, 0.500 being equilibrium — and ain is derived from it
    # through an absolute value, so it cannot express which side of
    # equilibrium a reading sits on.
    assert r.p_output == 0.52
    assert r.deviation == 0.01


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
