"""ZPL Engine SDK - Professional Python client for Zero Point Logic API."""

from zeropointlogic.version import __version__

__author__ = "Alex Cicic"
__license__ = "MIT"

from zeropointlogic.client import ZPLClient, AsyncZPLClient, ZPL_SDK_CLIENT_TYPE
from zeropointlogic.models import (
    ComputeResult,
    UsageInfo,
    PlanInfo,
    HealthStatus,
    AIStatusType,
)
from zeropointlogic.exceptions import (
    ZPLError,
    ZPLAuthError,
    ZPLRateLimitError,
    ZPLQuotaError,
    ZPLValidationError,
    ZPLNetworkError,
)
from zeropointlogic.utils import (
    matrix_from_prices,
    matrix_from_dataframe,
    matrix_from_timeseries,
    normalize_matrix,
    interpret_ain,
    create_random_matrix,
)

__all__ = [
    "__version__",
    "ZPL_SDK_CLIENT_TYPE",
    "ZPLClient",
    "AsyncZPLClient",
    "ComputeResult",
    "UsageInfo",
    "PlanInfo",
    "HealthStatus",
    "AIStatusType",
    "ZPLError",
    "ZPLAuthError",
    "ZPLRateLimitError",
    "ZPLQuotaError",
    "ZPLValidationError",
    "ZPLNetworkError",
    "matrix_from_prices",
    "matrix_from_dataframe",
    "matrix_from_timeseries",
    "normalize_matrix",
    "interpret_ain",
    "create_random_matrix",
]
