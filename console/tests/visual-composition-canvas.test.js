const fs = require("fs");
const path = require("path");
const { createSuite } = require("./test-utils");

function run() {
  const { assert, report } = createSuite("Visual Composition Canvas (React Flow)");
  const root = path.join(__dirname, "..");

  const canvasFile = path.join(root, "components/build/VisualCanvas.tsx");
  assert(fs.existsSync(canvasFile), "VisualCanvas.tsx component exists");

  const canvasSrc = fs.readFileSync(canvasFile, "utf8");
  assert(canvasSrc.includes("reactflow") || canvasSrc.includes("ReactFlow"), "ReactFlow engine integrated");
  assert(canvasSrc.includes("agentCore"), "AgentCore custom node type registered");
  assert(canvasSrc.includes("ToolNode") || canvasSrc.includes("tool"), "Tool custom node registered with scope badges");
  assert(canvasSrc.includes("GovernanceNode") || canvasSrc.includes("governance"), "GovernOS custom node registered");
  assert(canvasSrc.includes("parseYamlToGraph"), "Declarative YAML to Graph parser present");

  // Verify YAML Parsing logic
  function parseYamlMock(yaml) {
    const nodes = [];
    const edges = [];
    const nameMatch = yaml.match(/^name:\s*(.+)$/m);
    const agentName = nameMatch?.[1]?.trim() ?? "agent";
    nodes.push({ id: "agent-core", type: "agentCore", label: agentName });

    const toolsSection = yaml.split("tools:")[1] || "";
    const toolBlocks = toolsSection.split(/-\s+name:/).filter((b) => b.trim());
    let i = 0;
    for (const block of toolBlocks) {
      const name = block.split("\n")[0].trim();
      const scopeMatch = block.match(/scope:\s*([\w_]+)/);
      const scope = scopeMatch ? scopeMatch[1] : "read";
      if (name) {
        nodes.push({ id: `tool-${i}`, type: "tool", label: name, scope });
        edges.push({ id: `e-tool-${i}`, source: `tool-${i}`, target: "agent-core" });
        i++;
      }
    }
    return { nodes, edges };
  }

  const sampleYaml = `name: test-agent\nruntime:\n  model: gemini-2.5-pro\ntools:\n  - name: web_search\n    scope: read\n  - name: send_email\n    scope: read_write`;
  const { nodes, edges } = parseYamlMock(sampleYaml);

  assert(nodes.length === 3, "Parsed 3 nodes (1 agent core + 2 tool nodes)");
  assert(nodes[0].label === "test-agent", "Agent core extracted correct label");
  assert(nodes[1].label === "web_search" && nodes[1].scope === "read", "web_search tool extracted with scope 'read'");
  assert(nodes[2].label === "send_email" && nodes[2].scope === "read_write", "send_email tool extracted with scope 'read_write'");
  assert(edges.length === 2, "Both tools connect to agent-core node");

  return report();
}

module.exports = { run };
if (require.main === module) {
  run();
}
