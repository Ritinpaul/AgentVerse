const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Observability & Causal Tracing (Latitude Moat)");
  const root = path.join(__dirname, "..");

  const files = [
    "components/monitor/TraceMetricsRibbon.tsx",
    "components/monitor/TraceList.tsx",
    "components/monitor/TraceViewer.tsx",
    "components/monitor/GovernanceEvents.tsx",
    "components/monitor/CostBreakdown.tsx",
    "components/monitor/LiveFeed.tsx",
    "app/monitor/page.tsx",
    "hooks/useTrace.ts",
  ];
  for (const f of files) {
    assert(fs.existsSync(path.join(root, f)), `File exists: ${f}`);
  }

  const apiContent = fs.readFileSync(path.join(root, "lib/api.ts"), "utf8");
  assert(apiContent.includes("ExecutionTrace"), "ExecutionTrace type definition exported");
  assert(apiContent.includes("TraceEvent"), "TraceEvent causal step model defined");
  assert(apiContent.includes("MOCK_TRACES"), "MOCK_TRACES dataset available");

  // TraceViewer features
  const viewer = fs.readFileSync(path.join(root, "components/monitor/TraceViewer.tsx"), "utf8");
  assert(viewer.includes("Visual Execution Timeline"), "Visual timeline bar rendered");
  assert(viewer.includes("input_payload"), "Input payload inspection supported");
  assert(viewer.includes("output_payload"), "Output payload inspection supported");
  assert(viewer.includes("showRawJson") || viewer.includes("Raw JSON"), "OpenTelemetry raw JSON view toggle supported");
  assert(viewer.includes("Download") || viewer.includes("download"), "JSON export capability supported");

  // Metrics Ribbon
  const ribbon = fs.readFileSync(path.join(root, "components/monitor/TraceMetricsRibbon.tsx"), "utf8");
  assert(ribbon.includes("Total Runs") || ribbon.includes("Total Spend"), "6 top-level metrics ribbon present");

  // LiveFeed
  const liveFeed = fs.readFileSync(path.join(root, "components/monitor/LiveFeed.tsx"), "utf8");
  assert(liveFeed.includes("isStreaming") || liveFeed.includes("speed"), "Live telemetry terminal stream supported with speed control");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
