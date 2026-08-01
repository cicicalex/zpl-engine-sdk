"""Tests for ZPL Engine client."""

import unittest
from unittest.mock import Mock, patch, MagicMock

from zeropointlogic import ZPLClient, AsyncZPLClient, ZPL_SDK_CLIENT_TYPE
from zeropointlogic import __version__
from zeropointlogic.models import ComputeResult, UsageInfo, PlanInfo, HealthStatus
from zeropointlogic.exceptions import (
    ZPLError,
    ZPLAuthError,
    ZPLQuotaError,
    ZPLValidationError,
    ZPLNetworkError,
    ZPLRateLimitError,
)


class TestZPLClientInit(unittest.TestCase):
    """Test client initialization."""

    def test_init_valid_api_key(self):
        """Test initialization with valid API key."""
        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        assert client.api_key == "zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
        assert client.base_url == "https://engine.zeropointlogic.io"

    def test_init_empty_api_key(self):
        """Test initialization with empty API key."""
        with self.assertRaises(ValueError):
            ZPLClient(api_key="")

    def test_init_custom_base_url(self):
        """Test initialization with custom base URL on the allowlisted domain.

        Non-allowlisted URLs (e.g. http://localhost) are silently rejected and
        fall back to the production engine — see engine_normalize.py. The
        previous test asserted a non-allowlisted URL would be honoured, which
        regressed when URL hardening landed. Switching to a real subdomain
        keeps the "custom base URL" semantics intact without bypassing the
        production guard.
        """
        client = ZPLClient(
            api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
            base_url="https://engine-staging.zeropointlogic.io/",
        )
        assert client.base_url == "https://engine-staging.zeropointlogic.io"

    def test_init_timeout_and_retries(self):
        """Test initialization with custom timeout and retries."""
        client = ZPLClient(
            api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6", timeout=60, max_retries=5, backoff_factor=1.0
        )
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.backoff_factor == 1.0


class TestZPLClientHeaders(unittest.TestCase):
    """ADR 0002 optional telemetry headers."""

    def test_default_zpl_client_headers(self):
        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        h = client._get_headers()
        self.assertEqual(h["X-ZPL-Client"], ZPL_SDK_CLIENT_TYPE)
        self.assertEqual(h["X-ZPL-Client"], "sdk-python")
        self.assertEqual(h["X-ZPL-Client-Version"], __version__)

    def test_override_zpl_client_headers(self):
        client = ZPLClient(
            api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
            x_zpl_client="custom-bridge",
            x_zpl_client_version="9.8.7",
        )
        h = client._get_headers()
        self.assertEqual(h["X-ZPL-Client"], "custom-bridge")
        self.assertEqual(h["X-ZPL-Client-Version"], "9.8.7")


class TestZPLClientValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        self.client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")

    def test_validate_matrix_empty(self):
        """Test validation of empty matrix."""
        with self.assertRaises(ZPLValidationError):
            self.client._validate_matrix([])

    def test_validate_matrix_invalid_values(self):
        """Test validation of matrix with invalid values."""
        with self.assertRaises(ZPLValidationError):
            self.client._validate_matrix([[0, 2, 1]])

    def test_validate_matrix_inconsistent_rows(self):
        """Test validation of matrix with inconsistent row lengths."""
        with self.assertRaises(ZPLValidationError):
            self.client._validate_matrix([[0, 1], [1]])

    def test_validate_matrix_valid(self):
        """Test validation of valid matrix (>=3x3 to match engine constraint)."""
        # Should not raise
        self.client._validate_matrix([[0, 1, 0], [1, 0, 1], [0, 1, 1]])

    def test_validate_matrix_too_small(self):
        """Test that 2x2 matrices are rejected client-side (engine requires D>=3)."""
        with self.assertRaises(ZPLValidationError) as ctx:
            self.client._validate_matrix([[0, 1], [1, 0]])
        self.assertIn("at least 3x3", str(ctx.exception))


