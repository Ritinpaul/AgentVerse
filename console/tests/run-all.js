/**
 * Master Test Runner for AgentVerse Web Console
 * Executes all 20 domain-specific test suites in tests/
 */

const { getGlobalResults } = require("./test-utils");

const suites = [
  { name: "Foundation & Layout", runner: require("./foundation-layout.test") },
  { name: "Agent Fleet Catalog & Detail", runner: require("./agent-catalog-fleet.test") },
  { name: "AgentStudio Monaco IDE & Schema", runner: require("./agent-studio-ide.test") },
  { name: "Visual Composition Canvas", runner: require("./visual-composition-canvas.test") },
  { name: "Observability & Causal Tracing", runner: require("./observability-traces.test") },
  { name: "GovernOS Visual Policy Editor", runner: require("./govern-policies.test") },
  { name: "GovernOS Immutable Audit Ledger", runner: require("./govern-audit-ledger.test") },
  { name: "GovernOS HITL Approvals Queue", runner: require("./govern-approvals.test") },
  { name: "GovernOS QI Semantic Cache", runner: require("./govern-qi-cache.test") },
  { name: "GovernOS ASI Red-Team Scanner", runner: require("./govern-vulnerability-scanner.test") },
  { name: "GovernOS Compliance Badges", runner: require("./govern-compliance-frameworks.test") },
  { name: "GovernOS Gateways & MicroVM Proxy", runner: require("./govern-gateways.test") },
  { name: "AgentStore Marketplace & Details", runner: require("./store-marketplace-catalog.test") },
  { name: "AgentStore 4-Step Publish Wizard", runner: require("./store-publish-wizard.test") },
  { name: "AgentStore Purchases & Creator Revenue", runner: require("./store-purchases-revenue.test") },
  { name: "AgentStore A2A Escrow & Compositions", runner: require("./store-a2a-compositions.test") },
  { name: "Global Command Palette (Cmd+K) & Shortcuts", runner: require("./command-palette-shortcuts.test") },
  { name: "Organization Settings & Foundation Model Keys", runner: require("./settings-keys-admin.test") },
  { name: "Technical Architecture & Kernel Documentation", runner: require("./documentation-architecture.test") },
  { name: "Production Error Resilience & Boundaries", runner: require("./production-resilience-error.test") },
];

console.log("\n==============================================================");
console.log("🚀 AGENTVERSE WEB CONSOLE — MASTER TEST RUNNER");
console.log("==============================================================");

for (const suite of suites) {
  suite.runner.run();
}

const results = getGlobalResults();

console.log("\n==============================================================");
console.log(`🏁 ALL SUITES COMPLETE: ${results.totalPassed}/${results.total} TESTS PASSED`);
console.log("==============================================================");

if (results.failures.length > 0) {
  console.error("\n❌ Failed Tests:");
  results.failures.forEach((f) => console.error(`  • ${f}`));
  process.exit(1);
} else {
  console.log("\n🎉 ALL TESTS PASSED ACROSS 20 DOMAIN MODULES!\n");
  process.exit(0);
}
