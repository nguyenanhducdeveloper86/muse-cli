#!/usr/bin/env node
// muse-bridge-mcp — Model Context Protocol Server for Muse.ai (Meta AI Personal Agent)
//
// Wraps http://127.0.0.1:8766 (the Muse Bridge Server) as MCP tools.
// Provides:
//   - muse_status: check connection and session readiness
//   - muse_ask: ask Muse a prompt or question
//   - muse_generate_image: Text-to-Image & Image-to-Image generation
//   - muse_generate_video: Text-to-Video & Image-to-Video animation

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function applyArgvEnv(argv = process.argv.slice(2)) {
  let i = 0;
  while (i < argv.length) {
    if (argv[i] === "--env" && argv[i + 1] && argv[i + 1].includes("=")) {
      const [k, ...rest] = argv[i + 1].split("=");
      if (k) process.env[k] = rest.join("=");
      i += 2;
      continue;
    }
    if (argv[i].includes("=") && /^[A-Z0-9_]+?=/.test(argv[i])) {
      const [k, ...rest] = argv[i].split("=");
      if (k && process.env[k] == null) process.env[k] = rest.join("=");
    }
    i += 1;
  }
}
applyArgvEnv();

const BASE = (process.env.MUSE_BASE || "http://127.0.0.1:8766").replace(/\/+$/, "");
const BRIDGE_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");

async function checkBridgeAlive() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureBridge() {
  const alive = await checkBridgeAlive();
  if (alive) return true;

  console.error(`[muse-mcp] Bridge tại ${BASE} chưa chạy, đang tự động khởi động ngầm...`);
  const startScript = path.join(BRIDGE_ROOT, "start.sh");
  if (fs.existsSync(startScript)) {
    try {
      const child = spawn(startScript, ["serve"], {
        detached: true,
        stdio: "ignore",
        env: { ...process.env, MUSE_PORT: "8766" },
        cwd: BRIDGE_ROOT,
      });
      child.unref();

      // Poll for readiness up to 15 seconds
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 500));
        if (await checkBridgeAlive()) {
          console.error(`[muse-mcp] Bridge đã khởi động thành công và sẵn sàng tại ${BASE}!`);
          return true;
        }
      }
    } catch (e) {
      console.error(`[muse-mcp] Lỗi khi tự động khởi động bridge: ${e.message}`);
    }
  }
  return false;
}

