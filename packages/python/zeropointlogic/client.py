"""ZPL Engine SDK - Main client implementation."""

import time
import json
import logging
from typing import Optional
from datetime import datetime

from zeropointlogic.version import __version__
from zeropointlogic.models import ComputeResult, UsageInfo, PlanInfo, HealthStatus
from zeropointlogic.engine_normalize import compute_result_from_engine_dict
from zeropointlogic.http_errors import parse_engine_http_error
from zeropointlogic.exceptions import (
    ZPLError,
    ZPLAuthError,
    ZPLQuotaError,
    ZPLRateLimitError,
    ZPLValidationError,
    ZPLNetworkError,
)
from zeropointlogic.utils import validate_matrix

logger = logging.getLogger(__name__)

# ADR 0002 default for X-ZPL-Client from this package.
ZPL_SDK_CLIENT_TYPE = "sdk-python"


class BaseZPLClient:
    """Base client with common functionality."""

    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 0.5

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://engine.zeropointlogic.io",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        x_zpl_client: Optional[str] = None,
        x_zpl_client_version: Optional[str] = None,
    ):
        """
        Initialize ZPL Client.

        Args:
            api_key: API key (zpl_xxx format)
            base_url: Base URL for the API (default: production)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Multiplier for exponential backoff (default 0.5)
            x_zpl_client: ADR 0002 ``X-ZPL-Client`` (default: ``sdk-python``).
            x_zpl_client_version: ADR 0002 ``X-ZPL-Client-Version`` (default: package version).

        Raises:
            ValueError: If api_key is empty, a service key, or wrong format.
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")

        trimmed = api_key.strip()

        # v2.0.2 (audit 2026-05-13): reject service keys + enforce format.
        # Pre-2.0.2 the SDK only warned on a missing "zpl_" prefix, which
        # meant a developer could ship a service key (zpl_s_*) in a Jupyter
        # notebook or a CI script and not realise the secret was leaking
        # downstream. CLI and MCP already enforce this regex; SDK now
        # matches them.
        import re
        if re.match(r"^zpl_s_", trimmed, re.IGNORECASE):
            raise ValueError(
                "api_key is a service key (zpl_s_*). Service keys are "
                "server-only — never ship them in notebooks or shared "
                "scripts. Use a user key (zpl_u_*) from `zpl login` or "
                "zeropointlogic.io/dashboard/api-keys."
            )
        if not re.match(r"^zpl_u_(?:[a-z]+_)?[a-f0-9]{48}$", trimmed):
            raise ValueError(
                "api_key does not match the expected format "
                "(zpl_u_<48 hex> or zpl_u_<prefix>_<48 hex>). "
                "Check for trailing whitespace or stray characters."
            )

        self.api_key = trimmed
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._x_zpl_client = x_zpl_client if x_zpl_client is not None else ZPL_SDK_CLIENT_TYPE
        self._x_zpl_client_version = x_zpl_client_version if x_zpl_client_version is not None else __version__

        # v2.0.2 (audit 2026-05-13 Gap J): fire a one-shot heartbeat to
        # ZPL Main so /admin/usage counts Python SDK adoption. The receiver
        # already whitelists `sdk-python`. Fire-and-forget; never blocks
        # the happy path; never throws. Set ZPL_SKIP_HEARTBEAT=1 to
        # disable (e.g. CI runners without network).
        self._send_heartbeat_once()

    # Class-level dedup so 100 ZPLClient() in a loop = 1 heartbeat.
    _heartbeat_sent: bool = False

    def _send_heartbeat_once(self) -> None:
        import os
        if ZPLClient._heartbeat_sent:
            return
        if os.environ.get("ZPL_SKIP_HEARTBEAT") == "1":
            return
        ZPLClient._heartbeat_sent = True
        try:
            import threading
            url = os.environ.get(
                "ZPL_HEARTBEAT_URL",
                "https://zeropointlogic.io/api/auth/cli/heartbeat",
            )
            def _fire():
                try:
                    import requests
                    requests.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "User-Agent": (
                                f"Mozilla/5.0 (compatible; "
                                f"zeropointlogic-python-sdk/{__version__}; "
                                "+https://zeropointlogic.io)"
                            ),
                        },
                        json={
                            "client": self._x_zpl_client,
                            "version": self._x_zpl_client_version,
                        },
                        timeout=5,
                    )
                except Exception:
                    pass  # never throw on heartbeat
            threading.Thread(target=_fire, daemon=True).start()
        except Exception:
            pass

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ZPL-Client": self._x_zpl_client,
            "X-ZPL-Client-Version": self._x_zpl_client_version,
            "User-Agent": (
                f"Mozilla/5.0 (compatible; zeropointlogic-python-sdk/{__version__}; "
                "+https://zeropointlogic.io)"
            ),
        }

    def _handle_error_response(self, status_code: int, data: dict, body: str = ""):
        """Handle error responses from the API.

        Args:
            status_code: HTTP status code
            data: Parsed JSON response
            body: Raw response body

        Raises:
            ZPLAuthError: On 401
            ZPLQuotaError: On 402
            ZPLValidationError: On 400
            ZPLRateLimitError: On 429
            ZPLError: On other errors
        """
        error_msg = data.get("error", data.get("message", body or f"HTTP {status_code}"))

        if status_code == 401:
            raise ZPLAuthError(f"Authentication failed: {error_msg}", status_code=status_code)

        elif status_code == 402:
            # Reserved for a future "payment required" semantic. The engine
            # currently returns 403 for quota exhaustion — see the default
            # branch below for the "Token limit exceeded" detection.
            tokens_remaining = data.get("tokens_remaining", 0)
            raise ZPLQuotaError(
                f"Quota exceeded: {error_msg}",
                tokens_remaining=tokens_remaining,
                status_code=status_code,
            )

        elif status_code == 400:
            field = data.get("field")
            raise ZPLValidationError(f"Validation error: {error_msg}", field=field, status_code=status_code)

        elif status_code == 429:
            retry_after = int(data.get("retry_after", 60))
            raise ZPLRateLimitError(
                f"Rate limited: {error_msg}",
                retry_after=retry_after,
                status_code=status_code,
            )

        else:
            # Engine returns HTTP 403 with body "Token limit exceeded: X/Y
            # used this month" on monthly quota exhaustion. The 403 implies
            # "Forbidden" (auth) but the cause is billing, so promote it to
            # ZPLQuotaError with a friendly upgrade hint instead of raising
            # generic ZPLError. Mirrors the TypeScript SDK + MCP behaviour.
            # (audit complet 12.05 — SDK discoverability fix.)
            import re as _re
            if status_code == 403 and _re.search(r"token limit exceeded", error_msg, _re.IGNORECASE):
                m = _re.search(r"(\d+)\s*/\s*(\d+)", error_msg)
                used = int(m.group(1)) if m else None
                limit = int(m.group(2)) if m else None
                remaining = (limit - used) if (used is not None and limit is not None) else 0
                usage = f" ({used} / {limit} tokens used this month)" if used is not None else ""
                upgrade_msg = (
                    f"Monthly ZPL Engine quota exceeded{usage}.\n"
                    "\n"
                    "Upgrade at https://zeropointlogic.io/pricing\n"
                    "  • Basic   $10/mo   10,000 tokens\n"
                    "  • Pro     $29/mo   50,000 tokens\n"
                    "  • GamePro $69/mo  150,000 tokens\n"
                    "\n"
                    "Or buy a one-off pack: https://zeropointlogic.io/dashboard/billing"
                )
                raise ZPLQuotaError(
                    upgrade_msg,
                    tokens_remaining=remaining,
                    status_code=status_code,
                    response_data=data,
                )

            raise ZPLError(f"API error: {error_msg}", status_code=status_code, response_data=data)

    def _validate_matrix(self, matrix: list[list[int]]) -> None:
        """Validate matrix format.

        Args:
            matrix: Matrix to validate

        Raises:
            ZPLValidationError: If matrix is invalid
        """
        is_valid, error_msg = validate_matrix(matrix)
        if not is_valid:
            raise ZPLValidationError(error_msg)


class ZPLClient(BaseZPLClient):
    """Synchronous ZPL Engine client using requests library."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize synchronous client.

        Args:
            api_key: API key (zpl_xxx format)
            **kwargs: Additional arguments passed to BaseZPLClient
        """
        super().__init__(api_key, **kwargs)

        try:
            import requests

            self._requests = requests
        except ImportError:
            raise ImportError("requests library is required. Install with: pip install requests")

    def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (without base URL)
            data: Request body for POST requests

        Returns:
            Parsed JSON response

        Raises:
            ZPLNetworkError: On connection errors
            ZPLError: On API errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    response = self._requests.get(url, headers=headers, timeout=self.timeout)
                elif method == "POST":
                    response = self._requests.post(
                        url, headers=headers, json=data, timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle errors (non-JSON bodies: Cloudflare / HTML)
                if response.status_code >= 400:
                    ct = (response.headers.get("Content-Type") or "").lower()
                    if "application/json" not in ct:
                        raise ZPLError(
                            parse_engine_http_error(response),
                            status_code=response.status_code,
                        )

                # Try to parse JSON
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {}

                # Handle errors
                if response.status_code >= 400:
                    self._handle_error_response(response.status_code, response_data, response.text)

                return response_data

            except self._requests.exceptions.Timeout as e:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise ZPLNetworkError(f"Request timeout after {self.max_retries} attempts") from e
                time.sleep(self.backoff_factor * (2 ** attempt))

            except self._requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise ZPLNetworkError(f"Connection failed after {self.max_retries} attempts") from e
                time.sleep(self.backoff_factor * (2 ** attempt))

            except self._requests.exceptions.RequestException as e:
                raise ZPLNetworkError(f"Request failed: {str(e)}") from e

    def compute(
        self,
        matrix: list[list[int]],
        samples: int = 1000,
    ) -> ComputeResult:
        """Compute AIN (AI Neutrality Index) for a matrix.

        Args:
            matrix: Binary matrix (N×N with only 0/1 values)
            samples: Number of samples for analysis (default 1000)

        Returns:
            ComputeResult with AIN score and analysis

        Raises:
            ZPLValidationError: If matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        self._validate_matrix(matrix)

        if samples < 1:
            raise ZPLValidationError("samples must be >= 1")

        # v2.0 — convert (matrix, samples) to engine wire shape (d, bias, samples).
        # v1.x sent {matrix, samples} which Rust engine never accepted: every
        # call returned 400 "Failed to deserialize: missing field `bias`".
        # SDK had zero working users before v2.0. See TS client.ts for parity.
        # bias = density of 1s; matches binary-input distribution parameter.
        d = len(matrix)
        ones = sum(1 for row in matrix for cell in row if cell == 1)
        total = d * d
        bias = ones / total if total > 0 else 0.0

        payload = {"d": d, "bias": bias, "samples": samples}
        response = self._make_request("POST", "/compute", payload)

        return compute_result_from_engine_dict(
            response,
            matrix_size=d,
            samples=samples,
        )

    def batch_compute(
        self,
        matrices: list[list[list[int]]],
        samples: int = 1000,
    ) -> list[ComputeResult]:
        """Compute AIN for multiple matrices.

        Args:
            matrices: List of binary matrices
            samples: Number of samples per matrix (default 1000)

        Returns:
            List of ComputeResult objects

        Raises:
            ZPLValidationError: If any matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        results = []
        for matrix in matrices:
            result = self.compute(matrix, samples)
            results.append(result)
        return results

    def get_usage(self) -> UsageInfo:
        """Get current API usage information.

        Returns:
            UsageInfo with plan and token details

        Raises:
            ZPLAuthError: If API key is invalid
            ZPLNetworkError: On connection errors
        """
        response = self._make_request("GET", "/usage")

        return UsageInfo(
            plan=response.get("plan", "unknown"),
            tokens_used=response.get("tokens_used", 0),
            tokens_limit=response.get("tokens_limit", 0),
            tokens_remaining=response.get("tokens_remaining", 0),
            reset_date=response.get("reset_date", ""),
            requests_made=response.get("requests_made", 0),
            last_reset=response.get("last_reset", ""),
        )

    def get_plans(self) -> list[PlanInfo]:
        """Get available pricing plans.

        Returns:
            List of PlanInfo with pricing and features

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = self._make_request("GET", "/plans")

        plans = []
        for plan_data in response.get("plans", []):
            plan = PlanInfo(
                name=plan_data.get("name", ""),
                tokens_per_month=plan_data.get("tokens_per_month", 0),
                price_usd=plan_data.get("price_usd", 0.0),
                price_eur=plan_data.get("price_eur", 0.0),
                features=plan_data.get("features", []),
            )
            plans.append(plan)

        return plans

    def get_health(self) -> HealthStatus:
        """Check engine health status.

        Returns:
            HealthStatus with uptime and performance metrics

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = self._make_request("GET", "/health")

        # v2.0.1 — pass `None` (not 0.0) for metrics the engine doesn't
        # report so __str__ shows "uptime n/a" instead of the misleading
        # "0.00% uptime, 0ms".
        return HealthStatus(
            status=response.get("status", "unknown"),
            version=response.get("version", ""),
            uptime_percent=response.get("uptime_percent"),
            response_time_ms=response.get("response_time_ms"),
            requests_per_second=response.get("requests_per_second"),
            error_rate_percent=response.get("error_rate_percent"),
            last_check=response.get("last_check"),
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class AsyncZPLClient(BaseZPLClient):
    """Asynchronous ZPL Engine client using httpx library."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize async client.

        Args:
            api_key: API key (zpl_xxx format)
            **kwargs: Additional arguments passed to BaseZPLClient
        """
        super().__init__(api_key, **kwargs)

        try:
            import httpx

            self._httpx = httpx
            self._client: Optional[httpx.AsyncClient] = None
        except ImportError:
            raise ImportError("httpx library is required. Install with: pip install httpx")

    async def _ensure_client(self) -> "httpx.AsyncClient":
        """Ensure async client is initialized."""
        if self._client is None:
            self._client = self._httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (without base URL)
            data: Request body for POST requests

        Returns:
            Parsed JSON response

        Raises:
            ZPLNetworkError: On connection errors
            ZPLError: On API errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        client = await self._ensure_client()

        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle errors (non-JSON bodies: Cloudflare / HTML)
                if response.status_code >= 400:
                    ct = (response.headers.get("Content-Type") or "").lower()
                    if "application/json" not in ct:
                        raise ZPLError(
                            parse_engine_http_error(response),
                            status_code=response.status_code,
                        )

                # Try to parse JSON
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {}

                # Handle errors
                if response.status_code >= 400:
                    self._handle_error_response(response.status_code, response_data, response.text)

                return response_data

            except self._httpx.TimeoutException as e:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise ZPLNetworkError(f"Request timeout after {self.max_retries} attempts") from e
                await self._sleep(self.backoff_factor * (2 ** attempt))

            except self._httpx.ConnectError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise ZPLNetworkError(f"Connection failed after {self.max_retries} attempts") from e
                await self._sleep(self.backoff_factor * (2 ** attempt))

            except self._httpx.HTTPError as e:
                raise ZPLNetworkError(f"Request failed: {str(e)}") from e

    async def _sleep(self, seconds: float) -> None:
        """Async sleep wrapper."""
        import asyncio

        await asyncio.sleep(seconds)

    async def compute(
        self,
        matrix: list[list[int]],
        samples: int = 1000,
    ) -> ComputeResult:
        """Compute AIN (AI Neutrality Index) for a matrix (async).

        Args:
            matrix: Binary matrix (N×N with only 0/1 values)
            samples: Number of samples for analysis (default 1000)

        Returns:
            ComputeResult with AIN score and analysis

        Raises:
            ZPLValidationError: If matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        self._validate_matrix(matrix)

        if samples < 1:
            raise ZPLValidationError("samples must be >= 1")

        # v2.0 — see sync compute() above. Engine expects {d, bias, samples}.
        d = len(matrix)
        ones = sum(1 for row in matrix for cell in row if cell == 1)
        total = d * d
        bias = ones / total if total > 0 else 0.0

        payload = {"d": d, "bias": bias, "samples": samples}
        response = await self._make_request("POST", "/compute", payload)

        return compute_result_from_engine_dict(
            response,
            matrix_size=d,
            samples=samples,
        )

    async def batch_compute(
        self,
        matrices: list[list[list[int]]],
        samples: int = 1000,
    ) -> list[ComputeResult]:
        """Compute AIN for multiple matrices (async).

        Args:
            matrices: List of binary matrices
            samples: Number of samples per matrix (default 1000)

        Returns:
            List of ComputeResult objects

        Raises:
            ZPLValidationError: If any matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        import asyncio

        results = await asyncio.gather(*[self.compute(matrix, samples) for matrix in matrices])
        return results

    async def get_usage(self) -> UsageInfo:
        """Get current API usage information (async).

        Returns:
            UsageInfo with plan and token details

        Raises:
            ZPLAuthError: If API key is invalid
            ZPLNetworkError: On connection errors
        """
        response = await self._make_request("GET", "/usage")

        return UsageInfo(
            plan=response.get("plan", "unknown"),
            tokens_used=response.get("tokens_used", 0),
            tokens_limit=response.get("tokens_limit", 0),
            tokens_remaining=response.get("tokens_remaining", 0),
            reset_date=response.get("reset_date", ""),
            requests_made=response.get("requests_made", 0),
            last_reset=response.get("last_reset", ""),
        )

    async def get_plans(self) -> list[PlanInfo]:
        """Get available pricing plans (async).

        Returns:
            List of PlanInfo with pricing and features

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = await self._make_request("GET", "/plans")

        plans = []
        for plan_data in response.get("plans", []):
            plan = PlanInfo(
                name=plan_data.get("name", ""),
                tokens_per_month=plan_data.get("tokens_per_month", 0),
                price_usd=plan_data.get("price_usd", 0.0),
                price_eur=plan_data.get("price_eur", 0.0),
                features=plan_data.get("features", []),
            )
            plans.append(plan)

        return plans

    async def get_health(self) -> HealthStatus:
        """Check engine health status (async).

        Returns:
            HealthStatus with uptime and performance metrics

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = await self._make_request("GET", "/health")

        # See sync get_health above for the rationale on `None` defaults.
        return HealthStatus(
            status=response.get("status", "unknown"),
            version=response.get("version", ""),
            uptime_percent=response.get("uptime_percent"),
            response_time_ms=response.get("response_time_ms"),
            requests_per_second=response.get("requests_per_second"),
            error_rate_percent=response.get("error_rate_percent"),
            last_check=response.get("last_check"),
        )

    async def close(self) -> None:
        """Close the async client."""
        if self._client:
            await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
