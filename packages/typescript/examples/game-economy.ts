/**
 * Game Economy Analysis example
 * Demonstrates analyzing in-game economy balance for fairness and stability
 */

import {
  ZPLClient,
  createRandomMatrix,
  interpretStatus,
  ZPLQuotaExceededError,
  ZPLRateLimitError,
} from '../src/index.js';

async function analyzeGameEconomy() {
  const client = new ZPLClient({
    apiKey: process.env.ZPL_API_KEY || 'zpl_demo_key',
    retries: 3,
    debug: process.env.DEBUG === 'true',
  });

  console.log('ZPL Game Economy Balance Analysis');
  console.log('==================================\n');

  const gameMatrices = {
    'Item Drop Distribution': createRandomMatrix(20),
    'Player Wealth Curve': createRandomMatrix(25),
    'PvP Win Rate Matrix': createRandomMatrix(16),
    'Quest Reward Table': createRandomMatrix(12),
    'NPC Economy Flow': createRandomMatrix(18),
  };

  const results = [];

  for (const [label, matrix] of Object.entries(gameMatrices)) {
    try {
      console.log(`Analyzing: ${label}...`);

      const result = await client.compute({
        matrix,
        samples: 2000,
      });

      results.push({ label, ...result });

      console.log(`  AIN: ${result.ain.toFixed(4)} | Status: ${result.status} | Balance: ${result.biasLevel}\n`);
    } catch (error) {
      if (error instanceof ZPLQuotaExceededError) {
        console.error(`  ERROR: Quota exceeded. Tokens required: ${error.getTokensNeeded()}`);
        break;
      }

      if (error instanceof ZPLRateLimitError) {
        console.error(`  ERROR: Rate limited. Retry after ${error.getRetryDelayMs()}ms`);
        break;
      }

      console.error(`  ERROR: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Summary report
  console.log('\nEconomy Balance Summary:');
  console.log('------------------------');

  if (results.length > 0) {
    const avgAIN = results.reduce((sum, r) => sum + r.ain, 0) / results.length;
    const allNeutral = results.every((r) => r.isNeutral);

    console.log(`  Systems Analyzed: ${results.length}`);
    console.log(`  Average AIN: ${avgAIN.toFixed(4)}`);
    console.log(`  Overall Balance: ${allNeutral ? 'GOOD' : 'REVIEW NEEDED'}\n`);

    console.log('Detailed Breakdown:');
    results.forEach((r) => {
      const status = r.isNeutral ? '✓' : '⚠';
      console.log(`  ${status} ${r.label}`);
      console.log(`    AIN: ${r.ain.toFixed(4)} | ${r.status}`);
    });

    // Recommendations
    console.log('\nRecommendations:');
    const problematic = results.filter((r) => !r.isNeutral);

    if (problematic.length === 0) {
      console.log('  • Economy appears well-balanced across all systems');
      console.log('  • Consider regular re-analysis after game updates');
    } else {
      console.log(`  • ${problematic.length} system(s) need review:`);
      problematic.forEach((r) => {
        console.log(`    - ${r.label}: ${interpretStatus(r.status)}`);
      });
    }
  }

  console.log(`\nTotal Tokens Used: ${results.reduce((sum, r) => sum + r.tokensUsed, 0)}`);
}

analyzeGameEconomy();
