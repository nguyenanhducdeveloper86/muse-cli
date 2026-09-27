// smoke.mjs — Test JSON-RPC protocol over stdio for muse-bridge-mcp
import { spawn } from "node:child_process";
import path from "node:path";
import readline from "node:readline";

const serverPath = path.resolve(path.dirname(new URL(import.meta.url).pathname), "server.mjs");

const proc = spawn("node", [serverPath], {
  stdio: ["pipe", "pipe", "inherit"],
});

const rl = readline.createInterface({
  input: proc.stdout,
  terminal: false,
});

let testPassed = false;

rl.on("line", (line) => {
  try {
    const msg = JSON.parse(line);
    console.error("[smoke response]:", JSON.stringify(msg));

    if (msg.id === 1 && msg.result?.capabilities?.tools) {
      console.error("✅ Initialize handshake passed!");
      // Send tools/list request
      const listReq = JSON.stringify({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/list",
      });
      proc.stdin.write(listReq + "\n");
    } else if (msg.id === 2 && Array.isArray(msg.result?.tools)) {
      console.error(`✅ Tools list passed! Found ${msg.result.tools.length} tools:`);
      for (const t of msg.result.tools) {
        console.error(`   - ${t.name}: ${t.description.slice(0, 50)}...`);
      }
      testPassed = true;
      proc.kill();
      process.exit(0);
    }
  } catch (e) {
    console.error("[smoke error parsing line]:", e.message);
  }
});

// Step 1: Send initialize request
const initReq = JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: {
      name: "smoke-test",
      version: "1.0.0",
    },
  },
});
proc.stdin.write(initReq + "\n");

setTimeout(() => {
  if (!testPassed) {
    console.error("❌ Smoke test timed out!");
    proc.kill();
    process.exit(1);
  }
}, 10000);
