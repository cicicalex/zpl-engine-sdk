"""ZPL Engine SDK - Main client implementation."""

# AUDIT 2026-08-01: required for the `X | Y` annotations below.
# pyproject declares requires-python = ">=3.9" and classifies 3.9, but PEP 604
# unions are only evaluable at runtime from 3.10. Every use in this package is in
# annotation position (checked with ast: 27 in annotations, 0 outside), so making
# annotations lazy keeps the declared floor honest instead of narrowing support.
from __future__ import annotations

import time
import json
import logging
from typing import Optional
from datetime import datetime

from zeropointlogic.version import __version__
from zeropointlogic.models import (
    ComputeResult, UsageInfo, PlanInfo, HealthStatus, AnalyzeResult, FamilyVerdict,
)
from zeropointlogic.engine_normalize import (
    compute_result_from_engine_dict, analyze_result_from_engine_dict,
)
from zeropointlogic.http_errors import parse_engine_http_error
from zeropointlogic.exceptions import (
    ZPLError,
    ZPLAuthError,
    ZPLQuotaError,
    ZPLRateLimitError,
    ZPLUpgradeRequiredError,
    ZPLValidationError,
    ZPLNetworkError,
)
from zeropointlogic.utils import validate_matrix

logger = logging.getLogger(__name__)

# ADR 0002 default for X-ZPL-Client from this package.
ZPL_SDK_CLIENT_TYPE = "sdk-python"


# AUDIT 2026-05-14 (HIGH): host allowlist for any URL the SDK sends the
# Bearer-authorised API key to. Pre-fix base_url / account_base_url /
# ZPL_HEARTBEAT_URL accepted any string. A committed .env, a poisoned CI
# variable, or a malicious wrapper package could silently exfiltrate the
# user's API key on the first SDK call. CLI + MCP enforce the same
# allowlist. Genuine self-hosted setups can opt out with
# ZPL_SDK_ALLOW_PRIVATE=1.
_ALLOWED_HOST_SUFFIXES = ("zeropointlogic.io",)


def _is_allowed_host(url_str: str) -> bool:
    import os
    from urllib.parse import urlparse
    if os.environ.get("ZPL_SDK_ALLOW_PRIVATE") == "1":
        return True
    try:
        u = urlparse(url_str)
    except Exception:
        return False
    if u.scheme not in ("http", "https"):
        return False
    host = (u.hostname or "").lower()
    # Strict suffix match: `host == base` OR `host endswith ".base"` so
    # `evil-zeropointlogic.io` is rejected.
    for base in _ALLOWED_HOST_SUFFIXES:
        if host == base or host.endswith("." + base):
            return True
    return False


def _sanitize_base_url(candidate: Optional[str], fallback: str) -> str:
    import sys
    fb = fallback.rstrip("/")
    if not candidate:
        return fb
    cleaned = candidate.rstrip("/")
    if _is_allowed_host(cleaned):
        return cleaned
    sys.stderr.write(
        f"[zpl-sdk] Rejecting non-allowlisted URL {candidate!r} — "
        f"falling back to {fb!r}. Set ZPL_SDK_ALLOW_PRIVATE=1 if self-hosted.\n"
    )
    return fb


# AUDIT 2026-08-01: the default deadline was 30 seconds - exactly the engine's
# own /compute ceiling, and half its /sweep ceiling. A client deadline equal to
# the server's is a coin flip over which side fires first, and losing it is not
# free: the engine deducts tokens before it starts computing and refunds only on
# a timeout it issues itself. A client that gives up first drops the request,
# the refund path is never reached, and the caller has paid for an answer nobody
# will ever see. Waiting past the engine turns the same overrun into the
# engine's own 504, which does refund.
#
# The CLI, the MCP and the TypeScript SDK were all raised to these numbers
# earlier the same day. The Python SDK was the client left out. The values are
# the engine's ceilings plus headroom for the network, not round numbers - if
# the engine's ceilings move, these have to move with them.
#
# One deadline covers every route because every request goes through one path
# here, so it takes the slowest ceiling.
_ENGINE_COMPUTE_CEILING_S = 30
_ENGINE_SWEEP_CEILING_S = 60
_NETWORK_HEADROOM_S = 5


