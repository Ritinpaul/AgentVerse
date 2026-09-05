const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Agent-to-Agent (A2A) Escrow & Compositions");
  const root = path.join(__dirname, "..");

  const a2aFile = path.join(root, "app/store/a2a/page.tsx");
  const compFile = path.join(root, "app/store/compositions/page.tsx");

  assert(fs.existsSync(a2aFile), "app/store/a2a/page.tsx exists");
  assert(fs.existsSync(compFile), "app/store/compositions/page.tsx exists");

  const a2aSrc = fs.readFileSync(a2aFile, "utf8");
  assert(a2aSrc.includes("Agent-to-Agent") || a2aSrc.includes("A2A"), "A2A Escrow title rendered");
  assert(a2aSrc.includes("x402"), "x402 protocol referenced");
  assert(a2aSrc.includes("settleContract") || a2aSrc.includes("Settle"), "Manual contract settlement supported");
  assert(a2aSrc.includes("contract_hash"), "Contract hash copy supported");

  const compSrc = fs.readFileSync(compFile, "utf8");
  assert(compSrc.includes("Multi-Agent Compositions"), "Multi-agent compositions title rendered");
  assert(compSrc.includes("revenue share") || compSrc.includes("share_pct"), "Per-subagent revenue split percentage displayed");
  assert(compSrc.includes("Hire Pipeline") || compSrc.includes("handleRunPipeline"), "Multi-agent pipeline dispatch trigger supported");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
