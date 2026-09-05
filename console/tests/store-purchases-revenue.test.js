const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("AgentStore Purchases & Creator Revenue");
  const root = path.join(__dirname, "..");

  const purchasesFile = path.join(root, "app/store/purchases/page.tsx");
  const revenueFile = path.join(root, "app/store/revenue/page.tsx");

  assert(fs.existsSync(purchasesFile), "app/store/purchases/page.tsx exists");
  assert(fs.existsSync(revenueFile), "app/store/revenue/page.tsx exists");

  const purchasesSrc = fs.readFileSync(purchasesFile, "utf8");
  assert(purchasesSrc.includes("My Agent Installs"), "Purchases dashboard title rendered");
  assert(purchasesSrc.includes("API Key") || purchasesSrc.includes("api_key"), "API key management supported");
  assert(purchasesSrc.includes("rotateApiKey") || purchasesSrc.includes("Rotate"), "API key rotation supported");
  assert(purchasesSrc.includes("pauseInstallation") || purchasesSrc.includes("Pause"), "Subscription pause/resume supported");
  assert(purchasesSrc.includes("Spend vs Monthly Ceiling") || purchasesSrc.includes("spend_usd"), "Spend ceiling tracking supported");

  const revenueSrc = fs.readFileSync(revenueFile, "utf8");
  assert(revenueSrc.includes("Creator Revenue"), "Creator revenue dashboard title rendered");
  assert(revenueSrc.includes("80%"), "80% builder net earnings displayed");
  assert(revenueSrc.includes("Pending Payout") || purchasesSrc.includes("payout"), "Pending weekly payout tracking supported");
  assert(revenueSrc.includes("Polygon") || revenueSrc.includes("Wallet"), "Polygon USDC payout wallet configuration supported");
  assert(revenueSrc.includes("daily_history") || revenueSrc.includes("Daily"), "Daily execution volume table rendered");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
