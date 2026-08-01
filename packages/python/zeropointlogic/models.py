"""Data models for ZPL Engine SDK."""

# AUDIT 2026-08-01: required for the `X | Y` annotations below.
# pyproject declares requires-python = ">=3.9" and classifies 3.9, but PEP 604
# unions are only evaluable at runtime from 3.10. Every use in this package is in
# annotation position (checked with ast: 27 in annotations, 0 outside), so making
# annotations lazy keeps the declared floor honest instead of narrowing support.
from __future__ import annotations

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

# A five-label view of the engine's six `ain_status` bands. Six into five needs
# exactly one merge, and it is made at the top - between the two strongest
# neutral bands - where the distinction is how neutral a reading is rather than
# how biased:
#
#   none      CERTIFIED_NEUTRAL (>= 0.96) + HIGHLY_NEUTRAL (>= 0.90)
#   low       NEUTRAL           (>= 0.80)
#   moderate  MODERATE_BIAS     (>= 0.60)
#   high      SIGNIFICANT_BIAS  (>= 0.40)
#   critical  HIGH_BIAS         (<  0.40)
#
# Every boundary is an engine boundary; none was chosen here. The split that
# matters - between the labels meaning "not biased" (none, low) and those
# meaning "biased" (moderate, high, critical) - is the engine's own NEUTRAL
# floor of 0.80, so this scale cannot contradict `ain_status`.
BiasLevel = Literal["none", "low", "moderate", "high", "critical"]

_AIN_STATUS_TO_BIAS_LEVEL: dict[str, BiasLevel] = {
    "CERTIFIED_NEUTRAL": "none",
    "HIGHLY_NEUTRAL": "none",
    "NEUTRAL": "low",
    "MODERATE_BIAS": "moderate",
    "SIGNIFICANT_BIAS": "high",
    "HIGH_BIAS": "critical",
}


def ain_to_bias_level(ain: float) -> BiasLevel:
    """Convert an AIN score (float 0.0-1.0) into a bias-level classification.

    AUDIT 2026-08-01: the bands were 0.8 / 0.7 / 0.5 / 0.3, none of them an
    edge the engine recognises. The 2026-07-31 pass aligned ``interpret_ain``
    to the engine's six bands and left this function - the one that populates
    ``ComputeResult.bias_level`` - on the old scale. At ain 0.75 the engine
    says MODERATE_BIAS and this said "low", the label for a reading with
    almost no bias, so one result object disagreed with itself.

    The boundaries below are the engine's own, from crates/zpl-core/src/ain.rs.
    Mirrors ``ainToBiasLevel`` in the TypeScript SDK so the same reading gets
    the same label whichever language a team uses.
    """
    if ain >= 0.90:
        return "none"
    if ain >= 0.80:
        return "low"
    if ain >= 0.60:
        return "moderate"
    if ain >= 0.40:
        return "high"
    return "critical"


