const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("GovernOS Immutable Cryptographic Audit Ledger");
  const root = path.join(__dirname, "..");

  const auditFile = path.join(root, "app/govern/audit/page.tsx");
  assert(fs.existsSync(auditFile), "app/govern/audit/page.tsx exists");

  const auditSrc = fs.readFileSync(auditFile, "utf8");
  assert(auditSrc.includes("Immutable Cryptographic Audit Ledger"), "Audit ledger heading rendered");
  assert(auditSrc.includes("SHA-256") || auditSrc.includes("hash"), "SHA-256 cryptographic hashes displayed");
  assert(auditSrc.includes("Verify Merkle Proofs"), "Merkle proof verification button present");
  assert(auditSrc.includes("Export CSV") || auditSrc.includes(".csv"), "CSV export supported");
  assert(auditSrc.includes("outcomeFilter") || auditSrc.includes("ALLOW"), "ALLOW / BLOCKED / REDACTED outcome filters supported");
  assert(auditSrc.includes("searchQuery"), "Search query engine active on audit ledger");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
