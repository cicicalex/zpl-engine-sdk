"""Example: Analyze cryptocurrency market bias using ZPL Engine.

This example demonstrates how to use the ZPL SDK to analyze potential bias
in cryptocurrency price distributions. It fetches historical price data and
analyzes it with the AI Neutrality Index.
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zeropointlogic import ZPLClient, matrix_from_prices, interpret_ain


def analyze_crypto_prices(symbol: str = "BTC", days: int = 30) -> None:
    """Analyze cryptocurrency price bias.

    Args:
        symbol: Cryptocurrency symbol (BTC, ETH, XRP, etc.)
        days: Historical days to analyze
    """
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    print(f"\n{symbol} Market Bias Analysis")
    print("=" * 50)

    # Simulate historical price data
    # In production, you'd fetch from CoinGecko, Binance, etc.
    prices = generate_sample_prices(base=100, days=days)

    print(f"Analyzing {len(prices)} daily prices over {days} days")
    print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")

    # Convert prices to binary matrix using moving average
    matrix = matrix_from_prices(prices, window=10)
    print(f"Matrix size: {len(matrix)} x {len(matrix[0])}")

    # Compute bias analysis
    result = client.compute(matrix=matrix, samples=1000)

    # Display results
    print(f"\nAnalysis Results:")
    print(f"  AIN Score: {result.ain:.3f}")
    print(f"  Status: {result.status}")
    print(f"  Interpretation: {interpret_ain(result.ain, 'medium')}")
    print(f"  Probability Output: {result.p_output:.3f}")
    print(f"  Deviation: {result.deviation:.3f}")

    # Neutral threshold check
    if result.is_neutral(threshold=0.7):
        print(f"\n✓ Market shows NEUTRAL characteristics")
        print(f"  Price distribution is well-balanced")
    else:
        print(f"\n⚠ Market shows BIAS characteristics")
        print(f"  Price distribution may be skewed")

    # Usage info
    usage = client.get_usage()
    print(f"\nAPI Usage:")
    print(f"  Plan: {usage.plan}")
    print(f"  Tokens used: {usage.tokens_used} / {usage.tokens_limit}")
    print(f"  Tokens remaining: {usage.tokens_remaining}")
    print(f"  Usage: {usage.usage_percent:.1f}%")


def generate_sample_prices(base: float = 100, days: int = 30, volatility: float = 0.02) -> list[float]:
    """Generate sample cryptocurrency prices with random walk.

    Args:
        base: Base price
        days: Number of days
        volatility: Daily volatility (0.02 = 2%)

    Returns:
        List of prices
    """
    import random

    prices = [base]
    for _ in range(days - 1):
        change = random.gauss(0, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # Ensure positive prices

    return prices


def batch_analyze_cryptocurrencies() -> None:
    """Analyze multiple cryptocurrencies at once."""
    api_key = os.getenv("ZPL_API_KEY", "zpl_demo_key")
    client = ZPLClient(api_key=api_key)

    symbols = ["BTC", "ETH", "XRP", "ADA"]
    results = {}

    print("\nBatch Analysis: Multiple Cryptocurrencies")
    print("=" * 50)

    for symbol in symbols:
        prices = generate_sample_prices(base=100, days=30)
        matrix = matrix_from_prices(prices, window=10)

        result = client.compute(matrix=matrix, samples=500)
        results[symbol] = result

        print(f"{symbol:5} | AIN: {result.ain:.3f} | Status: {result.status:20} | {interpret_ain(result.ain, 'short')}")

    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    neutral_count = sum(1 for r in results.values() if r.is_neutral())
    print(f"  Neutral markets: {neutral_count}/{len(symbols)}")
    print(f"  Average AIN: {sum(r.ain for r in results.values()) / len(results):.3f}")

    # Tokens remaining
    usage = client.get_usage()
    print(f"  Tokens remaining: {usage.tokens_remaining}")


if __name__ == "__main__":
    # Single symbol analysis
    analyze_crypto_prices(symbol="BTC", days=30)

    # Multiple symbols batch analysis
    batch_analyze_cryptocurrencies()
