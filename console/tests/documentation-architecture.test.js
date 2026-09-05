const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Technical Architecture & Kernel Documentation");
  const root = path.join(__dirname, "..");

  const docsFile = path.join(root, "app/docs/page.tsx");
  assert(fs.existsSync(docsFile), "app/docs/page.tsx exists");

  const docsSrc = fs.readFileSync(docsFile, "utf8");
  assert(docsSrc.includes("Architecture & Kernel Documentation"), "Documentation title rendered");
  assert(docsSrc.includes("Port 8005") && docsSrc.includes("Port 8010") && docsSrc.includes("Port 8025"), "3-tier microservice ports documented");
  assert(docsSrc.includes("agent.yaml Specification") || docsSrc.includes("JSON-Schema"), "agent.yaml specification documented");
  assert(docsSrc.includes("GovernOS Sentinel") || docsSrc.includes("ASI01"), "GovernOS Sentinel policy matrix documented");
  assert(docsSrc.includes("VS Code") || docsSrc.includes("extension"), "VS Code extension setup documented");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
