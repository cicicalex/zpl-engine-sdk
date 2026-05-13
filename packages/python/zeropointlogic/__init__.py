"""ZPL Engine SDK - Professional Python client for Zero Point Logic API."""

from zeropointlogic.version import __version__

__author__ = "Alex Cicic"
__license__ = "MIT"

from zeropointlogic.client import ZPLClient, AsyncZPLClient, ZPL_SDK_CLIENT_TYPE

# AUDIT 2026-05-13 (BUG D1): the README quickstart + every example in
# the docs uses `from zeropointlogic import Client`, but pre-fix only
# `ZPLClient` was exported. That made the very first line of every
# tutorial throw `ImportError: cannot import name 'Client'`. Aliasing
# Client to ZPLClient (and AsyncClient to AsyncZPLClient) so both
# spellings work without breaking existing code.
Client = ZPLClient
AsyncClient = AsyncZPLClient
from zeropointlogic.models import (
    ComputeResult,
    UsageInfo,
    PlanInfo,
    HealthStatus,
    AIStatusType,
    BiasLevel,
    ain_to_bias_level,
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
    "Client",
    "AsyncClient",
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
