import sys
import os
import argparse
import time
from muse.config import load_cookies, save_cookies, get_cookie_path
from muse.core import MuseClient
from muse.server import run_server


def cmd_login(args):
    if args.manual:
        print("=" * 60)
        print("  🔑 Muse.ai Manual Cookie Setup")
        print("=" * 60)
        print("Hướng dẫn lấy cookies từ trình duyệt:")
        print("1. Mở https://muse.ai/ trên trình duyệt (đã đăng nhập).")
        print("2. Bấm F12 -> tab Network (hoặc Application -> Cookies).")
        print("3. Copy chuỗi Cookie header (bắt đầu bằng 'datr=...; hatch_sess=...').")
        print("=" * 60)
        try:
            raw = input("Dán chuỗi cookies vào đây: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nĐã hủy.")
            return

        if not raw:
            print("[!] Không có cookie nào được nhập.")
            return

        saved_path = save_cookies(raw, local=args.local)
        print(f"✅ Đã lưu cookies thành công vào: {saved_path}")
        return

    # Default: Automatic browser login
    print("=" * 60)
    print("  🚀 Muse.ai Auto-Login (Tự động mở trình duyệt & bắt cookies)")
    print("=" * 60)
    print("  1. Đang mở trình duyệt Google Chrome...")
    print("  2. Bạn chỉ cần đăng nhập tài khoản Muse.ai trên cửa sổ vừa mở.")
    print("  3. Ngay khi đăng nhập xong, hệ thống sẽ tự động lưu cookies!")
    print("=" * 60)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto("https://muse.ai/")
        except Exception:
            pass

        print("  ⏳ Đang đợi bạn đăng nhập trên trình duyệt...")
        captured = False

        for _ in range(300):  # 5 minutes timeout
            try:
                if page.is_closed():
                    print("\n[!] Cửa sổ trình duyệt đã bị đóng trước khi hoàn tất.")
                    break

                cookies = context.cookies(["https://muse.ai", "https://.muse.ai"])
                has_session = any(c.get("name") in ("hatch_sess", "hatch_vml") for c in cookies)

                if has_session:
                    time.sleep(2)
                    cookies = context.cookies(["https://muse.ai", "https://.muse.ai"])
                    cookie_str = "; ".join(
                        [f"{c['name']}={c['value']}" for c in cookies if c.get("name") and c.get("value")]
                    )
                    saved_path = save_cookies(cookie_str, local=args.local)
                    print(f"\n🎉 ĐĂNG NHẬP THÀNH CÔNG! Đã tự động bắt và lưu cookies vào: {saved_path}")
                    captured = True
                    break
            except Exception:
                pass
            time.sleep(1)

        try:
            browser.close()
        except Exception:
            pass

        if not captured:
            print("\n[!] Chưa phát hiện phiên đăng nhập.")
            print("💡 Mẹo: Bạn có thể dùng `muse login --manual` để dán cookies thủ công nếu muốn.")
        return

def cmd_status(args):
    print("Kiểm tra kết nối tới Muse.ai...")
    c = load_cookies()
    if not c:
        print("❌ Chưa cấu hình cookies. Hãy chạy `muse login` trước.")
        return
    try:
        client = MuseClient(headless=True)
        res = client.chat("Xin chào Muse, bạn có online không?")
        client.close()
        if res.get("ok"):
            print("✅ Kết nối thành công!")
            print(f"Phản hồi từ Muse: {res.get('reply')}")
        else:
            print("❌ Lỗi:", res.get("error"))
    except Exception as e:
        print("❌ Lỗi kết nối:", e)


def cmd_ask(args):
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        print("[!] Vui lòng nhập câu hỏi.")
        return
    client = MuseClient(headless=not args.headed)
    try:
        res = client.chat(prompt)
        if res.get("ok"):
            print(res.get("reply"))
        else:
            print(f"[!] Lỗi: {res.get('error')}", file=sys.stderr)
    finally:
        client.close()


def cmd_chat(args):
    print("=" * 60)
    print("  💬 Muse.ai Interactive Terminal Chat")
    print("  Gõ 'exit' hoặc 'quit' để thoát.")
    print("=" * 60)
    client = MuseClient(headless=not args.headed)
    try:
        while True:
            try:
                prompt = input("\nBạn > ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit"):
                break
            print("Muse đang trả lời...", end="", flush=True)
            res = client.chat(prompt)
            print("\r" + " " * 30 + "\r", end="")
            if res.get("ok"):
                print(f"Muse > {res.get('reply')}")
            else:
                print(f"[!] Lỗi: {res.get('error')}")
    finally:
        client.close()
    print("\nTạm biệt!")


