"""The SDK must send the caller's matrix, not a summary of it.

``compute(matrix)`` never transmits the matrix. It reduces it to a dimension
and a density of ones, sends those two numbers, and the engine generates fresh
random matrices at that density and reports on those. Two entirely different
inputs of equal density therefore receive the same answer, and nothing in the
response says the caller's data was never examined.

That behaviour is not changed here. ``analyze()`` is added alongside it and
posts the matrix itself, so the engine runs the fold over the caller's data and
reports what each operator family concluded.

These tests assert what was actually sent — the endpoint and the payload — not
just what came back. A test that only checked return values could not tell the
two paths apart, which is how the original defect survived unnoticed.
"""

import unittest
from unittest.mock import patch

from zeropointlogic import ZPLClient
from zeropointlogic.exceptions import ZPLValidationError

KEY = "zpl_u_" + "a1b2c3d4" * 6

CHECKERBOARD_5 = [
    [0, 1, 0, 1, 0],
    [1, 0, 1, 0, 1],
    [0, 1, 0, 1, 0],
    [1, 0, 1, 0, 1],
    [0, 1, 0, 1, 0],
]

ANALYZE_RESPONSE = {
    "n": 5,
    "families": [
        {"family": 0, "bit": 0, "tie_broken": False},
        {"family": 1, "bit": 0, "tie_broken": False},
        {"family": 2, "bit": 1, "tie_broken": False},
        {"family": 3, "bit": 0, "tie_broken": False},
    ],
    "ones": 1,
    "unanimous": False,
    "tokens_used": 1,
    "compute_ms": 0.55,
}


class TestAnalyzeSendsTheMatrix(unittest.TestCase):
    def setUp(self):
        self.client = ZPLClient(api_key=KEY)

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_posts_the_matrix_itself(self, mock_request):
        mock_request.return_value = ANALYZE_RESPONSE
        self.client.analyze(CHECKERBOARD_5)

        method, endpoint = mock_request.call_args[0][0], mock_request.call_args[0][1]
        payload = mock_request.call_args[0][2]

        assert method == "POST"
        assert endpoint == "/analyze", f"must call the analyze route, got {endpoint}"
        assert payload["matrix"] == CHECKERBOARD_5, (
            "the matrix must reach the engine unchanged — this is the entire point"
        )

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_does_not_reduce_the_matrix_to_a_density(self, mock_request):
        mock_request.return_value = ANALYZE_RESPONSE
        self.client.analyze(CHECKERBOARD_5)
        payload = mock_request.call_args[0][2]

        assert "bias" not in payload, "a density must not be sent — it is what discards the data"
        assert "d" not in payload, "a dimension must not stand in for the matrix"
        assert "samples" not in payload, "one matrix is one observation; there is nothing to sample"

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_returns_every_family_not_one_pooled_verdict(self, mock_request):
        mock_request.return_value = ANALYZE_RESPONSE
        result = self.client.analyze(CHECKERBOARD_5)

        assert len(result.families) == 4, "all four families must be reported"
        assert result.ones == 1
        assert result.unanimous is False, "a three-to-one split must not read as agreement"
        assert result.n == 5
        for f in result.families:
            assert f.bit in (0, 1)
            assert isinstance(f.tie_broken, bool), "tie-breaking must be visible to the caller"

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_carries_no_ain_and_no_p_output(self, mock_request):
        # One matrix is one observation, so a proportion over it is 0 or 1 and
        # says nothing about balance. A score here would be invented.
        mock_request.return_value = ANALYZE_RESPONSE
        result = self.client.analyze(CHECKERBOARD_5)

        assert not hasattr(result, "ain"), "a single matrix has no AIN"
        assert not hasattr(result, "p_output"), "a single matrix has no output proportion"

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_rejects_bad_input_before_spending_a_request(self, mock_request):
        with self.assertRaises(ZPLValidationError) as ctx:
            self.client.analyze([[0, 1], [1, 0]])
        assert "3x3" in str(ctx.exception), (
            f"the message must name the minimum; got: {ctx.exception}"
        )
        mock_request.assert_not_called()

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_compute_is_untouched_and_still_sends_a_density(self, mock_request):
        # Pinned deliberately. compute() summarising the matrix is the shipped
        # behaviour; this adds a second method rather than changing results
        # people already depend on.
        mock_request.return_value = {
            "p_output": 0.5, "ain": 0.93, "ain_status": "HIGHLY_NEUTRAL",
            "deviation": 0.03, "status": "STABLE", "samples": 1000,
            "d": 5, "bias": 0.48, "tokens_used": 1, "compute_ms": 1.2,
        }
        self.client.compute(CHECKERBOARD_5, samples=1000)

        endpoint = mock_request.call_args[0][1]
        payload = mock_request.call_args[0][2]
        assert endpoint == "/compute", "compute must keep using its own route"
        assert "bias" in payload, "compute still sends a density, as it always has"
        assert "matrix" not in payload, "compute has never transmitted the matrix"


if __name__ == "__main__":
    unittest.main()
