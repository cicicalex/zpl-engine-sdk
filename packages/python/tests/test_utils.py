"""Tests for ZPL SDK utility functions."""

import unittest
from zeropointlogic.utils import (
    matrix_from_prices,
    matrix_from_timeseries,
    normalize_matrix,
    interpret_ain,
    validate_matrix,
    create_random_matrix,
    get_status_color,
    chunk_matrices,
)
from zeropointlogic.exceptions import ZPLValidationError


class TestMatrixFromPrices(unittest.TestCase):
    """Test matrix_from_prices function."""

    def test_basic_conversion(self):
        """Test basic price to matrix conversion."""
        prices = [100, 110, 105, 115, 100, 120]
        matrix = matrix_from_prices(prices, window=3)
        assert len(matrix) == 3  # rows = len(prices) - window (see matrix_from_prices)
        assert all(len(row) == 3 for row in matrix)
        assert all(val in (0, 1) for row in matrix for val in row)

    def test_empty_prices(self):
        """Test with empty prices list."""
        with self.assertRaises(ValueError):
            matrix_from_prices([])

    def test_window_too_large(self):
        """Test with window larger than prices."""
        with self.assertRaises(ValueError):
            matrix_from_prices([100, 110], window=5)

    def test_invalid_window(self):
        """Test with invalid window size."""
        with self.assertRaises(ValueError):
            matrix_from_prices([100, 110, 120], window=1)


class TestMatrixFromTimeseries(unittest.TestCase):
    """Test matrix_from_timeseries function."""

    def test_quantile_binning(self):
        """Test quantile binning method."""
        values = list(range(100))
        matrix = matrix_from_timeseries(values, bins=5, method="quantile")
        assert len(matrix) == 95  # len(values) - bins
        assert all(len(row) == 5 for row in matrix)

    def test_equal_binning(self):
        """Test equal width binning method."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        matrix = matrix_from_timeseries(values, bins=2, method="equal")
        assert len(matrix) == 8  # len(values) - bins
        assert all(len(row) == 2 for row in matrix)

    def test_empty_values(self):
        """Test with empty values."""
        with self.assertRaises(ValueError):
            matrix_from_timeseries([])

    def test_invalid_method(self):
        """Test with invalid method."""
        with self.assertRaises(ValueError):
            matrix_from_timeseries([1, 2, 3], bins=2, method="invalid")


class TestNormalizeMatrix(unittest.TestCase):
    """Test normalize_matrix function."""

    def test_already_normalized(self):
        """Test matrix that's already normalized."""
        matrix = [[0, 1], [1, 0]]
        normalized = normalize_matrix(matrix)
        assert normalized == [[0, 1], [1, 0]]

    def test_non_normalized_values(self):
        """Test matrix with non-binary values."""
        matrix = [[0, 2], [3, 1]]
        normalized = normalize_matrix(matrix)
        assert normalized == [[0, 1], [1, 1]]

    def test_empty_matrix(self):
        """Test with empty matrix."""
        with self.assertRaises(ValueError):
            normalize_matrix([])


class TestValidateMatrix(unittest.TestCase):
    """Test validate_matrix function."""

    def test_valid_matrix(self):
        """Test validation of valid matrix (>=3x3 to satisfy engine constraint)."""
        is_valid, msg = validate_matrix([[0, 1, 0], [1, 0, 1], [0, 1, 1]])
        assert is_valid
        assert msg == ""

    def test_empty_matrix(self):
        """Test validation of empty matrix."""
        is_valid, msg = validate_matrix([])
        assert not is_valid

    def test_too_small_matrix(self):
        """Test that 2x2 matrices are rejected (engine requires D>=3)."""
        is_valid, msg = validate_matrix([[0, 1], [1, 0]])
        assert not is_valid
        assert "at least 3x3" in msg

    def test_too_large_matrix(self):
        """Test that >100x100 matrices are rejected (engine caps D at 100)."""
        big = [[0] * 101 for _ in range(101)]
        is_valid, msg = validate_matrix(big)
        assert not is_valid
        assert "at most 100x100" in msg

    def test_non_square_matrix(self):
        """Test that non-square matrices are rejected (engine requires square)."""
        # 3 rows but 4 columns
        is_valid, msg = validate_matrix([[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1]])
        assert not is_valid
        assert "square" in msg.lower()

    def test_inconsistent_rows(self):
        """Test validation of inconsistent row lengths."""
        is_valid, msg = validate_matrix([[0, 1, 0], [1, 0], [0, 1, 0]])
        assert not is_valid
        assert "same length" in msg.lower()

    def test_invalid_values(self):
        """Test validation with invalid values."""
        is_valid, msg = validate_matrix([[0, 2, 0], [1, 0, 1], [0, 1, 1]])
        assert not is_valid
        assert "must be 0 or 1" in msg


