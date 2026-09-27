# 🎭 muse-cli & muse-bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-orange.svg)](https://platform.openai.com/docs/api-reference)

**Unofficial CLI & OpenAI-Compatible Bridge for Muse.ai (Meta AI Personal Agent · Project Hatch)**

Tích hợp toàn diện **Muse.ai** vào dòng lệnh (CLI), cung cấp cầu nối API chuẩn **OpenAI (`/v1/chat/completions`)**, hỗ trợ trò chuyện, viết code, sinh ảnh AI (Text-to-Image), sinh video AI (Text-to-Video & Image-to-Video) và tích hợp trực tiếp vào **`omp`**, **Cursor**, **Cline**, v.v.

---

## 🌟 Tính năng nổi bật (Key Features)

- 💬 **Terminal Chat & QA (`muse chat` / `muse ask`):** Trò chuyện tương tác trực tiếp với Muse ngay trong terminal.
- 💻 **Tác vụ Coding:** Khả năng sinh mã nguồn hoàn chỉnh (HTML/JS Canvas game, script tự động hóa, thuật toán).
- 🎨 **Tạo ảnh AI (`muse image`):** Sinh ảnh chất lượng cao từ văn bản (Text-to-Image) và tự động tải về máy.
- 🎬 **Tạo video AI (`muse video`):** Sinh video hoạt họa từ văn bản (Text-to-Video).
- 🖼️ ➔ 🎬 **Tạo video từ ảnh mẫu (`muse video --ref`):** Nhận diện nhân vật từ ảnh tham chiếu và sinh video chuyển động (Image-to-Video).
- 🔌 **OpenAI-Compatible Bridge Server (`muse serve`):** Mở endpoint `http://127.0.0.1:8765/v1` chuẩn OpenAI để cắm thẳng vào **`omp`**, **Cursor**, **Cline**, hoặc gọi bằng `curl`.
- ⚡ **Tích hợp sẵn vào `omp`:** Cung cấp model `muse-ai` trong `omp` và Skill `muse-multimedia`.

---

## 🚀 Cài đặt (Installation)

### 1. Clone repository
```bash
git clone https://github.com/nguyenanhducdeveloper86/muse-bridge.git
cd muse-bridge
```

### 2. Cài đặt thư viện
```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

### 3. Cài đặt lệnh toàn cục (Tùy chọn)
```bash
pip install -e .
# Hoặc tạo symlink:
ln -sf $(pwd)/start.sh ~/.local/bin/muse
```

---

## 🔑 Thiết lập xác thực (Authentication)

### Cách 1: Tự động hoàn toàn (Khuyên dùng — Không cần F12)
Chỉ cần chạy lệnh:
```bash
muse login
```
1. Cửa sổ Google Chrome sẽ tự động bật lên tại `https://muse.ai/`.
2. Bạn chỉ việc đăng nhập tài khoản Muse.ai / Meta của bạn trên cửa sổ web vừa mở.
3. Ngay khi đăng nhập xong, công cụ sẽ **tự động bắt cookies**, lưu vào `~/.muse/cookies.txt` và tự động đóng trình duyệt lại. **Bạn không cần đụng tới F12 hay copy chuỗi cookie dài dòng.**

---

### Cách 2: Nhập thủ công (Dành cho VPS / Headless Server qua SSH)
Nếu máy chủ của bạn không có màn hình hiển thị:
```bash
muse login --manual
```
+- Mở `https://muse.ai/` trên máy tính cá nhân, nhấn `F12` → tab **Network** (hoặc **Application** → **Cookies**).
+- Copy chuỗi Cookie header và dán vào terminal.

---

Kiểm tra kết nối:
```bash
muse status
```

---

## 📖 Hướng dẫn sử dụng (CLI Usage)

### 1. Trò chuyện & Hỏi đáp
```bash
# Hỏi nhanh 1 câu:
muse ask "1 + 1 bằng mấy?"

# Trò chuyện tương tác liên tục:
muse chat
```

### 2. Sinh ảnh AI (Text-to-Image)
```bash
muse image "Một chú mèo con phi hành gia đang trôi nổi trong không gian vũ trụ" -o kitten_astro.png
```

### 3. Sinh video AI (Text-to-Video)
```bash
muse video "Một chú robot nhỏ đang pha cà phê buổi sáng" -o robot_coffee.mp4
```

### 4. Sinh video từ ảnh tham chiếu (Image-to-Video)
```bash
muse video "Nhân vật này đang mỉm cười và vẫy tay chào" --ref my_character.png -o character_wave.mp4
```

---

## 🔌 Dựng OpenAI Bridge Server cho omp / Cursor / Cline

Khởi động server cầu nối cục bộ:
```bash
muse serve
# Mặc định lắng nghe tại: http://127.0.0.1:8765/v1
```

### Test nhanh bằng cURL chuẩn OpenAI:
```bash
curl http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse-ai",
    "messages": [{"role": "user", "content": "Xin chào Muse!"}]
  }'
```

---

## ⚡ Tích hợp vào OMP (Oh My Pi / Coding Agent)

### Cách 1: Sử dụng như một LLM Model trong `omp`
Thêm cấu hình vào `~/.omp/agent/models.yml`:
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

Khởi chạy `omp` với model Muse:
```bash
omp --model muse/muse-ai
```

### Cách 2: Sử dụng Muse làm Tool sinh ảnh / video trong `omp`
Copy hoặc symlink skill vào thư mục `~/.omp/skills/`:
```bash
ln -sf $(pwd)/skills/muse-multimedia ~/.omp/skills/muse-multimedia
```
Trong phiên làm việc của `omp`, bạn có thể giao nhiệm vụ trực tiếp:
> *"Hãy dùng lệnh `muse image` tạo cho tôi ảnh banner..."*  
> *"Hãy dùng `muse video` tạo video demo..."*

---

## 🔒 Bảo mật (Security & Privacy)

- File cookie cá nhân (`cookies.txt`, `~/.muse/cookies.txt`, `.env`) và các sản phẩm sinh ra (`*.png`, `*.mp4`) được đưa vào `.gitignore` nghiêm ngặt, **không bao giờ bị đẩy lên GitHub**.
- Kết nối được thực hiện cục bộ giữa máy của bạn và `muse.ai` qua phiên trình duyệt Playwright an toàn.

---

## 📄 Bản quyền (License)

Phát hành theo giấy phép [MIT License](LICENSE).
Tác giả: Duc Nguyen (nguyenanhducdeveloper@gmail.com).
