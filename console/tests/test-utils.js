/**
 * Test Utilities for AgentVerse Console Test Suite
 */

let totalPassed = 0;
let totalFailed = 0;
const failures = [];

function createSuite(suiteName) {
  let suitePassed = 0;
  let suiteFailed = 0;

  console.log(`\n┌─────────────────────────────────────────────────────────┐`);
  console.log(`│ 🧪 ${suiteName.padEnd(52)} │`);
  console.log(`└─────────────────────────────────────────────────────────┘`);

  function assert(condition, label, detail = "") {
    if (condition) {
      console.log(`  ✅  ${label}`);
      suitePassed++;
      totalPassed++;
    } else {
      console.error(`  ❌  ${label}${detail ? `\n       → ${detail}` : ""}`);
      suiteFailed++;
      totalFailed++;
      failures.push(`[${suiteName}] ${label}`);
    }
  }

  function report() {
    const sum = suitePassed + suiteFailed;
    console.log(`  📊 ${suitePassed}/${sum} passed in ${suiteName}\n`);
    return { passed: suitePassed, failed: suiteFailed };
  }

  return { assert, report };
}

function getGlobalResults() {
  return {
    totalPassed,
    totalFailed,
    total: totalPassed + totalFailed,
    failures,
  };
}

module.exports = {
  createSuite,
  getGlobalResults,
};
