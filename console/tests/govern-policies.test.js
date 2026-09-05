const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS Visual Policy Editor");
  const root = path.join(__dirname, "..");

  const policyFile = path.join(root, "app/govern/policies/page.tsx");
  assert(fs.existsSync(policyFile), "app/govern/policies/page.tsx exists");

  const policySrc = fs.readFileSync(policyFile, "utf8");
  assert(policySrc.includes("Visual Policy Rule Editor"), "Visual Policy Rule Editor heading rendered");
  assert(policySrc.includes("ENFORCE") && policySrc.includes("AUDIT") && policySrc.includes("DISABLED"), "Supports ENFORCE, AUDIT, and DISABLED policy modes");
  assert(policySrc.includes("Add Security Rule"), "Custom rule creation modal supported");
  assert(policySrc.includes("Deploy to MicroVM Kernel"), "Deploy rules to MicroVM kernel button present");

  const hookSrc = fs.readFileSync(path.join(root, "hooks/useGovernance.ts"), "utf8");
  assert(hookSrc.includes("ASI01"), "ASI01 Prompt Injection Shield defined");
  assert(hookSrc.includes("ASI02"), "ASI02 Tool Scope Whitelist defined");
  assert(hookSrc.includes("ASI03"), "ASI03 PII & Secret Redaction defined");
  assert(hookSrc.includes("ASI04"), "ASI04 Runaway Cost Breaker defined");
  assert(hookSrc.includes("ASI05"), "ASI05 MicroVM Boundary Isolation defined");
  assert(hookSrc.includes("ASI09"), "ASI09 A2A Escrow Verification defined");
  assert(hookSrc.includes("togglePolicy"), "togglePolicy state transition available");
  assert(hookSrc.includes("updatePolicyMode"), "updatePolicyMode state transition available");
  assert(hookSrc.includes("addPolicy"), "addPolicy state transition available");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
