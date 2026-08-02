"""A rejection must describe the matrix the caller actually sent.

AUDIT 2026-08-02. Both row-count branches of ``validate_matrix`` printed the row
count twice -- ``{n}x{n}`` -- so for anything not already square the second
number was invented. Measured by running the function:

    2 rows x 5 columns   -> "got 2x2"
    1 row  x 4 columns   -> "got 1x1"
    150 rows x 7 columns -> "got 150x150"

The engine had the same defect and was fixed the same day, and so did the
TypeScript package. It matters more in a client than in the engine: this runs
BEFORE anything is sent, so the engine's corrected message never reaches the
caller. What a customer reads is what this returns. Someone who sent seven
columns and is told they sent 150 goes looking for a bug that is not there.

The squareness branch never had the problem -- it names both numbers it saw --
and is pinned so a change to its siblings does not take it along.

Behavioural rather than a source scan: what matters is the string a customer
reads, and asserting on it cannot drift from the template the way a pattern
match over the source can.
"""

import pytest

from zeropointlogic.utils import validate_matrix


def grid(rows: int, cols: int) -> list[list[int]]:
    """`rows` x `cols`, alternating bits. Not square unless the two match."""
    return [[(i + j) % 2 for j in range(cols)] for i in range(rows)]


def reject(rows: int, cols: int) -> str:
    ok, message = validate_matrix(grid(rows, cols))
    assert not ok, f"{rows}x{cols} was accepted; this test needs an input that is refused"
    return message


@pytest.mark.parametrize("rows,cols", [(2, 3), (2, 5), (1, 4)])
def test_a_matrix_below_the_minimum_is_told_its_real_width(rows, cols):
    message = reject(rows, cols)
    assert str(cols) in message, (
        f"the refusal for a {rows}x{cols} matrix never mentions its {cols} columns: {message}"
    )
    # The shape that was there: the row count printed as both dimensions.
    fabricated = f"{rows}x{rows}"
    assert fabricated not in message, (
        f"the refusal reports '{fabricated}' for a matrix that is {rows}x{cols}. The second "
        f"number is the row count printed twice, not anything the caller sent: {message}"
    )


@pytest.mark.parametrize("rows,cols", [(101, 3), (150, 7)])
def test_an_oversized_matrix_is_told_its_real_width_too(rows, cols):
    # The same template, the same defect, in the branch nobody exercised.
    message = reject(rows, cols)
    assert f"{cols} column" in message, (
        f"the refusal for a {rows}x{cols} matrix never mentions its {cols} columns: {message}"
    )
    fabricated = f"{rows}x{rows}"
    assert fabricated not in message, (
        f"the refusal reports '{fabricated}' for a matrix that is {rows}x{cols}: {message}"
    )


def test_the_squareness_refusal_still_names_both_numbers():
    # This branch was already correct. Pinned so a change to its siblings does
    # not take it with them.
    message = reject(5, 3)
    assert "5" in message and "3" in message, (
        f"the squareness refusal no longer names both the row count and the offending "
        f"width: {message}"
    )


def test_the_refusal_says_the_same_thing_the_engine_would():
    # Three surfaces answer this question -- the engine, this package, and the
    # TypeScript package -- and a customer who moves between them should not be
    # told two different stories about the same matrix. The engine's wording,
    # fixed the same day, is the one being matched.
    message = reject(2, 5)
    assert "got 2 row(s); row 0 has 5 column(s)" in message, (
        f"this package no longer phrases the refusal the way the engine does: {message}"
    )


@pytest.mark.parametrize("n", [3, 9, 100])
def test_a_valid_matrix_is_still_accepted(n):
    # A refusal that describes the input perfectly and refuses everything is not
    # an improvement.
    ok, message = validate_matrix(grid(n, n))
    assert ok, f"a valid {n}x{n} matrix was refused: {message}"


@pytest.mark.parametrize(
    "matrix",
    [
        [1, 2],
        ["nope", "nope", "nope"],
        [None, None, None],
    ],
)
def test_a_matrix_whose_first_row_is_not_a_list_is_refused_without_raising(matrix):
    # The width is read from row 0 before rows have been checked, so row 0 may be
    # anything at all. It must not take the validator down with it.
    ok, message = validate_matrix(matrix)
    assert not ok, f"a malformed matrix was accepted: {matrix!r}"
    assert message, "a malformed matrix was refused with no explanation"
