"""Utility functions for ZPL Engine SDK."""

import random
from typing import Optional

from zeropointlogic.models import AIStatusType


def matrix_from_prices(prices: list[float], window: int = 10) -> list[list[int]]:
    """Convert a list of prices to a binary matrix.

    Creates a binary matrix by comparing each price to its moving average.
    1 if price >= moving average, 0 otherwise.

    Args:
        prices: List of price values
        window: Moving average window size (default 10)

    Returns:
        Binary matrix of shape (len(prices) - window, window)

    Raises:
        ValueError: If prices is empty or window is too large
    """
    if not prices:
        raise ValueError("prices cannot be empty")
    if window > len(prices):
        raise ValueError(f"window ({window}) cannot be larger than prices length ({len(prices)})")
    if window < 2:
        raise ValueError("window must be at least 2")

    matrix = []
    for i in range(len(prices) - window):
        window_prices = prices[i : i + window]
        moving_avg = sum(window_prices) / len(window_prices)
        row = [1 if p >= moving_avg else 0 for p in window_prices]
        matrix.append(row)

    return matrix


def matrix_from_timeseries(
    values: list[float], bins: int = 10, method: str = "quantile"
) -> list[list[int]]:
    """Convert a time series to a binary matrix using binning.

    Args:
        values: List of values
        bins: Number of bins to create (default 10)
        method: Binning method - 'quantile' (equal frequency) or 'equal' (equal width)

    Returns:
        Binary matrix of shape (len(values) - bins, bins)

    Raises:
        ValueError: If values is empty, bins invalid, or method unknown
    """
    if not values:
        raise ValueError("values cannot be empty")
    if bins < 2:
        raise ValueError("bins must be at least 2")
    if len(values) < bins:
        raise ValueError(f"values length ({len(values)}) must be >= bins ({bins})")
    if method not in ("quantile", "equal"):
        raise ValueError(f"method must be 'quantile' or 'equal', got {method}")

    # Calculate bin edges
    if method == "quantile":
        sorted_vals = sorted(values)
        bin_size = len(sorted_vals) / bins
        edges = [sorted_vals[min(int(i * bin_size), len(sorted_vals) - 1)] for i in range(bins + 1)]
    else:  # equal width
        min_val, max_val = min(values), max(values)
        step = (max_val - min_val) / bins if max_val > min_val else 1
        edges = [min_val + i * step for i in range(bins + 1)]

    # Assign each value to bin
    matrix = []
    for i in range(len(values) - bins):
        window_vals = values[i : i + bins]
        row = []
        for val in window_vals:
            bin_idx = 0
            for j in range(len(edges) - 1):
                if edges[j] <= val <= edges[j + 1]:
                    bin_idx = j
                    break
            row.append(1 if bin_idx >= bins // 2 else 0)
        matrix.append(row)

    return matrix


def matrix_from_dataframe(df, col1: str, col2: str, normalize: bool = True) -> list[list[int]]:
    """Convert two columns from a pandas DataFrame to a binary matrix.

    Compares values in col1 and col2, creating a binary matrix where
    1 indicates col1 >= col2, 0 otherwise.

    Args:
        df: pandas DataFrame
        col1: Name of first column
        col2: Name of second column
        normalize: Whether to normalize values first (default True)

    Returns:
        Binary matrix of shape (len(df), 2)

    Raises:
        ValueError: If columns don't exist or DataFrame is empty
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for matrix_from_dataframe()")

    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a pandas DataFrame")
    if df.empty:
        raise ValueError("DataFrame cannot be empty")
    if col1 not in df.columns:
        raise ValueError(f"Column '{col1}' not found in DataFrame")
    if col2 not in df.columns:
        raise ValueError(f"Column '{col2}' not found in DataFrame")

    vals1 = df[col1].values.astype(float)
    vals2 = df[col2].values.astype(float)

    if normalize:
        min1, max1 = vals1.min(), vals1.max()
        min2, max2 = vals2.min(), vals2.max()
        if max1 > min1:
            vals1 = (vals1 - min1) / (max1 - min1)
        if max2 > min2:
            vals2 = (vals2 - min2) / (max2 - min2)

    matrix = [[1 if v1 >= v2 else 0 for v1, v2 in zip(vals1, vals2)]]
    return matrix


def normalize_matrix(matrix: list[list[int]]) -> list[list[int]]:
    """Ensure all values in matrix are 0 or 1.

    Args:
        matrix: Input matrix (can contain any numeric values)

    Returns:
        Normalized binary matrix

    Raises:
        ValueError: If matrix is empty or contains non-numeric values
    """
    if not matrix:
        raise ValueError("matrix cannot be empty")
    if not all(matrix):
        raise ValueError("matrix rows cannot be empty")

    normalized = []
    for row in matrix:
        normalized_row = [1 if val else 0 for val in row]
        normalized.append(normalized_row)

    return normalized


def create_random_matrix(size: int, density: float = 0.5) -> list[list[int]]:
    """Create a random binary matrix.

    Args:
        size: Matrix dimensions (size × size)
        density: Proportion of 1s in matrix (0.0-1.0, default 0.5)

    Returns:
        Random binary matrix of shape (size, size)

    Raises:
        ValueError: If size < 1 or density not in [0, 1]
    """
    if size < 1:
        raise ValueError("size must be at least 1")
    if not (0 <= density <= 1):
        raise ValueError("density must be between 0 and 1")

    matrix = [[1 if random.random() < density else 0 for _ in range(size)] for _ in range(size)]
    return matrix


def interpret_ain(ain: float, verbosity: str = "short") -> str:
    """Get human-readable interpretation of AIN score.

    Args:
        ain: AI Neutrality Index value (0-1)
        verbosity: 'short' for one word, 'medium' for phrase, 'long' for explanation

    Returns:
        Human-readable interpretation

    Raises:
        ValueError: If ain not in [0, 1]
    """
    if not (0 <= ain <= 1):
        raise ValueError(f"ain must be between 0 and 1, got {ain}")

    if verbosity not in ("short", "medium", "long"):
        raise ValueError(f"verbosity must be 'short', 'medium', or 'long', got {verbosity}")

    if ain >= 0.85:
        short = "Perfect"
        medium = "Perfectly Neutral"
        long = "Excellent neutrality with minimal bias detected. Data distribution is ideal."
    elif ain >= 0.70:
        short = "Excellent"
        medium = "Highly Neutral"
        long = "Strong neutrality with very low bias. Suitable for most applications."
    elif ain >= 0.55:
        short = "Good"
        medium = "Moderately Neutral"
        long = "Acceptable neutrality with minor bias patterns. Consider mitigation strategies."
    elif ain >= 0.40:
        short = "Fair"
        medium = "Slightly Biased"
        long = "Noticeable bias detected. Mitigation measures are recommended."
    elif ain >= 0.25:
        short = "Poor"
        medium = "Moderately Biased"
        long = "Significant bias patterns. Immediate mitigation needed."
    else:
        short = "Critical"
        medium = "Heavily Biased"
        long = "Critical bias levels detected. Immediate intervention required."

    if verbosity == "short":
        return short
    elif verbosity == "medium":
        return medium
    else:
        return long


def get_status_color(status: AIStatusType) -> str:
    """Get recommended color for status display.

    Args:
        status: AI status type

    Returns:
        Color code (green, yellow, orange, red)
    """
    color_map = {
        "CERTIFIED_NEUTRAL": "green",
        "STABLE": "green",
        "MODERATE_BIAS": "yellow",
        "HIGH_BIAS": "orange",
        "CRITICAL_BIAS": "red",
    }
    return color_map.get(status, "gray")


def validate_matrix(matrix: list[list[int]]) -> tuple[bool, str]:
    """Validate that a matrix is properly formatted.

    Engine constraints (verified against engine 3.1.0):
      - shape must be square N x N
      - 3 <= N <= 100  (engine returns HTTP 400 "D must be between 3 and 100"
        when violated; we fail fast client-side so the user sees a clear
        ZPLValidationError instead of a confusing API error)
      - every cell must be 0 or 1 (binary)

    Args:
        matrix: Matrix to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not matrix:
        return False, "Matrix cannot be empty"

    if not isinstance(matrix, list):
        return False, "Matrix must be a list"

    n = len(matrix)
    if n < 3:
        return False, (
            f"Matrix must be at least 3x3 (got {n}x{n}). The engine requires "
            "dimension >= 3."
        )
    if n > 100:
        return False, (
            f"Matrix must be at most 100x100 (got {n}x{n}). The engine "
            "rejects dimension > 100; upgrade plan if you need higher d."
        )

    row_lengths = set(len(row) for row in matrix)
    if len(row_lengths) > 1:
        return False, f"All rows must have same length, got {row_lengths}"

    # Square check — must equal N
    (only_len,) = row_lengths
    if only_len != n:
        return False, (
            f"Matrix must be square: {n} rows but rows have {only_len} columns"
        )

    for i, row in enumerate(matrix):
        if not isinstance(row, list):
            return False, f"Row {i} is not a list"
        for j, val in enumerate(row):
            if val not in (0, 1):
                return False, f"Row {i}, Col {j} is {val}, must be 0 or 1"

    return True, ""


def chunk_matrices(matrices: list[list[list[int]]], chunk_size: int = 10) -> list[list[list[list[int]]]]:
    """Split a list of matrices into chunks for batch processing.

    Args:
        matrices: List of matrices
        chunk_size: Size of each chunk (default 10)

    Returns:
        List of chunks, where each chunk is a list of matrices

    Raises:
        ValueError: If chunk_size < 1
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")

    chunks = []
    for i in range(0, len(matrices), chunk_size):
        chunks.append(matrices[i : i + chunk_size])

    return chunks
