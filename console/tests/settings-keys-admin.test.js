const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Organization Settings & Foundation Model Keys");
  const root = path.join(__dirname, "..");

  const settingsFile = path.join(root, "app/settings/page.tsx");
  assert(fs.existsSync(settingsFile), "app/settings/page.tsx exists");

  const settingsSrc = fs.readFileSync(settingsFile, "utf8");
  assert(settingsSrc.includes("Organization Settings"), "Settings title rendered");
  assert(settingsSrc.includes("8005") && settingsSrc.includes("8010") && settingsSrc.includes("8025"), "Ecosystem ports (:8005, :8010, :8025) configurable");
  assert(settingsSrc.includes("Gemini") || settingsSrc.includes("geminiKey"), "Google Gemini API key management present");
  assert(settingsSrc.includes("Claude") || settingsSrc.includes("claudeKey"), "Anthropic Claude API key management present");
  assert(settingsSrc.includes("OpenAI") || settingsSrc.includes("openAiKey"), "OpenAI GPT API key management present");
  assert(settingsSrc.includes("Firecracker") || settingsSrc.includes("MicroVM"), "Firecracker MicroVM sandbox tuning present");
  assert(settingsSrc.includes("Save Configuration") || settingsSrc.includes("handleSave"), "Save configuration button present");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
