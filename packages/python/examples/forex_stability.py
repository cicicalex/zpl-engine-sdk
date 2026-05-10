"""Example: Analyze forex market stability using ZPL Engine.

This example demonstrates how to use the ZPL SDK to analyze currency pair
stability and detect potential market bias or manipulation patterns.
"""

import os
import sys
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zeropointlogic import ZPLClient, matrix_from_prices, interpret_ain


def analyze_currency_pair(pair: str = "EURUSD", days: int = 60) -> dict:
    """Analyze forex currency pair stability.

    Args:
        pair: Currency pair (e.g., EURUSD, GBPUSD, JPYUSD)
        days: Historical days to analyze

    Returns:
        Analysis results
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print(f"\n{pair} Stability Analysis")
    print("=" * 60)

    # Generate or fetch price data
    prices = generate_forex_prices(base=1.0850, days=days)

    print(f"Analyzing {len(prices)} daily quotes over {days} days")
    print(f"Price range: {min(prices):.4f} - {max(prices):.4f}")
    print(f"Range: {(max(prices) - min(prices))*10000:.0f} pips")

    # Convert prices to binary matrix
    matrix = matrix_from_prices(prices, window=14)
    print(f"Matrix size: {len(matrix)} x {len(matrix[0])}")

    # Compute stability analysis
    result = client.compute(matrix=matrix, samples=1000)

    print(f"\nStability Results:")
    print(f"  AIN Score: {result.ain:.3f}")
    print(f"  Status: {result.status}")
    print(f"  Assessment: {interpret_ain(result.ain, 'long')}")
    print(f"  Probability Output: {result.p_output:.3f}")
    print(f"  Deviation: {result.deviation:.3f}")

    # Stability assessment
    volatility = (max(prices) - min(prices)) / prices[0]
    print(f"\nVolatility Metrics:")
    print(f"  Historical volatility: {volatility*100:.2f}%")

    if result.is_stable():
        print(f"\n✓ STABLE PAIR")
        print(f"  Price movement is well-distributed")
        print(f"  Suitable for range-trading strategies")
    else:
        print(f"\n⚠ VOLATILE PAIR")
        print(f"  Price shows trending or biased behavior")
        print(f"  Consider trend-following strategies")

    # Detection of manipulation
    if result.has_bias() and result.status == "CRITICAL_BIAS":
        print(f"\n⛔ WARNING: Potential Market Anomaly")
        print(f"   Extreme bias detected. Possible manipulation or regime change.")

    return {
        "pair": pair,
        "ain_score": result.ain,
        "status": result.status,
        "volatility": volatility * 100,
        "is_stable": result.is_stable(),
        "days_analyzed": days,
    }


def compare_forex_pairs() -> None:
    """Compare stability across multiple currency pairs."""
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    pairs = [
        ("EURUSD", 1.0850),
        ("GBPUSD", 1.2650),
        ("USDJPY", 150.50),
        ("AUDUSD", 0.6850),
    ]

    print("\nMulti-Pair Stability Comparison")
    print("=" * 60)

    results = {}
    for pair_name, base_price in pairs:
        prices = generate_forex_prices(base=base_price, days=60)
        matrix = matrix_from_prices(prices, window=14)

        result = client.compute(matrix=matrix, samples=500)
        results[pair_name] = result

        status_char = "✓" if result.is_stable() else "⚠"
        print(
            f"{status_char} {pair_name:10} | AIN: {result.ain:.3f} | {result.status:20} | {interpret_ain(result.ain, 'short')}"
        )

    # Summary
    print("\n" + "=" * 60)
    stable_count = sum(1 for r in results.values() if r.is_stable())
    print(f"Summary:")
    print(f"  Stable pairs: {stable_count}/{len(pairs)}")
    print(f"  Average AIN: {sum(r.ain for r in results.values()) / len(results):.3f}")

    # Find best and worst
    best = max(results.items(), key=lambda x: x[1].ain)
    worst = min(results.items(), key=lambda x: x[1].ain)
    print(f"  Most stable: {best[0]} (AIN: {best[1].ain:.3f})")
    print(f"  Most volatile: {worst[0]} (AIN: {worst[1].ain:.3f})")


def detect_market_regimes(prices: list[float], window_days: int = 20) -> None:
    """Detect market regime changes (trending vs ranging).

    Args:
        prices: List of prices
        window_days: Rolling window size
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print("\nMarket Regime Detection")
    print("=" * 60)

    regimes = []
    for i in range(0, len(prices) - window_days, window_days):
        window_prices = prices[i : i + window_days]
        matrix = matrix_from_prices(window_prices, window=5)

        if not matrix:
            continue

        result = client.compute(matrix=matrix, samples=300)
        regime = "RANGING" if result.is_neutral(threshold=0.65) else "TRENDING"

        regimes.append((i, regime, result.ain))
        print(f"Period {i:3d}-{i+window_days:3d}: {regime:10} (AIN: {result.ain:.3f})")

    print(f"\nRegime Analysis:")
    ranging_count = sum(1 for _, regime, _ in regimes if regime == "RANGING")
    trending_count = len(regimes) - ranging_count
    print(f"  Ranging periods: {ranging_count}/{len(regimes)}")
    print(f"  Trending periods: {trending_count}/{len(regimes)}")


def generate_forex_prices(base: float = 1.0850, days: int = 60, volatility: float = 0.0005) -> list[float]:
    """Generate synthetic forex price data with realistic characteristics.

    Args:
        base: Base exchange rate
        days: Number of days
        volatility: Daily volatility (0.0005 = 0.05%)

    Returns:
        List of prices
    """
    prices = [base]
    for _ in range(days - 1):
        change = random.gauss(0, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.0001))  # Ensure positive

    return prices


if __name__ == "__main__":
    # Example 1: Single pair analysis
    print("EXAMPLE 1: Single Currency Pair Analysis")
    analyze_currency_pair(pair="EURUSD", days=60)

    # Example 2: Multi-pair comparison
    print("\n" + "=" * 60)
    print("\nEXAMPLE 2: Multi-Pair Comparison")
    compare_forex_pairs()

    # Example 3: Market regime detection
    print("\n" + "=" * 60)
    print("\nEXAMPLE 3: Market Regime Detection")
    prices = generate_forex_prices(base=1.0850, days=100)
    detect_market_regimes(prices, window_days=20)