async function callBridge(endpoint, body = null, method = "POST", timeoutMs = 180000) {
  await ensureBridge();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
    };
    if (body) {
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${BASE}${endpoint}`, opts);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    const isTimeout = e.name === "AbortError" || e.name === "TimeoutError";
    return {
      ok: false,
      status: isTimeout ? 504 : 503,
      data: {
        error: isTimeout
          ? `Yêu cầu tới Muse Bridge bị quá thời gian (${Math.round(timeoutMs / 1000)}s)`
          : `Không thể kết nối tới Muse Bridge tại ${BASE}: ${e.message}`,
      },
    };
  } finally {
    clearTimeout(timer);
  }
}

const TOOLS = [
  {
    name: "muse_status",
    description: "Kiểm tra trạng thái kết nối tới Muse.ai Bridge Server và phiên đăng nhập cookies.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "muse_ask",
    description: "Gửi câu hỏi hoặc prompt văn bản tới Muse.ai (Meta AI Personal Agent) và nhận câu trả lời.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Nội dung câu hỏi hoặc prompt cần gửi cho Muse.",
        },
        timeout: {
          type: "number",
          description: "Thời gian chờ tối đa (giây). Mặc định: 60.",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "muse_generate_image",
    description: "Sinh ảnh AI chất lượng cao từ văn bản (Text-to-Image) hoặc từ ảnh tham chiếu (Image-to-Image) qua Muse.ai và lưu về file ảnh .png.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Mô tả chi tiết hình ảnh cần tạo (prompt tạo ảnh).",
        },
        output_path: {
          type: "string",
          description: "Đường dẫn lưu file ảnh kết quả (ví dụ: 'assets/hero_banner.png'). Mặc định lưu file .png trong thư mục hiện tại.",
        },
        ref_image: {
          type: "string",
          description: "Đường dẫn file ảnh tham chiếu nếu muốn tạo ảnh biến thể hoặc giữ nhân vật mẫu.",
        },
        timeout: {
          type: "number",
          description: "Thời gian chờ tối đa (giây). Mặc định: 90.",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "muse_generate_video",
    description: "Sinh video AI chuyển động hoạt họa từ văn bản (Text-to-Video) hoặc tạo chuyển động cho nhân vật từ ảnh mẫu (Image-to-Video) qua Muse.ai và lưu về file .mp4.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Mô tả chuyển động / hành động cần sinh trong video.",
        },
        output_path: {
          type: "string",
          description: "Đường dẫn lưu file video kết quả (ví dụ: 'assets/demo_animation.mp4'). Mặc định lưu file .mp4 trong thư mục hiện tại.",
        },
        ref_image: {
          type: "string",
          description: "Đường dẫn ảnh nhân vật / cảnh mẫu cần đưa vào chuyển động (Image-to-Video).",
        },
        timeout: {
          type: "number",
          description: "Thời gian chờ tối đa (giây). Mặc định: 120.",
        },
      },
      required: ["prompt"],
    },
  },
];

const server = new Server(
  {
    name: "muse-bridge-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;

  if (name === "muse_status") {
    const res = await callBridge("/status", null, "GET", 10000);
    const text = JSON.stringify(res.data, null, 2);
    return {
      content: [{ type: "text", text: `[Trạng thái Muse Bridge]\n${text}` }],
      isError: !res.ok,
    };
  }

  if (name === "muse_ask") {
    const timeout = (args.timeout || 60) * 1000;
    const res = await callBridge("/api/ask", { prompt: args.prompt, timeout: args.timeout || 60 }, "POST", timeout + 5000);
    if (!res.ok) {
      return {
        content: [{ type: "text", text: `Lỗi khi gọi Muse: ${res.data?.error || JSON.stringify(res.data)}` }],
        isError: true,
      };
    }
    return {
      content: [{ type: "text", text: res.data?.reply || JSON.stringify(res.data) }],
    };
  }

  if (name === "muse_generate_image") {
    const timeout = (args.timeout || 90) * 1000;
    const payload = {
      prompt: args.prompt,
      out_path: args.output_path,
      ref_image: args.ref_image,
      timeout: args.timeout || 90,
    };
    const res = await callBridge("/api/generate-image", payload, "POST", timeout + 5000);
    if (!res.ok) {
      return {
        content: [{ type: "text", text: `Lỗi tạo ảnh: ${res.data?.error || JSON.stringify(res.data)}` }],
        isError: true,
      };
    }
    return {
      content: [
        {
          type: "text",
          text: `🎉 Đã tạo ảnh thành công qua Muse.ai!\n📁 Đường dẫn file: ${res.data?.path || args.output_path || "ảnh đã lưu"}\nLoại: ${res.data?.type || "image"}`,
        },
      ],
    };
  }

  if (name === "muse_generate_video") {
    const timeout = (args.timeout || 120) * 1000;
    const payload = {
      prompt: args.prompt,
      out_path: args.output_path,
      ref_image: args.ref_image,
      timeout: args.timeout || 120,
    };
    const res = await callBridge("/api/generate-video", payload, "POST", timeout + 5000);
    if (!res.ok) {
      return {
        content: [{ type: "text", text: `Lỗi tạo video: ${res.data?.error || JSON.stringify(res.data)}` }],
        isError: true,
      };
    }
    return {
      content: [
        {
          type: "text",
          text: `🎉 Đã tạo video thành công qua Muse.ai!\n📁 Đường dẫn file: ${res.data?.path || args.output_path || "video đã lưu"}\nLoại: ${res.data?.type || "video"}`,
        },
      ],
    };
  }

  return {
    content: [{ type: "text", text: `Không tìm thấy tool: ${name}` }],
    isError: true,
  };
});

const transport = new StdioServerTransport();
await server.connect(transport);
console.error(`[muse-bridge-mcp] MCP Server đã khởi chạy qua stdio. Bridge URL: ${BASE}`);
