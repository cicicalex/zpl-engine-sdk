"""Normalize engine JSON (snake_case) into SDK-friendly fields."""

from __future__ import annotations

from typing import Any

from zeropointlogic.models import AINStatusType, ComputeResult, StabilityStatusType

# `status` — stability regime. Plain "INHIBITED" is not a member.
# Pre-fix this set held the AIN bands instead, so a real INHIBITED_HIGH /
# INHIBITED_LOW / ACTIVE from the engine was silently rewritten to
# "STABLE" — the SDK reported the opposite of what the engine said.
_VALID_STATUS: frozenset[str] = frozenset(
    {
        "STABLE",
        "ACTIVE",
        "INHIBITED_HIGH",
        "INHIBITED_LOW",
    }
)

# `ain_status` — AIN band. A different field from `status`.
_VALID_AIN_STATUS: frozenset[str] = frozenset(
    {
        "CERTIFIED_NEUTRAL",
        "HIGHLY_NEUTRAL",
        "NEUTRAL",
        "MODERATE_BIAS",
        "SIGNIFICANT_BIAS",
        "HIGH_BIAS",
    }
)


def _num(data: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for k in keys:
        v = data.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return default


def _int_num(data: dict[str, Any], *keys: str, default: int = 0) -> int:
    return int(round(_num(data, *keys, default=float(default))))


def compute_result_from_engine_dict(
    data: dict[str, Any],
    *,
    matrix_size: int | None = None,
    samples: int | None = None,
) -> ComputeResult:
    """Map raw ``/compute`` JSON into :class:`ComputeResult`."""
    status_raw = data.get("status")
    if isinstance(status_raw, str) and status_raw in _VALID_STATUS:
        status: StabilityStatusType = status_raw  # type: ignore[assignment]
    else:
        status = "STABLE"

    ain_status = data.get("ain_status")
    ain_status_s: AINStatusType | None = (
        ain_status  # type: ignore[assignment]
        if isinstance(ain_status, str) and ain_status in _VALID_AIN_STATUS
        else None
    )

    cm = data.get("compute_ms")
    compute_ms = float(cm) if isinstance(cm, (int, float)) and not isinstance(cm, bool) else None

    # AUDIT 2026-05-13 (D3 + D4): p_output / deviation removed from
    # ComputeResult to plug an IP leak. tokens_remaining is now
    # Optional and only populated when the engine actually returned a
    # value (None means "ask /usage").
    tokens_remaining_present = "tokens_remaining" in data or "tokensRemaining" in data
    tokens_remaining_val: int | None = (
        _int_num(data, "tokens_remaining", "tokensRemaining", default=0)
        if tokens_remaining_present
        else None
    )

    return ComputeResult(
        ain=_num(data, "ain", default=0.0),
        status=status,
        tokens_used=_int_num(data, "tokens_used", "tokensUsed", default=0),
        tokens_remaining=tokens_remaining_val,
        matrix_size=matrix_size,
        samples=samples,
        ain_status=ain_status_s,
        compute_ms=compute_ms,
    )


def analyze_result_from_engine_dict(payload: dict) -> "AnalyzeResult":
    """Build an AnalyzeResult from the engine's /analyze response.

    Kept beside the compute normaliser so both wire shapes are translated in
    one place. Unlike compute, nothing is dropped here: the analyze response
    carries no probability and no deviation to withhold — one matrix is one
    observation, so there is no distribution to summarise.

    Tolerant of a missing `families` list rather than raising: an empty result
    is visibly empty to the caller, whereas a KeyError deep in the SDK would
    surface as an unrelated crash.
    """
    from zeropointlogic.models import AnalyzeResult, FamilyVerdict

    families = [
        FamilyVerdict(
            family=int(f.get("family", i)),
            bit=1 if f.get("bit") == 1 else 0,
            tie_broken=bool(f.get("tie_broken", False)),
        )
        for i, f in enumerate(payload.get("families") or [])
    ]
    return AnalyzeResult(
        n=int(payload.get("n", 0)),
        families=families,
        ones=int(payload.get("ones", sum(f.bit for f in families))),
        unanimous=bool(payload.get("unanimous", False)),
        tokens_used=int(payload.get("tokens_used", 0)),
        compute_ms=payload.get("compute_ms"),
    )
