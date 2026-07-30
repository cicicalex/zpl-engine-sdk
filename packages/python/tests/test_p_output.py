"""The SDK must surface the measurement, not only the summary derived from it.

``p_output`` is the engine's actual reading — the balance of the output stream,
0.500 being equilibrium. It arrives on every /compute response and the SDK
dropped it in the normaliser, under a note citing IP protection.

That reasoning does not survive contact with the wire: the engine's own HTTP
response serialises p_output and deviation to every caller holding a key, so
neither was ever secret. The only people they were hidden from were those
reading through a client. The owner's position, asked directly: the calculation
stays secret, the numbers it produces do not.

It matters mathematically too. ``ain`` is derived through an absolute value and
cannot say which side of equilibrium a reading sits on: 0.4687 and 0.5313 both
give AIN 0.9373. For a method whose purpose is finding a stable centre, which
way it leans is half the answer.
"""

import unittest

from zeropointlogic.engine_normalize import compute_result_from_engine_dict

ENGINE_RESPONSE = {
    "p_output": 0.4655,
    "ain": 0.931,
    "ain_status": "HIGHLY_NEUTRAL",
    "deviation": 0.0345,
    "status": "STABLE",
    "samples": 2000,
    "d": 9,
    "bias": 0.5,
    "tokens_used": 2,
    "compute_ms": 1.4,
}


class TestPOutputReachesTheCaller(unittest.TestCase):
    def test_p_output_survives_normalisation(self):
        r = compute_result_from_engine_dict(ENGINE_RESPONSE, matrix_size=9, samples=2000)
        assert r.p_output == 0.4655, "the engine's own measurement must reach the caller"

    def test_deviation_survives_normalisation(self):
        r = compute_result_from_engine_dict(ENGINE_RESPONSE, matrix_size=9, samples=2000)
        assert r.deviation == 0.0345

    def test_direction_of_imbalance_is_recoverable(self):
        low = compute_result_from_engine_dict(
            {**ENGINE_RESPONSE, "p_output": 0.4687, "ain": 0.9373}, matrix_size=9, samples=2000
        )
        high = compute_result_from_engine_dict(
            {**ENGINE_RESPONSE, "p_output": 0.5313, "ain": 0.9373}, matrix_size=9, samples=2000
        )
        assert low.ain == high.ain, "AIN cannot tell these apart — that is the problem"
        assert low.p_output != high.p_output, "p_output must tell them apart"
        assert low.p_output < 0.5 < high.p_output

    def test_absent_fields_stay_none_not_zero(self):
        # Reporting 0 would claim the output was entirely zeros — a real, and
        # very wrong, reading. Absent must stay absent.
        r = compute_result_from_engine_dict(
            {"ain": 0.9, "status": "STABLE", "tokens_used": 1}, matrix_size=9, samples=1000
        )
        assert r.p_output is None, "a missing measurement must not read as 0.0"
        assert r.deviation is None

    def test_existing_fields_untouched(self):
        r = compute_result_from_engine_dict(ENGINE_RESPONSE, matrix_size=9, samples=2000)
        assert r.ain == 0.931
        assert r.status == "STABLE"
        assert r.ain_status == "HIGHLY_NEUTRAL"
        assert r.tokens_used == 2


if __name__ == "__main__":
    unittest.main()