class TestZPLClientCompute(unittest.TestCase):
    """Test compute operations."""

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_compute_success(self, mock_request):
        """Test successful compute operation."""
        mock_request.return_value = {
            "ain": 0.75,
            "p_output": 0.52,
            "deviation": 0.08,
            "status": "STABLE",
            "ain_status": "MODERATE_BIAS",
            "samples": 100,
            "tokens_used": 1,
            "tokens_remaining": 999,
        }

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        result = client.compute([[0, 1, 0], [1, 0, 1], [0, 1, 1]], samples=100)

        assert isinstance(result, ComputeResult)
        assert result.ain == 0.75
        assert result.status == "STABLE"
        assert result.tokens_remaining == 999
        assert result.is_stable()
        # AUDIT 2026-08-01: this asserted bias_level == "low" for ain 0.75, and
        # the engine calls that same reading MODERATE_BIAS. The test was pinning
        # the disagreement rather than catching it. 0.60-0.80 is the engine's
        # MODERATE_BIAS band, so "moderate" is the only label that agrees with
        # the ain_status arriving in the same payload.
        assert result.bias_level == "moderate"
        assert result.has_bias()
        assert not result.is_neutral(), "0.75 is below the engine's NEUTRAL floor of 0.80"
        # An explicitly supplied threshold still compares against `ain`, so
        # callers who chose their own cut-off are unaffected.
        assert result.is_neutral(threshold=0.7)

    def test_compute_invalid_samples(self):
        """Test compute with invalid samples.

        AUDIT 2026-08-01: only `samples=0` was rejected. The engine does not
        refuse an out-of-range count, it clamps it to 100..50,000 and returns
        the clamped figure — so `samples=5` ran 100 and `samples=200_000` ran
        50,000, silently, while the caller believed otherwise. Anything the
        engine would rewrite is refused here instead.
        """
        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        for bad in (0, 5, 99, 50_001, 1_000_000):
            with self.assertRaises(ZPLValidationError, msg=f"samples={bad} must be refused"):
                client.compute([[0, 1, 0], [1, 0, 1], [0, 1, 1]], samples=bad)

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_compute_reports_the_sample_count_that_ran(self, mock_request):
        """The result carries the engine's sample count, not the request's.

        A synthesised payload can still disagree with the argument — an engine
        older than the field, or a caller building a result by hand — and when
        it does, the engine's figure is the one that describes the work done.
        """
        mock_request.return_value = {
            "ain": 0.93,
            "status": "STABLE",
            "ain_status": "HIGHLY_NEUTRAL",
            "samples": 1000,
            "tokens_used": 1,
        }

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        result = client.compute([[0, 1, 0], [1, 0, 1], [0, 1, 1]], samples=100)

        assert result.samples == 1000

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_batch_compute_success(self, mock_request):
        """Test successful batch compute."""
        mock_request.side_effect = [
            {
                "ain": 0.70,
                "p_output": 0.50,
                "deviation": 0.10,
                "status": "STABLE",
                "tokens_used": 1,
                "tokens_remaining": 999,
            },
            {
                "ain": 0.80,
                "p_output": 0.55,
                "deviation": 0.05,
                "status": "CERTIFIED_NEUTRAL",
                "tokens_used": 1,
                "tokens_remaining": 998,
            },
        ]

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        matrices = [
            [[0, 1, 0], [1, 0, 1], [0, 1, 1]],
            [[1, 1, 0], [0, 0, 1], [1, 0, 1]],
        ]
        results = client.batch_compute(matrices, samples=100)

        assert len(results) == 2
        assert results[0].ain == 0.70
        assert results[1].ain == 0.80


