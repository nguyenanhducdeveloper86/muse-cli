# AGENT.md — Autonomous Agent Integration & Setup Guide

This document is specifically designed for autonomous AI agents (such as **omp**, **Hermes**, **Claude Code**, **Cursor**, **Cline**, **Devin**, or sub-agents) to automatically discover, configure, authenticate, and control **`muse-cli`** and **`muse-bridge`** without requiring human instruction.

---

## 1. System Identity & Capabilities

`muse-bridge` is a local bridge and CLI that exposes **Muse.ai (Meta AI Personal Agent · Project Hatch)** as:
1. **An OpenAI-compatible LLM provider** (`/v1/chat/completions` at `http://127.0.0.1:8765/v1`, model `muse-ai`).
2. **A Text-to-Image generator** (`muse image "<prompt>" -o <out.png>`).
3. **An Image-to-Image generator** (`muse image "<prompt>" --ref <image.png> -o <out.png>`).
4. **A Text-to-Video generator** (`muse video "<prompt>" -o <out.mp4>`).
5. **An Image-to-Video generator** (`muse video "<prompt>" --ref <image.png> -o <out.mp4>`).

---

## 2. Agent Bootstrap & Self-Setup Flow

When an agent enters this repository or needs to provide Muse capabilities, execute the following deterministic sequence:

### Step 2.1: Python Environment & Dependencies
```bash
# Check if virtual environment exists, if not create it
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Ensure Playwright Chromium browser is installed
python -m playwright install chromium
```

### Step 2.2: Verify or Establish Authentication
The agent should test whether credentials already exist:
```bash
./start.sh status
```
- **If status returns `✅ Kết nối thành công!`**: Authentication is ready. Proceed to execution.
- **If status returns `❌ Chưa cấu hình cookies`**:
  - Check if the environment variable `MUSE_COOKIES` is present.
  - Or check if `~/.muse/cookies.txt` or `./cookies.txt` exists.
  - If a user is present at the desktop, run interactive auto-login:
    ```bash
    ./start.sh login
    ```
    *(This opens Chrome, lets the user log in on `https://muse.ai/`, and automatically grabs session cookies into `~/.muse/cookies.txt` without F12).*
  - In headless/remote environments where cookies are already captured, supply them via:
    ```bash
    echo "<raw_cookie_string>" > ~/.muse/cookies.txt
    ```

---

## 3. Starting the OpenAI-Compatible Bridge Server

To use Muse as an LLM model inside `omp`, `Cursor`, `Cline`, or via API:

### Launch Daemon / Background Server:
```bash
./start.sh serve --port 8765 &
```
*(Or invoke via python: `python -m muse.server &`)*

### Verify Server Readiness:
```bash
curl -s http://127.0.0.1:8765/health
# Expected response: {"status": "running", "service": "muse.ai Bridge Server"}

curl -s http://127.0.0.1:8765/v1/models
# Expected response: {"object": "list", "data": [{"id": "muse-ai", ...}]}
```

### Test Chat Completion:
```bash
curl -s -X POST http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse-ai",
    "messages": [{"role": "user", "content": "Ping"}]
  }'
```

---

## 4. OMP Integration Protocol

### Step 4.1: Register Model Provider in OMP
Add the following block to `~/.omp/agent/models.yml`:
```yaml
providers:
  muse:
    baseUrl: http://127.0.0.1:8765/v1
    apiKey: muse-local-key
    api: openai-completions
    models:
    - id: muse-ai
      name: Muse.ai Personal Agent (Meta AI)
      input: [text]
      contextWindow: 128000
      maxTokens: 8192
```

### Step 4.2: Enable Multimedia Skill in OMP
Symlink the repository's skill into the OMP skills directory:
```bash
mkdir -p ~/.omp/skills
ln -sf "$(pwd)/skills/muse-multimedia" ~/.omp/skills/muse-multimedia
```

---

## 5. Direct Agent CLI Command Reference

When an agent needs to generate visual assets or perform fast queries, invoke the CLI directly:

### 1. One-off Query / Code Generation
```bash
muse ask "<prompt>"
```

### 2. Text-to-Image Generation
```bash
muse image "<image description>" -o <output_filename.png>
```

### 3. Image-to-Image (Style Transfer / Modification)
```bash
muse image "<transformation instructions>" --ref <source_image.png> -o <output_filename.png>
```

### 4. Text-to-Video Generation
```bash
muse video "<video description>" -o <output_filename.mp4>
```

### 5. Image-to-Video (Animation from Reference)
```bash
muse video "<animation instructions>" --ref <character_image.png> -o <output_filename.mp4>
```

---

## 6. Troubleshooting & Self-Healing for Agents

| Issue | Cause | Agent Action |
|---|---|---|
| `No Muse.ai cookies found!` | `cookies.txt` or `MUSE_COOKIES` missing | Check environment variables or prompt user to run `muse login`. |
| `Page.goto: Timeout 45000ms exceeded` | Network glitch or slow initial load | Retry once with `wait_until='domcontentloaded'`. |
| `Video generation timeout` | Large video render takes >60s | Allow up to 120s timeout or check Muse Library on web. |
| `Address already in use: 8765` | Existing server process running | Identify PID via `lsof -i :8765` and reuse or restart. |