# The engine's own bounds: `req.samples.unwrap_or(1000).clamp(100, 50_000)`.
_MIN_SAMPLES = 100
_MAX_SAMPLES = 50_000


def _validate_samples(samples: int) -> None:
    """Reject sample counts the engine would silently rewrite.

    AUDIT 2026-08-01: the only check here was ``samples < 1``. The engine does
    not reject an out-of-range count, it clamps it - so ``samples=5`` ran 100
    and ``samples=200_000`` ran 50,000, both without a word, and the caller's
    own record said otherwise. A sample count is the lever that decides how
    much work was done and paid for.

    The MCP tool schema and the website's /api/compute both enforce this same
    range and refuse outside it. With this the three clients agree, and nobody
    is told a number ran that did not.
    """
    if isinstance(samples, bool) or not isinstance(samples, int):
        raise ZPLValidationError(
            f"samples must be an integer, got {type(samples).__name__}"
        )
    if samples < _MIN_SAMPLES or samples > _MAX_SAMPLES:
        raise ZPLValidationError(
            f"samples must be between {_MIN_SAMPLES} and {_MAX_SAMPLES:,} "
            f"(got {samples:,}). The engine clamps anything outside that range "
            f"and reports the clamped value, so this request would not run what "
            f"you asked for."
        )


def _plan_from_engine_dict(data: dict) -> PlanInfo:
    """Map one entry of ``GET /plans`` onto :class:`PlanInfo`.

    Shared by the sync and async clients so the two cannot drift; they held
    two copies of this mapping, and both copies read the same two keys the
    engine has never sent.
    """
    return PlanInfo(
        name=data.get("name", ""),
        tokens_per_month=data.get("tokens_per_month", 0),
        price_usd=data.get("price_usd", 0.0),
        max_d=data.get("max_d", 0),
        max_keys=data.get("max_keys", 0),
        unlimited=bool(data.get("unlimited", False)),
    )


def _health_from_engine_dict(data: dict) -> HealthStatus:
    """Map ``GET /health`` onto :class:`HealthStatus`.

    ``uptime_seconds`` stays None when absent rather than defaulting to 0:
    zero would claim the engine process restarted this second.
    """
    uptime = data.get("uptime_seconds")
    return HealthStatus(
        status=data.get("status", "unknown"),
        version=data.get("version", ""),
        uptime_seconds=(
            int(uptime)
            if isinstance(uptime, (int, float)) and not isinstance(uptime, bool)
            else None
        ),
    )


