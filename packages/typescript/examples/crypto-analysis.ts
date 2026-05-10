/**
 * Crypto Market Analysis example
 * Demonstrates analyzing price volatility and market bias using real price data
 */

import { ZPLClient, pricesToMatrix, interpretStatus, interpretAIN } from '../src/index.js';

async function analyzeMarketBias() {
  const client = new ZPLClient({
    apiKey: process.env.ZPL_API_KEY || 'zpl_demo_key',
  });

  // Example BTC price data (last 30 days)
  const btcPrices = [
    45230, 45890, 44950, 46120, 47100, 46890, 47500, 48200, 47800, 49100, 50200, 49800, 51100,
    50500, 52300, 51900, 53200, 52800, 54500, 53200, 55100, 54300, 56200, 55800, 57500, 56900,
    58200, 57500, 59100, 58400,
  ];

  console.log('ZPL Crypto Market Bias Analysis');
  console.log('================================\n');

  try {
    // Convert price data to binary matrix
    console.log('Analyzing BTC price movements...');
    const matrix = pricesToMatrix(btcPrices, 15);

    // Run analysis with higher sample count for financial data
    const result = await client.compute({
      matrix,
      samples: 5000, // More samples for market data
    });

    console.log('\nAnalysis Results:');
    console.log(`  Price Window: ${btcPrices[0]} → ${btcPrices[btcPrices.length - 1]}`);
    console.log(`  Matrix Size: ${matrix.length}x${matrix[0].length}`);
    console.log(`  AIN Score: ${result.ain.toFixed(4)}`);
    console.log(`  Status: ${result.status}`);
    console.log(`  Bias Level: ${result.biasLevel.toUpperCase()}\n`);

    // Interpret the market conditions
    console.log('Market Interpretation:');
    console.log(`  ${interpretStatus(result.status)}`);
    console.log(`  ${interpretAIN(result.ain)}\n`);

    // Provide recommendations
    if (result.ain >= 0.7) {
      console.log('Recommendation:');
      console.log('  Market shows balanced behavior. Suitable for automated trading strategies.');
    } else if (result.ain >= 0.5) {
      console.log('Recommendation:');
      console.log(
        '  Market shows some directional bias. Use risk management and consider smaller positions.'
      );
    } else {
      console.log('Recommendation:');
      console.log('  Market shows strong bias. Exercise caution. Consider manual review before trading.');
    }

    console.log(`\nTokens Used: ${result.tokensUsed}`);
    console.log(`Tokens Remaining: ${result.tokensRemaining}`);
  } catch (error) {
    console.error('Analysis failed:', error);
    process.exit(1);
  }
}

analyzeMarketBias();
