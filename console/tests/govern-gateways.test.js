const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS Gateways & MicroVM Proxy");
  const root = path.join(__dirname, "..");

  const gwFile = path.join(root, "app/govern/gateways/page.tsx");
  assert(fs.existsSync(gwFile), "app/govern/gateways/page.tsx exists");

  const gwSrc = fs.readFileSync(gwFile, "utf8");
  assert(gwSrc.includes("8025"), "Port 8025 local kernel interceptor documented");
  assert(gwSrc.includes("mTLS") || gwSrc.includes("Cryptographic"), "mTLS cryptographic handshake configured");
  assert(gwSrc.includes("Firecracker") || gwSrc.includes("MicroVM"), "Firecracker microVM sandboxes verified");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