def cmd_image(args):
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        print("[!] Vui lòng nhập prompt tạo ảnh.")
        return
    out = args.output or f"muse_{int(time.time())}.png"
    if args.ref:
        print(f"Đang yêu cầu Muse tạo ảnh từ ảnh mẫu '{args.ref}': '{prompt}'...")
    else:
        print(f"Đang yêu cầu Muse tạo ảnh: '{prompt}'...")
    client = MuseClient(headless=not args.headed)
    try:
        res = client.image(prompt, out_path=out, ref_image=args.ref)
        if res.get("ok"):
            print(f"🎉 Tạo ảnh thành công! Đã lưu tại: {res.get('path')}")
        else:
            print(f"[!] Lỗi: {res.get('error')}")
    finally:
        client.close()


def cmd_video(args):
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        print("[!] Vui lòng nhập prompt tạo video.")
        return
    out = args.output or f"muse_{int(time.time())}.mp4"
    print(f"Đang yêu cầu Muse tạo video: '{prompt}'...")
    client = MuseClient(headless=not args.headed)
    try:
        res = client.video(prompt, out_path=out, ref_image=args.ref)
        if res.get("ok"):
            print(f"🎉 Tạo video thành công! Đã lưu tại: {res.get('path')}")
        else:
            print(f"[!] Lỗi: {res.get('error')}")
    finally:
        client.close()


def cmd_serve(args):
    run_server(host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="muse",
        description="Muse CLI & OpenAI-Compatible Bridge for Muse.ai (Meta AI Personal Agent)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh khả dụng")

    # login
    p_login = subparsers.add_parser("login", help="Đăng nhập và tự động bắt cookies tài khoản Muse.ai")
    p_login.add_argument("--manual", action="store_true", help="Dán chuỗi cookies thủ công thay vì tự động mở trình duyệt")
    p_login.add_argument("--local", action="store_true", help="Lưu cookies vào thư mục hiện tại thay vì ~/.muse/")
    subparsers.add_parser("status", help="Kiểm tra trạng thái kết nối tới Muse.ai")

    # ask
    p_ask = subparsers.add_parser("ask", help="Gửi 1 câu hỏi nhanh và in kết quả ra terminal")
    p_ask.add_argument("prompt", nargs="+", help="Nội dung câu hỏi")
    p_ask.add_argument("--headed", action="store_true", help="Hiện cửa sổ trình duyệt")

    # chat
    p_chat = subparsers.add_parser("chat", help="Trò chuyện tương tác với Muse trực tiếp trong terminal")
    p_chat.add_argument("--headed", action="store_true", help="Hiện cửa sổ trình duyệt")

    # image
    p_image = subparsers.add_parser("image", help="Tạo ảnh từ văn bản (Text-to-Image)")
    p_image.add_argument("prompt", nargs="+", help="Mô tả bức ảnh cần tạo")
    p_image.add_argument("-r", "--ref", help="Đường dẫn file ảnh tham chiếu (Image-to-Image)")
    p_image.add_argument("-o", "--output", help="Đường dẫn file ảnh đầu ra (.png)")
    p_image.add_argument("--headed", action="store_true", help="Hiện cửa sổ trình duyệt")

    # video
    p_video = subparsers.add_parser("video", help="Tạo video từ văn bản hoặc ảnh tham chiếu")
    p_video.add_argument("prompt", nargs="+", help="Mô tả video cần tạo")
    p_video.add_argument("-r", "--ref", help="Đường dẫn file ảnh tham chiếu (Image-to-Video)")
    p_video.add_argument("-o", "--output", help="Đường dẫn file video đầu ra (.mp4)")
    p_video.add_argument("--headed", action="store_true", help="Hiện cửa sổ trình duyệt")

    # serve
    p_serve = subparsers.add_parser("serve", help="Khởi động OpenAI-Compatible API Bridge Server")
    p_serve.add_argument("-p", "--port", type=int, default=8765, help="Cổng server (mặc định: 8765)")
    p_serve.add_argument("-H", "--host", default="127.0.0.1", help="Địa chỉ bind (mặc định: 127.0.0.1)")

    args = parser.parse_args()

    dispatch = {
        "login": cmd_login,
        "status": cmd_status,
        "ask": cmd_ask,
        "chat": cmd_chat,
        "image": cmd_image,
        "video": cmd_video,
        "serve": cmd_serve,
    }

    if not args.command:
        parser.print_help()
        return

    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
