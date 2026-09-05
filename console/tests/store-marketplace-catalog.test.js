const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("AgentStore Marketplace & Agent Details");
  const root = path.join(__dirname, "..");

  const storePage = path.join(root, "app/store/page.tsx");
  const detailPage = path.join(root, "app/store/[agentId]/page.tsx");
  const subnavFile = path.join(root, "components/store/StoreSubNav.tsx");

  assert(fs.existsSync(storePage), "app/store/page.tsx exists");
  assert(fs.existsSync(detailPage), "app/store/[agentId]/page.tsx exists");
  assert(fs.existsSync(subnavFile), "components/store/StoreSubNav.tsx exists");

  const storeSrc = fs.readFileSync(storePage, "utf8");
  assert(storeSrc.includes("AgentStore & A2A Marketplace"), "Marketplace title rendered");
  assert(storeSrc.includes("x402"), "x402 micropayments callout present");
  assert(storeSrc.includes("categories") || storeSrc.includes("selectedCategory"), "Category filtering supported");
  assert(storeSrc.includes("Search"), "Search input present");
  assert(storeSrc.includes("Provisioned Live API Key") || storeSrc.includes("provisionedKey"), "Instant API key provisioning modal supported");

  const detailSrc = fs.readFileSync(detailPage, "utf8");
  assert(detailSrc.includes("5-Factor Computed Trust Score"), "Trust score breakdown rendered");
  assert(detailSrc.includes("Price per Execution"), "Price per execution displayed");
  assert(detailSrc.includes("codeSnippets") || detailSrc.includes("python"), "Multi-language integration snippets present");
  assert(detailSrc.includes("Hire / Install"), "Hire / Install action button present");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
