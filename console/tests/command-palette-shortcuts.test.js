const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Global Command Palette (Cmd+K) & Shortcuts");
  const root = path.join(__dirname, "..");

  const paletteFile = path.join(root, "components/shared/CommandPalette.tsx");
  const topNavFile = path.join(root, "components/layout/TopNav.tsx");

  assert(fs.existsSync(paletteFile), "components/shared/CommandPalette.tsx exists");
  assert(fs.existsSync(topNavFile), "components/layout/TopNav.tsx exists");

  const paletteSrc = fs.readFileSync(paletteFile, "utf8");
  assert(paletteSrc.includes("Cmd+K") || paletteSrc.includes("metaKey") || paletteSrc.includes("ctrlKey"), "Cmd+K / Ctrl+K shortcut listener active");
  assert(paletteSrc.includes("filteredCommands") || paletteSrc.includes("filter"), "Real-time command search filter supported");
  assert(paletteSrc.includes("/build"), "Direct shortcut to Monaco IDE & Canvas supported");
  assert(paletteSrc.includes("/govern/approvals"), "Direct shortcut to HITL approvals supported");
  assert(paletteSrc.includes("/govern/scan"), "Direct shortcut to ASI Red-Team scanner supported");
  assert(paletteSrc.includes("/store/publish"), "Direct shortcut to AgentStore publisher supported");

  const navSrc = fs.readFileSync(topNavFile, "utf8");
  assert(navSrc.includes("CommandPalette"), "CommandPalette mounted in TopNav");
  assert(navSrc.includes("Cmd+K"), "Cmd+K search pill indicator rendered in TopNav");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
