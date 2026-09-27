// test_ask.mjs — Test muse_ask tool call
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

rl.on("line", (line) => {
  try {
    const msg = JSON.parse(line);
    if (msg.id === 1) {
      const callReq = JSON.stringify({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "muse_ask",
          arguments: {
            prompt: "Trả lời ngắn gọn 1 từ: 2 + 2 bằng mấy?",
            timeout: 30,
          },
        },
      });
      proc.stdin.write(callReq + "\n");
    } else if (msg.id === 2) {
      console.error("✅ muse_ask response:", JSON.stringify(msg, null, 2));
      proc.kill();
      process.exit(0);
    }
  } catch (e) {
    console.error("[error]:", e.message);
  }
});

proc.stdin.write(
  JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "test-ask", version: "1.0.0" },
    },
  }) + "\n"
);
