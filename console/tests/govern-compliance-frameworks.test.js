const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS Regulatory Compliance & Certification Badges");
  const root = path.join(__dirname, "..");

  const compFile = path.join(root, "app/govern/compliance/page.tsx");
  assert(fs.existsSync(compFile), "app/govern/compliance/page.tsx exists");

  const compSrc = fs.readFileSync(compFile, "utf8");
  assert(compSrc.includes("Compliance"), "Compliance verification title rendered");
  assert(compSrc.includes("SOC2"), "SOC2 Type II framework card present");
  assert(compSrc.includes("HIPAA"), "HIPAA HITECH security rule framework card present");
  assert(compSrc.includes("GDPR"), "GDPR data minimization framework card present");
  assert(compSrc.includes("EU AI Act") || compSrc.includes("eu_ai_act"), "EU AI Act high-risk AI framework card present");
  assert(compSrc.includes("Copy Embed Badge"), "Copy Embed Badge markdown button present");
  assert(compSrc.includes("Export Audit Pack"), "Export Audit Pack PDF button present");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
