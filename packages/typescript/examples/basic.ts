/**
 * Basic example: Simple compute operation
 * Shows how to initialize client and run a single AIN calculation
 */

import { ZPLClient, createRandomMatrix, interpretAIN } from '../src/index.js';

async function main() {
  // Initialize client with API key
  const client = new ZPLClient({
    apiKey: process.env.ZPL_API_KEY || 'zpl_demo_key',
    debug: true,
  });

  try {
    // Create a random binary matrix for testing
    const matrix = createRandomMatrix(16);

    console.log('Computing AIN for 16x16 random matrix...\n');

    // Run compute
    const result = await client.compute({
      matrix,
      samples: 1000,
    });

    // Display results
    console.log('Result:');
    console.log(`  AIN Score: ${result.ain.toFixed(4)}`);
    console.log(`  Status: ${result.status}`);
    console.log(`  Bias Level: ${result.biasLevel}`);
    console.log(`  P-Output: ${result.pOutput.toFixed(4)}`);
    console.log(`  Deviation: ${result.deviation.toFixed(4)}`);
    console.log(`  Tokens Used: ${result.tokensUsed}`);
    console.log(`  Tokens Remaining: ${result.tokensRemaining}\n`);

    // Interpret the result
    console.log('Interpretation:');
    console.log(`  ${interpretAIN(result.ain)}`);
    console.log(`  Is Neutral: ${result.isNeutral ? 'Yes' : 'No'}`);

    // Get usage information
    console.log('\nCurrent Usage:');
    const usage = await client.getUsage();
    console.log(`  Plan: ${usage.plan}`);
    console.log(`  Tokens Remaining (Today): ${usage.tokensRemainingToday}`);
    console.log(`  Tokens Remaining (Month): ${usage.tokensRemainingMonth}`);
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
