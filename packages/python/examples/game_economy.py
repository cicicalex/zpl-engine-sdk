"""Example: Analyze game economy balance using ZPL Engine.

This example demonstrates how to use the ZPL SDK to analyze game item
distributions and economy balance. It helps identify if items are fairly
distributed or if there's bias toward certain tiers.
"""

import os
import sys
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zeropointlogic import ZPLClient, normalize_matrix, interpret_ain


def analyze_item_distribution(items: list[int], thresholds: tuple = (20, 50)) -> dict:
    """Analyze game item rarity distribution.

    Args:
        items: List of item rarity values (1-100)
        thresholds: Tuple of (common_threshold, rare_threshold)

    Returns:
        Analysis results dictionary
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print("\nGame Economy Analysis: Item Distribution")
    print("=" * 50)

    common_threshold, rare_threshold = thresholds
    total_items = len(items)

    # Categorize items
    common = sum(1 for i in items if i < common_threshold)
    uncommon = sum(1 for i in items if common_threshold <= i < rare_threshold)
    rare = sum(1 for i in items if i >= rare_threshold)

    print(f"Total items: {total_items}")
    print(f"  Common (< {common_threshold}): {common} ({100*common/total_items:.1f}%)")
    print(f"  Uncommon ({common_threshold}-{rare_threshold}): {uncommon} ({100*uncommon/total_items:.1f}%)")
    print(f"  Rare (> {rare_threshold}): {rare} ({100*rare/total_items:.1f}%)")

    # Create binary matrix comparing items to median
    median = sorted(items)[len(items) // 2]
    matrix = []
    for i in range(0, len(items) - 10, 10):
        row = [1 if item >= median else 0 for item in items[i : i + 10]]
        if len(row) == 10:
            matrix.append(row)

    if not matrix:
        print("\nWarning: Not enough items for analysis (need 10+ items)")
        return {}

    # Compute balance index
    result = client.compute(matrix=matrix, samples=500)

    print(f"\nBalance Analysis:")
    print(f"  AIN Score: {result.ain:.3f}")
    print(f"  Status: {result.status}")
    print(f"  Assessment: {interpret_ain(result.ain, 'medium')}")

    if result.is_neutral(threshold=0.65):
        print(f"\n✓ BALANCED ECONOMY")
        print(f"  Item distribution is fair and well-balanced")
    else:
        print(f"\n⚠ UNBALANCED ECONOMY")
        print(f"  Consider rebalancing rare/common item rates")

    return {
        "total_items": total_items,
        "common_percent": 100 * common / total_items,
        "uncommon_percent": 100 * uncommon / total_items,
        "rare_percent": 100 * rare / total_items,
        "ain_score": result.ain,
        "is_balanced": result.is_neutral(threshold=0.65),
    }


def analyze_drop_rates(drops_per_session: list[int], session_count: int = 100) -> None:
    """Analyze drop rate consistency across sessions.

    Args:
        drops_per_session: List of drop counts per session
        session_count: Number of sessions
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print("\nGame Economy Analysis: Drop Rate Consistency")
    print("=" * 50)

    average_drops = sum(drops_per_session) / len(drops_per_session)
    print(f"Sessions analyzed: {len(drops_per_session)}")
    print(f"Average drops per session: {average_drops:.2f}")
    print(f"Min: {min(drops_per_session)}, Max: {max(drops_per_session)}")

    # Create binary matrix: compare each session to average
    matrix = []
    for i in range(0, len(drops_per_session) - 5, 5):
        window = drops_per_session[i : i + 5]
        row = [1 if drops >= average_drops else 0 for drops in window]
        if len(row) == 5:
            matrix.append(row)

    if not matrix:
        print("Not enough data for analysis")
        return

    # Compute consistency
    result = client.compute(matrix=matrix, samples=500)

    print(f"\nConsistency Analysis:")
    print(f"  AIN Score: {result.ain:.3f}")
    print(f"  Status: {result.status}")

    if result.is_neutral(threshold=0.7):
        print(f"\n✓ CONSISTENT DROPS")
        print(f"  Drop rates are stable and predictable")
    else:
        print(f"\n⚠ INCONSISTENT DROPS")
        print(f"  Drop rates fluctuate significantly")


def compare_patch_balance(before_items: list[int], after_items: list[int]) -> None:
    """Compare game balance before and after a patch.

    Args:
        before_items: Item values before patch
        after_items: Item values after patch
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print("\nPatch Impact Analysis: Balance Comparison")
    print("=" * 50)

    # Analyze both distributions
    def create_analysis_matrix(items: list[int]) -> list[list[int]]:
        median = sorted(items)[len(items) // 2]
        matrix = []
        for i in range(0, len(items) - 10, 10):
            row = [1 if item >= median else 0 for item in items[i : i + 10]]
            if len(row) == 10:
                matrix.append(row)
        return matrix

    before_matrix = create_analysis_matrix(before_items)
    after_matrix = create_analysis_matrix(after_items)

    if not before_matrix or not after_matrix:
        print("Not enough data for comparison")
        return

    # Get results for both
    before_result = client.compute(matrix=before_matrix, samples=500)
    after_result = client.compute(matrix=after_matrix, samples=500)

    print(f"Before Patch:")
    print(f"  AIN Score: {before_result.ain:.3f}")
    print(f"  Status: {before_result.status}")

    print(f"\nAfter Patch:")
    print(f"  AIN Score: {after_result.ain:.3f}")
    print(f"  Status: {after_result.status}")

    # Impact assessment
    ain_change = after_result.ain - before_result.ain
    print(f"\nPatch Impact:")
    print(f"  AIN Change: {ain_change:+.3f}")

    if ain_change > 0.05:
        print(f"  ✓ IMPROVED balance (more neutral)")
    elif ain_change < -0.05:
        print(f"  ⚠ DEGRADED balance (more biased)")
    else:
        print(f"  ~ NEUTRAL impact (minimal change)")


if __name__ == "__main__":
    # Example 1: Analyze item rarity distribution
    print("EXAMPLE 1: Item Rarity Distribution")
    sample_items = [
        5, 15, 8, 45, 52, 12, 88, 95, 72, 35,
        28, 42, 18, 65, 38, 22, 78, 91, 30, 55,
        10, 60, 75, 48, 25, 82, 15, 50, 65, 40,
    ]
    analyze_item_distribution(sample_items)

    # Example 2: Analyze drop rate consistency
    print("\n" + "=" * 50)
    print("\nEXAMPLE 2: Drop Rate Consistency")
    sample_drops = [3, 4, 2, 5, 3, 4, 2, 3, 5, 4] * 5  # 50 sessions
    analyze_drop_rates(sample_drops)

    # Example 3: Compare before/after patch
    print("\n" + "=" * 50)
    print("\nEXAMPLE 3: Patch Balance Impact")
    before = [10, 20, 15, 25, 30, 18, 22, 28, 35, 12, 40, 38]
    after = [15, 22, 18, 24, 28, 20, 23, 26, 32, 16, 38, 36]
    compare_patch_balance(before, after)
