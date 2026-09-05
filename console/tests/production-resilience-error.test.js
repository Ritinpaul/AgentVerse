const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Production Error Resilience & Boundaries");
  const root = path.join(__dirname, "..");

  const boundaryFile = path.join(root, "components/shared/ErrorBoundary.tsx");
  const errorFile = path.join(root, "app/error.tsx");
  const notFoundFile = path.join(root, "app/not-found.tsx");

  assert(fs.existsSync(boundaryFile), "components/shared/ErrorBoundary.tsx exists");
  assert(fs.existsSync(errorFile), "app/error.tsx exists");
  assert(fs.existsSync(notFoundFile), "app/not-found.tsx exists");

  const boundarySrc = fs.readFileSync(boundaryFile, "utf8");
  assert(boundarySrc.includes("Recover Component"), "ErrorBoundary provides recovery action trigger");

  const errorSrc = fs.readFileSync(errorFile, "utf8");
  assert(errorSrc.includes("Reset Boundary"), "app/error.tsx provides reset trigger");

  const notFoundSrc = fs.readFileSync(notFoundFile, "utf8");
  assert(notFoundSrc.includes("404"), "app/not-found.tsx handles missing routes gracefully");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
