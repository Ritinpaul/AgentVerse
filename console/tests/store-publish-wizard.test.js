const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("AgentStore 4-Step Publish Wizard");
  const root = path.join(__dirname, "..");

  const publishFile = path.join(root, "app/store/publish/page.tsx");
  assert(fs.existsSync(publishFile), "app/store/publish/page.tsx exists");

  const publishSrc = fs.readFileSync(publishFile, "utf8");
  assert(publishSrc.includes("AgentStore Publisher Wizard"), "Publisher wizard title rendered");
  assert(publishSrc.includes("80%"), "80% builder revenue share displayed");
  assert(publishSrc.includes("Metadata") || publishSrc.includes("Step 1"), "Step 1 (Metadata) supported");
  assert(publishSrc.includes("agent.yaml") || publishSrc.includes("Manifest"), "Step 2 (Manifest YAML) supported");
  assert(publishSrc.includes("Pricing") || publishSrc.includes("pricePerRun"), "Step 3 (Pricing & x402 setup) supported");
  assert(publishSrc.includes("ASI") || publishSrc.includes("Red-Team"), "Step 4 (ASI scan & publish) supported");
  assert(publishSrc.includes("Successfully Published"), "Success state and live listing link supported");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
