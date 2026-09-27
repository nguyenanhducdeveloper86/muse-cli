// e2e_test.mjs — Test end-to-end tool call for muse_status
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

let callDone = false;

rl.on("line", (line) => {
  try {
    const msg = JSON.parse(line);

    if (msg.id === 1) {
      // Send tool call for muse_status
      const callReq = JSON.stringify({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "muse_status",
          arguments: {},
        },
      });
      proc.stdin.write(callReq + "\n");
    } else if (msg.id === 2) {
      console.error("✅ Tool call response:", JSON.stringify(msg, null, 2));
      callDone = true;
      proc.kill();
      process.exit(0);
    }
  } catch (e) {
    console.error("[e2e error]:", e.message);
  }
});

// Step 1: Initialize
const initReq = JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "e2e-test", version: "1.0.0" },
  },
});
proc.stdin.write(initReq + "\n");

setTimeout(() => {
  if (!callDone) {
    console.error("❌ E2E test timed out");
    proc.kill();
    process.exit(1);
  }
}, 20000);