class BaseZPLClient:
    """Base client with common functionality."""

    DEFAULT_TIMEOUT = _ENGINE_SWEEP_CEILING_S + _NETWORK_HEADROOM_S  # 65s
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 0.5

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://engine.zeropointlogic.io",
        account_base_url: str = "https://zeropointlogic.io",
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
            timeout: Request timeout in seconds (default 65). Keep it ABOVE
                the engine's own ceilings - 30s for /compute, 60s for /sweep -
                plus headroom for the network. Below them the caller pays for
                computations it then abandons; see the note above this class.
            max_retries: Maximum number of retries for failed requests. A
                request that hits the deadline is never retried - see
                ``_make_request``.
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
        # AUDIT 2026-05-14 (HIGH): both `base_url` and `account_base_url`
        # accept any caller-supplied string. The SDK sends Authorization:
        # Bearer <api_key> to both, so an attacker-controlled hostname
        # (env, malicious wrapper config, committed .env) silently
        # exfiltrates the API key. CLI + MCP enforce a host allowlist;
        # SDK now matches. Self-hosted setups set ZPL_SDK_ALLOW_PRIVATE=1.
        self.base_url = _sanitize_base_url(base_url, "https://engine.zeropointlogic.io")
        # AUDIT 2026-05-14 (v2.0.3): account-level metadata (plan, quota,
        # usage) lives on ZPL Main, not the engine. Engine has no /usage
        # endpoint — pre-fix get_usage() hit a 404. CLI made the same
        # switch in v1.1.7. Override only for self-hosted deployments.
        self.account_base_url = _sanitize_base_url(
            account_base_url, "https://zeropointlogic.io"
        )
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
            # AUDIT 2026-05-14: env override goes through the same allowlist
            # so a poisoned ZPL_HEARTBEAT_URL can't redirect the Bearer-
            # authenticated POST to an attacker host.
            heartbeat_default = "https://zeropointlogic.io/api/auth/cli/heartbeat"
            heartbeat_env = os.environ.get("ZPL_HEARTBEAT_URL")
            url = (
                _sanitize_base_url(heartbeat_env, heartbeat_default)
                if heartbeat_env
                else heartbeat_default
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

        elif status_code == 426:
            # Forced-upgrade gate: engine's check_min_supported_version
            # rejects callers below ZPL_MIN_VERSION_SDK_PYTHON. Body is a
            # flat object with upgrade_command / minimum_version /
            # current_version / message — surface them as instance fields
            # so caller code can branch on them.
            default_cmd = "pip install -U zeropointlogic"
            composed = data.get("message") or (
                f"ZPL SDK version {data.get('current_version', '?')} is below the "
                f"supported floor (minimum {data.get('minimum_version', '?')}). "
                f"Upgrade with: {data.get('upgrade_command', default_cmd)}"
            )
            raise ZPLUpgradeRequiredError(
                composed,
                upgrade_command=data.get("upgrade_command", default_cmd),
                minimum_version=data.get("minimum_version"),
                current_version=data.get("current_version"),
                status_code=status_code,
                response_data=data,
            )

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

        # AUDIT 2026-08-02: this was `range(self.max_retries)`, which made the
        # parameter a count of ATTEMPTS while its name, its docstring and the
        # TypeScript client all say RETRIES. Measured with a counting
        # transport, no network involved:
        #
        #   max_retries=0  ->  0 requests sent, and this function fell off the
        #                      end returning None. The caller got
        #                      "AttributeError: 'NoneType' object has no
        #                      attribute 'get'" out of the result parser.
        #                      Someone asking for no retries got a client that
        #                      never contacted the engine at all.
        #   max_retries=3  ->  3 attempts, where the TypeScript client makes 4
        #                      from the same number.
        #
        # One first attempt, then that many retries. `max(1, ...)` so a
        # negative value cannot empty the loop and bring the None back.
        attempts = max(1, self.max_retries + 1)

        for attempt in range(attempts):
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
                # AUDIT 2026-08-01: this retried, up to max_retries times, and
                # it was the most expensive thing this loop could re-send. The
                # engine charges for a call before it starts computing, so once
                # the deadline fires the tokens are already spent and the
                # computation may still be running on the other side - a retry
                # buys the same work again. One user call became three billed
                # ones, and the caller saw an error either way.
                #
                # A timeout is now terminal, matching the CLI and the MCP,
                # which were fixed the same day for the same reason. With the
                # deadline raised past the engine's own ceiling, a genuine
                # overrun arrives as the engine's 504 - which refunds - rather
                # than as a client-side abort, so reaching this line means
                # something no repetition will fix.
                logger.warning(
                    "Request timed out after %ss - not retried: the engine has "
                    "already charged for this call and a retry would charge again",
                    self.timeout,
                )
                raise ZPLNetworkError(
                    f"Request timed out after {self.timeout}s. Not retried: the engine "
                    f"deducts tokens before computing, so re-sending bills you a second "
                    f"time for work that may still be running. Lower `samples` or the "
                    f"matrix dimension, or raise `timeout` above the engine's ceiling "
                    f"({_ENGINE_COMPUTE_CEILING_S}s for /compute)."
                ) from e

            except self._requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{attempts}")
                if attempt == attempts - 1:
                    raise ZPLNetworkError(f"Connection failed after {attempts} attempts") from e
                time.sleep(self.backoff_factor * (2 ** attempt))

            except self._requests.exceptions.RequestException as e:
                raise ZPLNetworkError(f"Request failed: {str(e)}") from e

        # Unreachable: `attempts` is at least 1, so the loop above either
        # returns or raises. Kept so that if the bound is ever loosened again
        # this fails loudly instead of handing back None, which is how the
        # defect above reached callers as an AttributeError in the parser.
        raise ZPLNetworkError(
            f"No request was attempted for {method} {endpoint} (max_retries={self.max_retries})"
        )

    def compute(
        self,
        matrix: list[list[int]],
        samples: int = 1000,
    ) -> ComputeResult:
        """Compute AIN (AI Neutrality Index) for a matrix.

        Args:
            matrix: Binary matrix (N×N with only 0/1 values)
            samples: Number of samples for analysis (default 1000). The engine
                accepts 100-50,000 and silently clamps anything outside that
                range, so values outside it are rejected here.

        Returns:
            ComputeResult with AIN score and analysis

        Raises:
            ZPLValidationError: If matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        self._validate_matrix(matrix)

        _validate_samples(samples)

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

    def analyze(self, matrix: list[list[int]]) -> "AnalyzeResult":
        """Analyse a specific matrix — the engine sees your data.

        ``compute()`` does not transmit the matrix. It reduces it to a
        dimension and a density of ones, sends those two numbers, and the
        engine generates fresh random matrices at that density and reports on
        those. Two entirely different inputs of equal density therefore get the
        same answer, and nothing in that response indicates the caller's data
        was never examined.

        This method posts the matrix itself. The engine runs the fold over it
        and reports what each operator family concluded, whether any needed the
        centre to break a tie, and how far the four agree.

        There is no AIN here, on purpose: one matrix is one observation, so a
        proportion over it is 0 or 1 and would say nothing about balance.

        Args:
            matrix: Binary matrix (N×N, cells 0 or 1, 3 <= N <= 100)

        Returns:
            AnalyzeResult with every family's verdict and their agreement

        Raises:
            ZPLValidationError: If the matrix is invalid
            ZPLAuthError: If the API key is invalid
            ZPLQuotaError: If quota is exceeded
            ZPLNetworkError: On connection errors
        """
        # Validated locally so a malformed matrix costs nothing: the engine
        # would refuse it anyway, and spending a round trip to learn that
        # helps no one.
        self._validate_matrix(matrix)

        response = self._make_request("POST", "/analyze", {"matrix": matrix})
        return analyze_result_from_engine_dict(response)

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

        AUDIT 2026-05-14 (v2.0.3): re-routed from ``engine/usage`` (404,
        never existed) to ``zeropointlogic.io/api/user/me``. The CLI made
        the same switch in v1.1.7. Response shape is mapped back to
        ``UsageInfo`` so existing callers see no breaking change beyond
        the fields the old endpoint never delivered.

        Returns:
            UsageInfo with plan and token details

        Raises:
            ZPLAuthError: If API key is invalid
            ZPLNetworkError: On connection errors
        """
        # Direct request to ZPL Main (not the engine). Reuses the requests
        # library + headers + timeout policy from the sync client.
        url = f"{self.account_base_url}/api/user/me"
        headers = self._get_headers()
        try:
            r = self._requests.get(url, headers=headers, timeout=self.timeout)
        except Exception as e:  # pragma: no cover — network failure path
            from .exceptions import ZPLNetworkError
            raise ZPLNetworkError(f"Failed to reach {url}: {e}")
        if r.status_code != 200:
            self._handle_error_response(r.status_code, {}, r.text or "")
        data = r.json()

        # Map ZPL Main /api/user/me → SDK UsageInfo dataclass.
        #
        # AUDIT 2026-08-01: `tokens.source` was never read. The server reports
        # it because three different failures on its side all produce
        # `used_this_month: 0`, which is also what an idle account produces -
        # so without it an unmeasured zero arrived looking exactly like a
        # measured one. Enforcement runs on the engine regardless of what this
        # endpoint managed to read, which makes a wrong zero the only warning
        # anyone gets before being refused. `UsageInfo.usage_measured`
        # whitelists the single value that means "read from the engine"; see
        # the note on that dataclass.
        tokens = data.get("tokens", {})
        return UsageInfo(
            plan=data.get("user", {}).get("plan", "unknown"),
            tokens_used=tokens.get("used_this_month", 0),
            tokens_limit=tokens.get("monthly_quota", 0),
            tokens_remaining=tokens.get("remaining", 0),
            reset_date="",  # legacy field; ZPL Main computes via cycles, not absolute dates
            requests_made=0,  # ZPL Main aggregates by tokens, not raw request count
            last_reset="",
            source=tokens.get("source"),
            engine_unreachable=bool(tokens.get("engine_unreachable", False)),
        )

    def get_plans(self) -> list[PlanInfo]:
        """Get available pricing plans.

        AUDIT 2026-08-01: this read `price_eur` and `features` out of the
        response. The engine sends neither - it sends `{name, max_d,
        tokens_per_month, max_keys, price_usd, unlimited}` - so both defaults
        fired on every plan, every time, and the dataclass then printed a
        fabricated EUR price. It also discarded `max_d` and `max_keys`, the two
        fields that say what a plan actually permits. Now mapped to what the
        endpoint returns.

        Returns:
            List of PlanInfo, one per plan the engine publishes

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = self._make_request("GET", "/plans")
        return [_plan_from_engine_dict(p) for p in response.get("plans", [])]

    def get_health(self) -> HealthStatus:
        """Check engine health status.

        AUDIT 2026-08-01: this read four metrics the engine has never sent
        (`uptime_percent`, `response_time_ms`, `requests_per_second`,
        `error_rate_percent`) and ignored the one it does (`uptime_seconds`).
        See HealthStatus for what /health actually returns.

        Returns:
            HealthStatus with the engine's status, version and process uptime

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = self._make_request("GET", "/health")
        return _health_from_engine_dict(response)

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

        # One first attempt, then that many retries - see the note in
        # ZPLClient._make_request. Both clients read the same parameter and
        # must not disagree about what it counts.
        attempts = max(1, self.max_retries + 1)

        for attempt in range(attempts):
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
                # AUDIT 2026-08-01: terminal for the same reason as the sync
                # client above - the engine has already deducted the tokens by
                # the time this fires, so a retry pays for the same computation
                # twice. See the note in ZPLClient._make_request.
                logger.warning(
                    "Request timed out after %ss - not retried: the engine has "
                    "already charged for this call and a retry would charge again",
                    self.timeout,
                )
                raise ZPLNetworkError(
                    f"Request timed out after {self.timeout}s. Not retried: the engine "
                    f"deducts tokens before computing, so re-sending bills you a second "
                    f"time for work that may still be running. Lower `samples` or the "
                    f"matrix dimension, or raise `timeout` above the engine's ceiling "
                    f"({_ENGINE_COMPUTE_CEILING_S}s for /compute)."
                ) from e

            except self._httpx.ConnectError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{attempts}")
                if attempt == attempts - 1:
                    raise ZPLNetworkError(f"Connection failed after {attempts} attempts") from e
                await self._sleep(self.backoff_factor * (2 ** attempt))

            except self._httpx.HTTPError as e:
                raise ZPLNetworkError(f"Request failed: {str(e)}") from e

        # Unreachable, and kept for the same reason as in the sync client.
        raise ZPLNetworkError(
            f"No request was attempted for {method} {endpoint} (max_retries={self.max_retries})"
        )

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
            samples: Number of samples for analysis (default 1000). The engine
                accepts 100-50,000 and silently clamps anything outside that
                range, so values outside it are rejected here.

        Returns:
            ComputeResult with AIN score and analysis

        Raises:
            ZPLValidationError: If matrix is invalid
            ZPLAuthError: If API key is invalid
            ZPLQuotaError: If quota exceeded
            ZPLNetworkError: On connection errors
        """
        self._validate_matrix(matrix)

        _validate_samples(samples)

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

    async def analyze(self, matrix: list[list[int]]) -> "AnalyzeResult":
        """Analyse a specific matrix (async) — the engine sees your data.

        ``compute()`` does not transmit the matrix. It reduces it to a
        dimension and a density of ones, sends those two numbers, and the
        engine generates fresh random matrices at that density and reports on
        those. Two entirely different inputs of equal density therefore get the
        same answer, and nothing in that response indicates the caller's data
        was never examined.

        This method posts the matrix itself. The engine runs the fold over it
        and reports what each operator family concluded, whether any needed the
        centre to break a tie, and how far the four agree.

        There is no AIN here, on purpose: one matrix is one observation, so a
        proportion over it is 0 or 1 and would say nothing about balance.

        Args:
            matrix: Binary matrix (N×N, cells 0 or 1, 3 <= N <= 100)

        Returns:
            AnalyzeResult with every family's verdict and their agreement

        Raises:
            ZPLValidationError: If the matrix is invalid
            ZPLAuthError: If the API key is invalid
            ZPLQuotaError: If quota is exceeded
            ZPLNetworkError: On connection errors
        """
        # Validated locally so a malformed matrix costs nothing: the engine
        # would refuse it anyway, and spending a round trip to learn that
        # helps no one.
        self._validate_matrix(matrix)

        response = await self._make_request("POST", "/analyze", {"matrix": matrix})
        return analyze_result_from_engine_dict(response)

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

        AUDIT 2026-05-14 (v2.0.3): see sync counterpart — re-routed from
        ``engine/usage`` (404) to ``zeropointlogic.io/api/user/me``.

        Returns:
            UsageInfo with plan and token details

        Raises:
            ZPLAuthError: If API key is invalid
            ZPLNetworkError: On connection errors
        """
        client = await self._ensure_client()
        url = f"{self.account_base_url}/api/user/me"
        headers = self._get_headers()
        try:
            r = await client.get(url, headers=headers, timeout=self.timeout)
        except Exception as e:  # pragma: no cover — network failure path
            from .exceptions import ZPLNetworkError
            raise ZPLNetworkError(f"Failed to reach {url}: {e}")
        if r.status_code != 200:
            self._handle_error_response(r.status_code, {}, r.text or "")
        data = r.json()

        # See the sync counterpart for why `source` and `engine_unreachable`
        # are read: an unmeasured zero must not be reported as measured usage.
        tokens = data.get("tokens", {})
        return UsageInfo(
            plan=data.get("user", {}).get("plan", "unknown"),
            tokens_used=tokens.get("used_this_month", 0),
            tokens_limit=tokens.get("monthly_quota", 0),
            tokens_remaining=tokens.get("remaining", 0),
            reset_date="",
            requests_made=0,
            last_reset="",
            source=tokens.get("source"),
            engine_unreachable=bool(tokens.get("engine_unreachable", False)),
        )

    async def get_plans(self) -> list[PlanInfo]:
        """Get available pricing plans (async).

        See the sync counterpart: the response carries no EUR price and no
        feature list, and does carry max_d / max_keys.

        Returns:
            List of PlanInfo, one per plan the engine publishes

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = await self._make_request("GET", "/plans")
        return [_plan_from_engine_dict(p) for p in response.get("plans", [])]

    async def get_health(self) -> HealthStatus:
        """Check engine health status (async).

        See the sync counterpart: /health returns status, version and
        uptime_seconds, and no performance metrics.

        Returns:
            HealthStatus with the engine's status, version and process uptime

        Raises:
            ZPLNetworkError: On connection errors
        """
        response = await self._make_request("GET", "/health")
        return _health_from_engine_dict(response)

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
