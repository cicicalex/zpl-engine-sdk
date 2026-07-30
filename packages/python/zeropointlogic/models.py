"""Data models for ZPL Engine SDK."""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime


# `ain_status` — quality of the balance, derived from `ain`.
# Bands (inclusive lower bound): CERTIFIED_NEUTRAL >= 0.96,
# HIGHLY_NEUTRAL >= 0.90, NEUTRAL >= 0.80, MODERATE_BIAS >= 0.60,
# SIGNIFICANT_BIAS >= 0.40, HIGH_BIAS < 0.40.
#
# Pre-fix a single `AIStatusType` mixed these values with the `status`
# values (`STABLE`), invented a `CRITICAL_BIAS` member no engine returns,
# and omitted HIGHLY_NEUTRAL / NEUTRAL / SIGNIFICANT_BIAS entirely.
AINStatusType = Literal[
    "CERTIFIED_NEUTRAL",
    "HIGHLY_NEUTRAL",
    "NEUTRAL",
    "MODERATE_BIAS",
    "SIGNIFICANT_BIAS",
    "HIGH_BIAS",
]

# `status` — stability regime. A DIFFERENT field from `ain_status`.
# Plain "INHIBITED" does not exist; only the _HIGH / _LOW variants do.
StabilityStatusType = Literal[
    "STABLE",
    "ACTIVE",
    "INHIBITED_HIGH",
    "INHIBITED_LOW",
]

# Backwards-compatible alias for the old (incorrect) single union. It now
# points at the `ain_status` band enum, which is what most callers meant.
AIStatusType = AINStatusType

BiasLevel = Literal["none", "low", "moderate", "high", "critical"]


def ain_to_bias_level(ain: float) -> BiasLevel:
    """Convert AIN score (float 0.0-1.0) into a bias-level classification.

    Mirrors `ainToBiasLevel` in the TypeScript SDK so users get the same
    label whichever language they choose.
    """
    if ain >= 0.8:
        return "none"
    if ain >= 0.7:
        return "low"
    if ain >= 0.5:
        return "moderate"
    if ain >= 0.3:
        return "high"
    return "critical"


@dataclass
class ComputeResult:
    """Result from a compute operation.

    AUDIT 2026-05-13 (BUG D3 — IP LEAK + D4 tokens display):

    Pre-fix this dataclass exposed `p_output: float` and `deviation: float`
    as required, documented attributes. The MCP server intentionally hides
    those fields (see `mcp/src/index.ts` "IP protection: expose AIN score
    + status only"). The SDK contradicting that policy meant internal
    probability + deviation scalars shipped in every wheel and were
    documented in the public README. Per the "Live Engine Only" rule
    and the trade-secret strategy, both fields are removed from the
    public surface. The wire response still carries them but the SDK
    normaliser drops them before constructing this dataclass.

    `tokens_remaining` is now Optional[int]: pre-fix it defaulted to 0
    when the engine didn't return a value, which scared every fresh
    user with "tokens=0 left" on their first compute even though they
    had 50M left. `None` now means "engine didn't tell us"; the __str__
    prints "tokens=n/a" in that case and consumers should call
    `client.get_usage()` for live quota.

    Attributes:
        ain: AI Neutrality Index — float on the 0.0-1.0 scale with 6
            decimals, higher is more neutral. Display as a percentage with
            ``f"{ain * 100:.2f}"``; never ``round(ain * 100)``, which
            discards 4 of the 6 decimals.
        status: Stability regime (STABLE / ACTIVE / INHIBITED_HIGH /
            INHIBITED_LOW). NOT the AIN band — see `ain_status`.
        tokens_used: Number of tokens consumed by this request
        tokens_remaining: Tokens left when the engine actually returns it,
            else None.
        matrix_size: Size of input matrix (N×N)
        samples: Number of samples used
        ain_status: AIN band label when present (CERTIFIED_NEUTRAL …
            HIGH_BIAS). A different field from `status`.
        compute_ms: Server-side compute time when present
    """

    ain: float
    status: StabilityStatusType
    tokens_used: int
    tokens_remaining: int | None = None
    matrix_size: int | None = None
    samples: int | None = None
    ain_status: AINStatusType | None = None
    compute_ms: float | None = None

    def is_neutral(self, threshold: float = 0.7) -> bool:
        """Check if result is considered neutral.

        Args:
            threshold: AIN threshold (default 0.7)

        Returns:
            True if ain >= threshold
        """
        return self.ain >= threshold

    def is_stable(self) -> bool:
        """Check if the stability regime indicates stability.

        Returns:
            True if status is STABLE. (Pre-fix this also accepted
            CERTIFIED_NEUTRAL, which belongs to `ain_status`, not
            `status`.)
        """
        return self.status == "STABLE"

    def has_bias(self) -> bool:
        """Check if the AIN band indicates bias.

        Reads `ain_status`, not `status`: the bias bands live on
        `ain_status`. Falls back to the `ain` value when the engine did
        not send a band.

        Returns:
            True if the AIN band is one of the *_BIAS values.
        """
        if self.ain_status is not None:
            return "BIAS" in self.ain_status
        return self.ain < 0.80

    @property
    def bias_level(self) -> BiasLevel:
        """Bias-level classification derived from `ain`.

        Mirrors `biasLevel` on the TypeScript ComputeResult so cross-language
        code can switch on the same set of labels.
        """
        return ain_to_bias_level(self.ain)

    def __str__(self) -> str:
        rem = (
            f"{self.tokens_remaining} left"
            if self.tokens_remaining is not None
            else "tokens=n/a (call get_usage())"
        )
        # 6 decimals: `ain` is delivered on the 0.0-1.0 scale with 6
        # decimals and the default repr must not silently truncate it.
        return f"ComputeResult(ain={self.ain:.6f}, status={self.status}, used={self.tokens_used}, {rem})"


