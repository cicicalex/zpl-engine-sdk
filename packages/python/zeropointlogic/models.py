"""Data models for ZPL Engine SDK."""

from dataclasses import dataclass
from typing import Literal
from datetime import datetime


AIStatusType = Literal[
    "CERTIFIED_NEUTRAL",
    "STABLE",
    "MODERATE_BIAS",
    "HIGH_BIAS",
    "CRITICAL_BIAS",
]

BiasLevel = Literal["none", "low", "moderate", "high", "critical"]


def ain_to_bias_level(ain: float) -> BiasLevel:
    """Convert AIN score (0-1) into a bias-level classification.

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

    Attributes:
        ain: AI Neutrality Index (0-1), higher is more neutral
        p_output: Probability output from the model
        deviation: Standard deviation from expected distribution
        status: Classification of bias level (CERTIFIED_NEUTRAL, STABLE, etc.)
        tokens_used: Number of tokens consumed by this request
        tokens_remaining: Number of tokens left when the API returns it (else 0)
        matrix_size: Size of input matrix (N×N)
        samples: Number of samples used
        ain_status: Engine AIN band label when present
        compute_ms: Server-side compute time when present
    """

    ain: float
    p_output: float
    deviation: float
    status: AIStatusType
    tokens_used: int
    tokens_remaining: int
    matrix_size: int | None = None
    samples: int | None = None
    ain_status: str | None = None
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
        """Check if status indicates stability.

        Returns:
            True if status is CERTIFIED_NEUTRAL or STABLE
        """
        return self.status in ("CERTIFIED_NEUTRAL", "STABLE")

    def has_bias(self) -> bool:
        """Check if status indicates bias.

        Returns:
            True if status contains BIAS
        """
        return "BIAS" in self.status

    @property
    def bias_level(self) -> BiasLevel:
        """Bias-level classification derived from `ain`.

        Mirrors `biasLevel` on the TypeScript ComputeResult so cross-language
        code can switch on the same set of labels.
        """
        return ain_to_bias_level(self.ain)

    def __str__(self) -> str:
        return f"ComputeResult(ain={self.ain:.3f}, status={self.status}, tokens={self.tokens_remaining} left)"


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

    Attributes:
        status: Overall status (up, degraded, down)
        uptime_percent: Uptime percentage (0-100)
        response_time_ms: Average response time in milliseconds
        requests_per_second: Current requests per second
        error_rate_percent: Error rate percentage (0-100)
        last_check: ISO timestamp of last health check
        version: Engine API version
    """

    status: Literal["up", "degraded", "down"]
    uptime_percent: float
    response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    last_check: datetime | str
    version: str

    def is_healthy(self) -> bool:
        """Check if engine is healthy.

        Returns:
            True if status is 'up' and uptime > 99%
        """
        return self.status == "up" and self.uptime_percent >= 99.0

    def __str__(self) -> str:
        return f"HealthStatus({self.status}, {self.uptime_percent:.2f}% uptime, {self.response_time_ms:.0f}ms)"