def bias_level_from_ain_status(ain_status: str) -> BiasLevel | None:
    """Bias level for an ``ain_status`` band, or None if the band is unknown.

    Preferred over :func:`ain_to_bias_level` whenever the engine sent a band:
    the band IS the engine's classification of that reading, so deriving from
    it cannot land on the far side of a boundary the way re-deriving from the
    float can.
    """
    return _AIN_STATUS_TO_BIAS_LEVEL.get(ain_status)


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
    p_output: float | None = None
    """The engine's own measurement: output balance, 0.500 being equilibrium.

    ``ain`` is derived from this through an absolute value and so cannot say
    which side of equilibrium a reading sits on — 0.4687 and 0.5313 both give
    AIN 0.9373. Read ``p_output`` when the direction of the imbalance matters,
    and compare it against 0.5 rather than against 1.

    ``None`` when the engine did not report it, never 0.0: a balance of zero
    would mean the output stream was entirely zeros, a real and very different
    claim from "not reported".
    """

    deviation: float | None = None
    """Distance from equilibrium as the engine reports it, when present."""
    tokens_remaining: int | None = None
    matrix_size: int | None = None
    samples: int | None = None
    ain_status: AINStatusType | None = None
    compute_ms: float | None = None

    def is_neutral(self, threshold: float | None = None) -> bool:
        """Check whether the engine considers this reading neutral.

        AUDIT 2026-08-01: the default threshold was 0.7, which sits inside the
        engine's MODERATE_BIAS band (0.60-0.80). Every reading between 0.70 and
        0.80 was called neutral here and biased by the engine that produced it,
        in the same object - ``ain_status`` said MODERATE_BIAS while
        ``is_neutral()`` said True.

        With no threshold the engine decides: its own band when it sent one
        (the three neutral bands are those without BIAS in the name), its
        NEUTRAL floor of 0.80 when it did not. Passing a threshold explicitly
        still compares against ``ain`` and is unchanged - a caller who has
        decided 0.65 is neutral enough for their own purpose is answering a
        different question and is left alone.

        Args:
            threshold: optional AIN threshold. Omit to use the engine's verdict.

        Returns:
            True if the reading is neutral by whichever rule applies.
        """
        if threshold is not None:
            return self.ain >= threshold
        if self.ain_status is not None:
            return "BIAS" not in self.ain_status
        return self.ain >= 0.80

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
        """Bias-level classification for this reading.

        Taken from ``ain_status`` when the engine sent a band, since that is
        the engine's own verdict, and from ``ain`` on the engine's boundaries
        when it did not. Deriving this and ``is_neutral()`` from the same
        source is what stops them disagreeing at a band edge.

        Mirrors `biasLevel` on the TypeScript ComputeResult so cross-language
        code can switch on the same set of labels.
        """
        if self.ain_status is not None:
            from_band = bias_level_from_ain_status(self.ain_status)
            if from_band is not None:
                return from_band
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

    input_ones: Optional[int] = None
    """Cells set to 1 in the matrix you sent.

    AUDIT 2026-07-31: the engine was swept over 3..=100. At every even
    dimension the four family bits for an all-zeros matrix are identical to
    those for an all-ones matrix - 49 of 49 even dimensions, none of the 49 odd
    ones - so the two most opposite inputs you can send came back with the same
    verdict. Every paid ceiling except Pro's 25 is even: 16, 32, 48, 64, 100.

    This and the two fields below are your own matrix counted back to you, so a
    degenerate input stays visible whatever the verdict says.

    ``None`` when the engine predates the sweep. Check for ``None`` rather than
    treating it as 0 - an ``input_ones`` of 0 means an all-zeros matrix, which
    is a real answer, not a missing one.
    """

    cells: Optional[int] = None
    """Total cells, so ``input_ones`` can be read as a proportion."""

    degenerate: Optional[bool] = None
    """Every cell identical. The verdict alone cannot show this at even n."""

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
        source: How the server obtained ``tokens_used`` - see below.
        engine_unreachable: The server could not reach the engine database
            while answering, so the figures may be up to an hour stale.

    AUDIT 2026-08-01: ``source`` was on the wire and this SDK never read it.
    ZPL Main added the field because three different server-side failures all
    produce ``used_this_month: 0``, which is also what a genuinely idle account
    produces. Measured on production: 200 tokens were spent on the engine and
    the endpoint reported 0 used, before and after, with no way to tell from
    outside. Only ``"engine_log"`` means the number was read from the engine's
    usage log; ``"engine_user_not_found"`` means the two databases disagree
    about who this account is, and ``"user_table_fallback"`` means the engine
    could not be reached.

    Enforcement does not go through this endpoint - the engine deducts
    atomically on every request - so an unmeasured zero is not cosmetic. It is
    the only warning anyone gets before being refused. Read
    :attr:`usage_measured` rather than comparing the string: it whitelists the
    one value that means "measured", so a source added on the server later
    reads as not-measured until someone decides otherwise. The CLI's ``whoami``
    and ``quota`` were tightened the same way.
    """

    plan: str
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    reset_date: datetime | str
    requests_made: int
    last_reset: datetime | str
    source: str | None = None
    engine_unreachable: bool = False

    @property
    def usage_measured(self) -> bool:
        """True only when the server actually read usage from the engine.

        When False, ``tokens_used``, ``tokens_remaining`` and
        ``usage_percent`` are the only figures the server had, not the right
        ones. Display them as unknown.
        """
        return self.source == "engine_log"

    @property
    def usage_percent(self) -> float:
        """Get usage as percentage (0-100).

        Meaningful only when :attr:`usage_measured` is True; it is computed
        from ``tokens_used``, which the server may not have been able to read.
        """
        if self.tokens_limit == 0:
            return 0.0
        return (self.tokens_used / self.tokens_limit) * 100

    @property
    def is_unlimited(self) -> bool:
        """Check if plan is unlimited."""
        return self.tokens_limit == 0 or self.tokens_limit < 0

    def __str__(self) -> str:
        # A figure the server could not stand behind must not be printed as a
        # measurement. The plan's allowance is a property of the plan rather
        # than a reading, so it stays visible either way.
        if not self.usage_measured:
            why = self.source or "not reported"
            return (
                f"UsageInfo(plan={self.plan}, usage unknown "
                f"(source={why}), quota {self.tokens_limit})"
            )
        if self.is_unlimited:
            return f"UsageInfo(plan={self.plan}, unlimited, {self.requests_made} requests)"
        return f"UsageInfo(plan={self.plan}, {self.usage_percent:.1f}% used, {self.tokens_remaining} left)"


@dataclass
class PlanInfo:
    """One plan, exactly as ``GET /plans`` returns it.

    AUDIT 2026-08-01: this carried ``price_eur`` and ``features``, neither of
    which the engine has ever sent. Both were read with ``.get(..., default)``
    from a payload that never carries the key, so ``features`` was always ``[]``
    and ``price_eur`` always 0.0 - which ``__str__`` then printed as
    "Basic (EUR 0.00/mo)" for a plan that costs 10 USD. Wrong currency and
    wrong number in one line. No EUR pricing exists anywhere in the system:
    not in the engine plan table, not in the website constants, not in this
    response, and Stripe charges USD. The same fabricated column was removed
    from the PyPI landing page on 2026-07-31 and is pinned by a test.

    Meanwhile ``max_d`` and ``max_keys`` - which the engine does send, and
    which decide what a plan actually lets you do - were dropped on the floor.
    The fields below are the engine's, and only the engine's.

    Attributes:
        name: Plan name (Free, Basic, Pro, GamePro, Studio, Agent, Enterprise,
            Enterprise XL)
        tokens_per_month: Monthly token allowance
        max_d: Largest matrix dimension this plan may send
        max_keys: Simultaneously active API keys this plan may hold
        price_usd: Monthly price in USD - the only currency in the system
        unlimited: The engine's ``unlimited`` flag. NOT an absence of a cap:
            the engine sets it for any plan at or above 50,000,000 tokens per
            month, which today is Enterprise XL alone - and 50,000,000 is
            precisely the ceiling that plan is metered against.
            ``tokens_per_month`` is the number that is enforced.
    """

    name: str
    tokens_per_month: int
    price_usd: float
    max_d: int = 0
    max_keys: int = 0
    unlimited: bool = False

    def is_free(self) -> bool:
        """Check if this is the free plan."""
        return self.price_usd == 0

    def __str__(self) -> str:
        if self.is_free():
            return f"{self.name} (Free, {self.tokens_per_month:,} tokens/mo)"
        return f"{self.name} (${self.price_usd:.2f}/mo, {self.tokens_per_month:,} tokens)"


@dataclass
class HealthStatus:
    """Engine health, exactly as ``GET /health`` returns it.

    AUDIT 2026-08-01: this declared ``uptime_percent``, ``response_time_ms``,
    ``requests_per_second``, ``error_rate_percent`` and ``last_check``. The
    engine's health handler returns ``{status, version, uptime_seconds}`` and
    has never measured any of the five, so all of them were permanently None -
    and the README's own quickstart line, ``f"Uptime:
    {health.uptime_percent:.2f}%"``, raised TypeError on None for anyone who
    copied it. Keeping fields that can only ever be None does not make them
    optional metrics, it makes them a promise the engine never made, so they
    are gone and the one number the engine does report has taken their place.

    Attributes:
        status: The engine sends the literal ``"ok"`` and has no other value -
            the handler builds it from a constant, so there is no degraded or
            down reading to branch on. A ``get_health()`` call that returns at
            all is the signal that the engine answered.
        version: Engine version (its own ``CARGO_PKG_VERSION``).
        uptime_seconds: Seconds since the engine process started. ``None``
            when the engine did not send it, never 0 - zero would mean the
            process restarted this second, which is a real and very different
            reading.
    """

    status: str
    version: str = ""
    uptime_seconds: int | None = None

    def is_healthy(self) -> bool:
        """Check if the engine answered and reported itself up.

        "ok" is what today's engine sends; "up" is accepted as well so a
        deployment that relabels it does not read as an outage. There is no
        uptime figure to threshold against - the endpoint reports how long the
        process has been running, not what fraction of the time it was up.
        """
        return self.status in ("up", "ok")

    def __str__(self) -> str:
        uptime = (
            f"up {self.uptime_seconds}s"
            if self.uptime_seconds is not None
            else "uptime n/a"
        )
        ver = f", v{self.version}" if self.version else ""
        return f"HealthStatus({self.status}{ver}, {uptime})"