@dataclass
class FamilyVerdict:
    """One operator family's verdict on a supplied matrix."""

    family: int
    """Index into the engine's fixed family list."""

    bit: int
    """The family's output bit for this matrix: 0 or 1."""

    tie_broken: bool
    """
    The fold reached an exact tie and the centre decided it.

    A tie means no majority was found at all — a weaker result than a
    confident bit, and anything presenting a verdict should say so rather
    than hide the difference.
    """

    def __repr__(self) -> str:
        tie = ", tie-broken" if self.tie_broken else ""
        return f"FamilyVerdict(family={self.family}, bit={self.bit}{tie})"


@dataclass
class AnalyzeResult:
    """What the method determines about one specific matrix.

    Deliberately carries no ``ain`` and no ``p_output``. Both describe how
    output bits distribute across many sampled matrices; over a single matrix
    the proportion is 0 or 1 and says nothing about balance. A score here would
    be an invented number wearing the clothes of a measurement.
    """

    n: int
    """Dimension of the matrix that was analysed."""

    families: list["FamilyVerdict"]
    """Every family's verdict, in engine order."""

    ones: int
    """How many families returned 1."""

    unanimous: bool
    """
    All families agreed. Unanimity is a stronger result than a three-to-one
    split, and the engine's pooled reading could not express the difference.
    """

    tokens_used: int = 0
    compute_ms: Optional[float] = None

    def __repr__(self) -> str:
        bits = "".join(str(f.bit) for f in self.families)
        agree = "unanimous" if self.unanimous else f"{self.ones}/{len(self.families)} say 1"
        return f"AnalyzeResult(n={self.n}, bits={bits}, {agree})"


@dataclass
class UsageInfo:
    """API usage information.

    Attributes:
        plan: Current plan tier
        tokens_used: Total tokens used in current period
        tokens_limit: Total tokens allowed in current period
        tokens_remaining: Tokens available until next reset
        reset_date: When the token limit resets
        requests_made: Number of API requests made
        last_reset: When tokens were last reset
    """

    plan: str
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    reset_date: datetime | str
    requests_made: int
    last_reset: datetime | str

    @property
    def usage_percent(self) -> float:
        """Get usage as percentage (0-100)."""
        if self.tokens_limit == 0:
            return 0.0
        return (self.tokens_used / self.tokens_limit) * 100

    @property
    def is_unlimited(self) -> bool:
        """Check if plan is unlimited."""
        return self.tokens_limit == 0 or self.tokens_limit < 0

    def __str__(self) -> str:
        if self.is_unlimited:
            return f"UsageInfo(plan={self.plan}, unlimited, {self.requests_made} requests)"
        return f"UsageInfo(plan={self.plan}, {self.usage_percent:.1f}% used, {self.tokens_remaining} left)"


@dataclass
class PlanInfo:
    """Information about a pricing plan.

    Attributes:
        name: Plan name (Free, Basic, Pro, GamePro, Studio, Agent, Enterprise, XL)
        tokens_per_month: Monthly token allowance
        price_usd: Monthly price in USD
        price_eur: Monthly price in EUR
        features: List of features included
    """

    name: str
    tokens_per_month: int
    price_usd: float
    price_eur: float
    features: list[str]

    def is_free(self) -> bool:
        """Check if this is the free plan."""
        return self.price_usd == 0 and self.price_eur == 0

    def __str__(self) -> str:
        if self.is_free():
            return f"{self.name} (Free, {self.tokens_per_month:,} tokens/mo)"
        return f"{self.name} (€{self.price_eur:.2f}/mo, {self.tokens_per_month:,} tokens)"


@dataclass
class HealthStatus:
    """Engine health status.

    All metric fields are Optional because the engine `/health` endpoint
    currently returns only `{status, version}` — the latency/uptime/RPS
    metrics are not yet exposed. Pre-v2.0.1 the SDK defaulted these to 0
    which rendered as "0.00% uptime, 0ms" in `__str__`, falsely implying
    the engine was offline. Now we display "n/a" for unknown fields.

    Attributes:
        status: Overall status (ok / up / degraded / down).
        version: Engine API version (e.g. "3.1.0").
        uptime_percent: Uptime percentage (0-100) when reported, else None.
        response_time_ms: Average response time in ms when reported.
        requests_per_second: Current RPS when reported.
        error_rate_percent: Error rate percentage when reported.
        last_check: ISO timestamp of last health check when reported.
    """

    status: str
    version: str = ""
    uptime_percent: float | None = None
    response_time_ms: float | None = None
    requests_per_second: float | None = None
    error_rate_percent: float | None = None
    last_check: datetime | str | None = None

    def is_healthy(self) -> bool:
        """Check if engine is healthy.

        Returns:
            True if status is "up"/"ok" and uptime is either None (not
            reported) OR >= 99%. Returning True on None preserves the
            sensible default that "no metric = no problem" for an engine
            that hasn't shipped metrics yet.
        """
        if self.status not in ("up", "ok"):
            return False
        if self.uptime_percent is None:
            return True
        return self.uptime_percent >= 99.0

    def __str__(self) -> str:
        uptime = (
            f"{self.uptime_percent:.2f}% uptime"
            if self.uptime_percent is not None
            else "uptime n/a"
        )
        latency = (
            f"{self.response_time_ms:.0f}ms"
            if self.response_time_ms is not None
            else "latency n/a"
        )
        ver = f", v{self.version}" if self.version else ""
        return f"HealthStatus({self.status}{ver}, {uptime}, {latency})"
