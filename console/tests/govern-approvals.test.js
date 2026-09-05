const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS Human-in-the-Loop Approvals Queue");
  const root = path.join(__dirname, "..");

  const approvalsFile = path.join(root, "app/govern/approvals/page.tsx");
  assert(fs.existsSync(approvalsFile), "app/govern/approvals/page.tsx exists");

  const approvalsSrc = fs.readFileSync(approvalsFile, "utf8");
  assert(approvalsSrc.includes("Human-in-the-Loop"), "HITL Approvals Queue title rendered");
  assert(approvalsSrc.includes("Approve & Sign"), "Approve & Sign action button present");
  assert(approvalsSrc.includes("Reject"), "Reject action button present");
  assert(approvalsSrc.includes("timeout_seconds") || approvalsSrc.includes("timeout"), "Countdown timeout indicator present");
  assert(approvalsSrc.includes("Risk:") || approvalsSrc.includes("risk_score"), "Risk score rating displayed");
  assert(approvalsSrc.includes("payload"), "Expandable payload drawer supported for inspecting intercepted arguments");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