class TestInterpretAIN(unittest.TestCase):
    """Test interpret_ain function."""

    def test_perfect_neutrality(self):
        """Test interpretation of perfect neutrality."""
        assert interpret_ain(0.95, "short") == "Perfect"
        assert "neutral" in interpret_ain(0.95, "medium").lower()

    def test_high_bias(self):
        """Test interpretation of high bias."""
        assert interpret_ain(0.20, "short") == "Critical"
        assert "critical" in interpret_ain(0.20, "long").lower()

    def test_moderate_values(self):
        """Test interpretation of moderate values."""
        assert interpret_ain(0.50, "short") in ("Fair", "Good")
        assert interpret_ain(0.65, "short") == "Good"

    def test_invalid_ain(self):
        """Test with invalid AIN value."""
        with self.assertRaises(ValueError):
            interpret_ain(1.5)

    def test_invalid_verbosity(self):
        """Test with invalid verbosity."""
        with self.assertRaises(ValueError):
            interpret_ain(0.7, "invalid")


class TestCreateRandomMatrix(unittest.TestCase):
    """Test create_random_matrix function."""

    def test_basic_creation(self):
        """Test basic random matrix creation."""
        matrix = create_random_matrix(5)
        assert len(matrix) == 5
        assert all(len(row) == 5 for row in matrix)
        assert all(val in (0, 1) for row in matrix for val in row)

    def test_density(self):
        """Test matrix density."""
        matrix = create_random_matrix(10, density=0.0)
        assert all(row == [0] * 10 for row in matrix)

    def test_invalid_size(self):
        """Test with invalid size."""
        with self.assertRaises(ValueError):
            create_random_matrix(0)

    def test_invalid_density(self):
        """Test with invalid density."""
        with self.assertRaises(ValueError):
            create_random_matrix(5, density=1.5)


class TestGetStatusColor(unittest.TestCase):
    """Test get_status_color function."""

    def test_neutral_colors(self):
        """Test colors for neutral statuses."""
        assert get_status_color("CERTIFIED_NEUTRAL") == "green"
        assert get_status_color("STABLE") == "green"

    def test_bias_colors(self):
        """Test colors for biased statuses."""
        assert get_status_color("MODERATE_BIAS") == "yellow"
        assert get_status_color("HIGH_BIAS") == "orange"
        assert get_status_color("CRITICAL_BIAS") == "red"


class TestChunkMatrices(unittest.TestCase):
    """Test chunk_matrices function."""

    def test_basic_chunking(self):
        """Test basic matrix chunking."""
        matrices = [[[0, 1]] * i for i in range(5)]
        chunks = chunk_matrices(matrices, chunk_size=2)
        assert len(chunks) == 3  # 5 matrices / 2 size = 3 chunks
        assert len(chunks[0]) == 2
        assert len(chunks[-1]) == 1

    def test_chunk_size_one(self):
        """Test chunking with size 1."""
        matrices = [[[0, 1]]] * 3
        chunks = chunk_matrices(matrices, chunk_size=1)
        assert len(chunks) == 3

    def test_invalid_chunk_size(self):
        """Test with invalid chunk size."""
        with self.assertRaises(ValueError):
            chunk_matrices([[[0, 1]]], chunk_size=0)


if __name__ == "__main__":
    unittest.main()
