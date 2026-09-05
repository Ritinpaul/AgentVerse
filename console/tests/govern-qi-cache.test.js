const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS QI Semantic Cache & Telemetry");
  const root = path.join(__dirname, "..");

  const analyticsFile = path.join(root, "app/govern/analytics/page.tsx");
  assert(fs.existsSync(analyticsFile), "app/govern/analytics/page.tsx exists");

  const analyticsSrc = fs.readFileSync(analyticsFile, "utf8");
  assert(analyticsSrc.includes("QI Semantic Cache"), "QI Semantic Cache title rendered");
  assert(analyticsSrc.includes("hit_rate_pct") || analyticsSrc.includes("Hit Ratio"), "Hit ratio percentage displayed");
  assert(analyticsSrc.includes("cost_saved_usd") || analyticsSrc.includes("Total Saved"), "Cost savings metric displayed");
  assert(analyticsSrc.includes("tokens_saved") || analyticsSrc.includes("Tokens Spared"), "Tokens spared metric displayed");
  assert(analyticsSrc.includes("Purge Stale Vectors"), "Vector purge action button supported");
  assert(analyticsSrc.includes("Latency Comparison") || analyticsSrc.includes("speedupRatio"), "Latency speedup comparison bar rendered");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