class TestZPLClientMethods(unittest.TestCase):
    """Test client methods."""

    def test_get_usage(self):
        """Test get_usage method.

        AUDIT 2026-05-14 (v2.0.3): get_usage no longer hits the engine —
        it hits ZPL Main's /api/user/me. The mock target changed from
        _make_request (engine wrapper) to self._requests.get (direct
        requests.get call to zeropointlogic.io).
        """
        from unittest.mock import MagicMock

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")

        # Mock the live response from zeropointlogic.io/api/user/me
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "user": {"id": "u1", "email": "test@test.com", "name": "Test", "role": "user", "plan": "pro", "plan_name": "Pro"},
            "tokens": {
                "remaining": 45000,
                "used_this_month": 5000,
                "monthly_quota": 50000,
                "bonus_balance": 0,
                "total_available_this_cycle": 50000,
                "percent_used": 10,
                "source": "engine_log",
                "engine_unreachable": False,
            },
            "limits": {"max_d": 25, "max_keys": 3},
        }
        client._requests = MagicMock()
        client._requests.get.return_value = fake_response

        usage = client.get_usage()

        assert isinstance(usage, UsageInfo)
        assert usage.plan == "pro"
        assert usage.tokens_remaining == 45000
        assert usage.tokens_used == 5000
        assert usage.tokens_limit == 50000
        assert usage.source == "engine_log"
        assert usage.usage_measured
        assert not usage.engine_unreachable
        # Verify it hit ZPL Main, not the engine
        called_url = client._requests.get.call_args[0][0]
        assert called_url.endswith("/api/user/me"), f"expected /api/user/me, got {called_url}"
        assert "zeropointlogic.io" in called_url
        assert "engine.zeropointlogic.io" not in called_url

    def test_get_usage_flags_an_unmeasured_zero(self):
        """A zero the server could not measure must not read as measured usage.

        AUDIT 2026-08-01: `tokens.source` was on the wire and this SDK dropped
        it. Three server-side failures all produce `used_this_month: 0`, which
        is also what an idle account produces, so without the source an
        unmeasured zero was indistinguishable from a real one. Measured on
        production: 200 tokens spent on the engine, 0 reported here. The
        engine enforces the quota regardless, so this zero is the only warning
        anyone gets before being refused.
        """
        from unittest.mock import MagicMock

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "user": {"plan": "free", "plan_name": "Free"},
            "tokens": {
                "remaining": 5000,
                "used_this_month": 0,
                "monthly_quota": 5000,
                "bonus_balance": 0,
                "percent_used": 0,
                "source": "engine_user_not_found",
                "engine_unreachable": False,
            },
            "limits": {"max_d": 9, "max_keys": 1},
        }
        client._requests = MagicMock()
        client._requests.get.return_value = fake_response

        usage = client.get_usage()

        assert usage.source == "engine_user_not_found"
        assert not usage.usage_measured
        assert "unknown" in str(usage), "an unmeasured figure must not print as a measurement"

    def test_get_usage_without_a_source_is_not_treated_as_measured(self):
        """An absent or unfamiliar source reads as not-measured.

        Whitelisting the one value that means "read from the engine" is the
        safe direction: a source added on the server later reads as unknown
        until someone decides otherwise, rather than being rendered as a
        measurement nobody signed off on. The CLI was tightened the same way.
        """
        from unittest.mock import MagicMock

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "user": {"plan": "free"},
            "tokens": {"remaining": 5000, "used_this_month": 0, "monthly_quota": 5000},
        }
        client._requests = MagicMock()
        client._requests.get.return_value = fake_response

        usage = client.get_usage()

        assert usage.source is None
        assert not usage.usage_measured

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_get_plans(self, mock_request):
        """Test get_plans method.

        AUDIT 2026-08-01: the mock used to carry `price_eur` and `features`,
        which the engine has never sent, and omitted `max_d` / `max_keys`,
        which it does. A mock written from the SDK's wishes rather than from
        the wire is how PlanInfo kept two fabricated fields; this is the body
        the engine's plans handler actually serialises.
        """
        mock_request.return_value = {
            "plans": [
                {
                    "name": "Free",
                    "max_d": 9,
                    "tokens_per_month": 5000,
                    "max_keys": 1,
                    "price_usd": 0,
                    "unlimited": False,
                },
                {
                    "name": "Basic",
                    "max_d": 16,
                    "tokens_per_month": 10000,
                    "max_keys": 1,
                    "price_usd": 10,
                    "unlimited": False,
                },
            ]
        }

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        plans = client.get_plans()

        assert len(plans) == 2
        assert plans[0].name == "Free"
        assert plans[0].is_free()
        assert plans[0].max_d == 9
        assert plans[0].max_keys == 1
        assert not plans[1].is_free()
        assert plans[1].price_usd == 10
        # The USD price is the only price; nothing prints a currency the
        # system does not charge in.
        assert "$" in str(plans[1])

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_get_health(self, mock_request):
        """Test get_health method.

        AUDIT 2026-08-01: the mock returned uptime_percent / response_time_ms /
        requests_per_second / error_rate_percent / last_check. The engine sends
        none of them — its health handler returns status, version and
        uptime_seconds — so the SDK was tested against a body no deployment has
        ever produced, and the README told users to format a metric that was
        always None.
        """
        mock_request.return_value = {
            "status": "ok",
            "version": "3.2.0",
            "uptime_seconds": 4212,
        }

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        health = client.get_health()

        assert isinstance(health, HealthStatus)
        assert health.status == "ok"
        assert health.version == "3.2.0"
        assert health.uptime_seconds == 4212
        assert health.is_healthy()

    @patch("zeropointlogic.client.ZPLClient._make_request")
    def test_get_health_without_uptime_stays_none(self, mock_request):
        """Absent uptime must not become 0 — 0 means "restarted this second"."""
        mock_request.return_value = {"status": "ok", "version": "3.2.0"}

        client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")
        health = client.get_health()

        assert health.uptime_seconds is None
        assert health.is_healthy()


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""

    def setUp(self):
        self.client = ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6")

    def test_handle_401_error(self):
        """Test handling of 401 Unauthorized."""
        with self.assertRaises(ZPLAuthError):
            self.client._handle_error_response(401, {"error": "Invalid API key"})

    def test_handle_402_error(self):
        """Test handling of 402 Payment Required."""
        with self.assertRaises(ZPLQuotaError) as ctx:
            self.client._handle_error_response(
                402, {"error": "Quota exceeded", "tokens_remaining": 0}
            )
        assert ctx.exception.tokens_remaining == 0

    def test_handle_400_error(self):
        """Test handling of 400 Bad Request."""
        with self.assertRaises(ZPLValidationError) as ctx:
            self.client._handle_error_response(
                400, {"error": "Invalid matrix", "field": "matrix"}
            )
        assert ctx.exception.field == "matrix"

    def test_handle_429_error(self):
        """Test handling of 429 Too Many Requests."""
        with self.assertRaises(ZPLRateLimitError) as ctx:
            self.client._handle_error_response(
                429, {"error": "Rate limited", "retry_after": "30"}
            )
        assert ctx.exception.retry_after == 30


class TestContextManager(unittest.TestCase):
    """Test context manager functionality."""

    def test_context_manager(self):
        """Test using client as context manager."""
        with ZPLClient(api_key="zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6") as client:
            assert client.api_key == "zpl_u_test_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"


if __name__ == "__main__":
    unittest.main()
