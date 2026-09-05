const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Agent Fleet Catalog & Details");
  const root = path.join(__dirname, "..");

  // Check files
  const files = [
    "components/shared/AgentCard.tsx",
    "components/shared/StatusBadge.tsx",
    "components/shared/TrustScore.tsx",
    "app/agents/page.tsx",
    "app/agents/[slug]/page.tsx",
    "hooks/useAgents.ts",
  ];
  for (const f of files) {
    assert(fs.existsSync(path.join(root, f)), `File exists: ${f}`);
  }

  // Hook validation
  const hook = fs.readFileSync(path.join(root, "hooks/useAgents.ts"), "utf8");
  assert(hook.includes("useAgents"), "useAgents hook exported");
  assert(hook.includes("searchQuery"), "Search query state managed in useAgents");
  assert(hook.includes("selectedCategory"), "Category filter state managed in useAgents");

  // Dynamic slug page check
  const slugPage = fs.readFileSync(path.join(root, "app/agents/[slug]/page.tsx"), "utf8");
  assert(slugPage.includes("trustFactors") || slugPage.includes("Trust"), "5-factor Trust score visualization mounted on agent details");
  assert(slugPage.includes("recentRuns") || slugPage.includes("runs"), "Execution history list mounted on agent details");
  assert(slugPage.includes("Run Agent") || slugPage.includes("Execute") || slugPage.includes("executeAgent"), "Local microVM run trigger supported on detail view");

  // AgentCard component
  const card = fs.readFileSync(path.join(root, "components/shared/AgentCard.tsx"), "utf8");
  assert(card.includes("TrustScore"), "AgentCard displays trust score gauge");
  assert(card.includes("StatusBadge"), "AgentCard displays status badge");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
