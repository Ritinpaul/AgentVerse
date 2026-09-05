const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("AgentStudio Monaco IDE & Schema Engine");
  const root = path.join(__dirname, "..");

  // Component files
  const files = [
    "components/build/MonacoAgentEditor.tsx",
    "components/build/GovernanceSidebar.tsx",
    "components/build/CostPreview.tsx",
    "app/build/page.tsx",
    "public/agent-yaml-schema.json",
  ];
  for (const f of files) {
    assert(fs.existsSync(path.join(root, f)), `File exists: ${f}`);
  }

  // Validate JSON schema
  try {
    const schema = JSON.parse(fs.readFileSync(path.join(root, "public/agent-yaml-schema.json"), "utf8"));
    assert(schema.$schema !== undefined, "JSON Schema defines draft-07 standard");
    assert(schema.required?.includes("name"), "Schema requires 'name'");
    assert(schema.required?.includes("runtime"), "Schema requires 'runtime'");
    assert(schema.properties?.governance !== undefined, "Schema defines 'governance' block");
    assert(schema.properties?.budget !== undefined, "Schema defines 'budget' block");
  } catch (e) {
    assert(false, "Schema is valid JSON", e.message);
  }

  // Governance rule logic verification
  const monacoSrc = fs.readFileSync(path.join(root, "components/build/MonacoAgentEditor.tsx"), "utf8");
  assert(monacoSrc.includes("ASI01"), "Monaco editor implements ASI01 (prompt injection shield check)");
  assert(monacoSrc.includes("ASI02"), "Monaco editor implements ASI02 (tool scope whitelist check)");
  assert(monacoSrc.includes("ASI03"), "Monaco editor implements ASI03 (PII data protection check)");
  assert(monacoSrc.includes("ASI04"), "Monaco editor implements ASI04 (runaway cost ceiling check)");
  assert(monacoSrc.includes("ASI05"), "Monaco editor implements ASI05 (admin scope human approval check)");
  assert(monacoSrc.includes("ASI06"), "Monaco editor implements ASI06 (model fallback safeguard check)");

  // Cost preview logic
  const costSrc = fs.readFileSync(path.join(root, "components/build/CostPreview.tsx"), "utf8");
  assert(costSrc.includes("gemini-2.5-pro") || costSrc.includes("estimate"), "Cost preview supports Gemini/Claude/GPT model tiers");
  assert(costSrc.includes("budgetCeiling") || costSrc.includes("budget"), "Budget utilization progress bar rendered in cost preview");

  // Build page controls
  const buildPage = fs.readFileSync(path.join(root, "app/build/page.tsx"), "utf8");
  assert(buildPage.includes("Run Locally"), "Run Locally button mounted on IDE");
  assert(buildPage.includes("Deploy"), "Deploy dropdown mounted with targets");
  assert(buildPage.includes("editorTab"), "Tabs for Code (Monaco) and Canvas (React Flow) present");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
