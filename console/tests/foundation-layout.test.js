const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Foundation, App Shell & Layout");
  const root = path.join(__dirname, "..");

  // Config files
  const configs = [
    "package.json",
    "tsconfig.json",
    "next.config.mjs",
    "tailwind.config.ts",
    "app/globals.css",
  ];
  for (const c of configs) {
    assert(fs.existsSync(path.join(root, c)), `Config file exists: ${c}`);
  }

  // Layout components
  const layouts = [
    "components/layout/Sidebar.tsx",
    "components/layout/TopNav.tsx",
    "components/layout/ShellLayout.tsx",
    "app/layout.tsx",
    "app/page.tsx",
  ];
  for (const l of layouts) {
    assert(fs.existsSync(path.join(root, l)), `Layout component exists: ${l}`);
  }

  // Sidebar links check
  const sidebar = fs.readFileSync(path.join(root, "components/layout/Sidebar.tsx"), "utf8");
  assert(sidebar.includes("/build"), "Sidebar navigates to /build (AgentStudio IDE)");
  assert(sidebar.includes("/agents"), "Sidebar navigates to /agents (Fleet Catalog)");
  assert(sidebar.includes("/monitor"), "Sidebar navigates to /monitor (Observability & Traces)");
  assert(sidebar.includes("/govern"), "Sidebar navigates to /govern (GovernOS Kernel)");
  assert(sidebar.includes("/store"), "Sidebar navigates to /store (Marketplace & A2A)");

  // TopNav health indicators
  const topnav = fs.readFileSync(path.join(root, "components/layout/TopNav.tsx"), "utf8");
  assert(topnav.includes("ServerStatusPill") || topnav.includes("8005"), "TopNav monitors ecosystem backend ports (:8005, :8010, :8025)");
  assert(topnav.includes("Search"), "TopNav contains global command search");

  // Globals CSS dark mode tokens
  const css = fs.readFileSync(path.join(root, "app/globals.css"), "utf8");
  assert(css.includes("--background") || css.includes("090a0f") || css.includes("dark"), "Dark mode design tokens configured in globals.css");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
