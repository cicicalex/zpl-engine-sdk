"""Normalize engine JSON (snake_case) into SDK-friendly fields."""

from __future__ import annotations

from typing import Any

from zeropointlogic.models import AIStatusType, ComputeResult

_VALID_STATUS: frozenset[str] = frozenset(
    {
        "CERTIFIED_NEUTRAL",
        "STABLE",
        "MODERATE_BIAS",
        "HIGH_BIAS",
        "CRITICAL_BIAS",
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
        status: AIStatusType = status_raw  # type: ignore[assignment]
    else:
        status = "STABLE"

    ain_status = data.get("ain_status")
    ain_status_s = ain_status if isinstance(ain_status, str) else None

    cm = data.get("compute_ms")
    compute_ms = float(cm) if isinstance(cm, (int, float)) and not isinstance(cm, bool) else None

    return ComputeResult(
        ain=_num(data, "ain", default=0.0),
        p_output=_num(data, "p_output", "pOutput", default=0.0),
        deviation=_num(data, "deviation", default=0.0),
        status=status,
        tokens_used=_int_num(data, "tokens_used", "tokensUsed", default=0),
        tokens_remaining=_int_num(data, "tokens_remaining", "tokensRemaining", default=0),
        matrix_size=matrix_size,
        samples=samples,
        ain_status=ain_status_s,
        compute_ms=compute_ms,
    )
