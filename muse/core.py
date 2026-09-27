import os
import sys
import time
import base64
import threading
import queue
from muse.config import load_cookies, parse_cookie_list


class MuseClient:
    def __init__(self, headless=True, cookies_str=None):
        self.headless = headless
        self.cookies_str = cookies_str or load_cookies()
        if not self.cookies_str:
            raise ValueError(
                "No Muse.ai cookies found!\n"
                "Please run `muse login` or set MUSE_COOKIES environment variable, "
                "or place cookies in ~/.muse/cookies.txt"
            )
        self.cmd_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.is_ready = False
        self._init_event = threading.Event()
        self._init_error = None
        self._init_event.wait(timeout=45)
        if self._init_error:
            raise RuntimeError(f"Failed to initialize Muse session: {self._init_error}")

    def _worker_loop(self):
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 850},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
                )
                context.add_cookies(parse_cookie_list(self.cookies_str))
                page = context.new_page()

                try:
                    page.goto("https://muse.ai/", wait_until="domcontentloaded", timeout=45000)
                    time.sleep(3)
                    # If name onboarding button exists, click Muse
                    muse_btn = page.locator('button:has-text("Muse")').first
                    if muse_btn.is_visible() and muse_btn.is_enabled():
                        muse_btn.click()
                        time.sleep(1)
                    self.is_ready = True
                    self._init_event.set()
                except Exception as e:
                    self._init_error = str(e)
                    self._init_event.set()
                    return

                while True:
                    task = self.cmd_queue.get()
                    if not task:
                        break
                    cmd = task.get("cmd")
                    resp_q = task.get("resp")

                    try:
                        if cmd == "chat":
                            prompt = task.get("prompt", "")
                            reply = self._send_and_wait_reply(page, prompt, timeout=task.get("timeout", 60))
                            resp_q.put({"ok": True, "reply": reply})

                        elif cmd == "generate_image":
                            prompt = task.get("prompt", "")
                            out_path = task.get("out_path")
                            ref_image = task.get("ref_image")
                            result = self._handle_image_generation(page, prompt, out_path, ref_image=ref_image, timeout=task.get("timeout", 90))
                            resp_q.put(result)

                        elif cmd == "generate_video":
                            prompt = task.get("prompt", "")
                            out_path = task.get("out_path")
                            ref_image = task.get("ref_image")
                            result = self._handle_video_generation(page, prompt, out_path, ref_image, timeout=task.get("timeout", 120))
                            resp_q.put(result)

                        elif cmd == "close":
                            resp_q.put({"ok": True})
                            break
                    except Exception as e:
                        resp_q.put({"ok": False, "error": str(e)})

                browser.close()
        except Exception as e:
            self._init_error = str(e)
            self._init_event.set()

    def _send_and_wait_reply(self, page, prompt, timeout=60):
        textarea = page.locator('textarea[placeholder="Message"], textarea').first
        if not textarea.is_visible():
            time.sleep(1)

        p_before = len(page.locator("p").all())
        textarea.fill(prompt)
        time.sleep(0.15)
        textarea.press("Enter")

        time.sleep(1.5)
        last_text = ""
        stable_count = 0

        # Poll until assistant response stabilizes
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.5)
            # Check latest assistant message body or p tags
            asst_msgs = page.locator('[data-hatch-assistant-message-body="true"]').all()
            if asst_msgs:
                cur_text = asst_msgs[-1].inner_text().strip()
                if cur_text == last_text and len(cur_text) > 0:
                    stable_count += 1
                    if stable_count >= 3:
                        return cur_text
                else:
                    last_text = cur_text
                    stable_count = 0
            else:
                paragraphs = page.locator("p").all_inner_texts()
                if len(paragraphs) > p_before:
                    cur_text = paragraphs[-1].strip()
                    if cur_text == last_text and len(cur_text) > 0:
                        stable_count += 1
                        if stable_count >= 3:
                            return cur_text
                    else:
                        last_text = cur_text
                        stable_count = 0

        return last_text or "No response from Muse (timeout)"

    def _handle_image_generation(self, page, prompt, out_path=None, ref_image=None, timeout=90):
        out_path = out_path or f"muse_image_{int(time.time())}.png"

        # If reference image provided, upload it first
        if ref_image and os.path.exists(ref_image):
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(os.path.abspath(ref_image))
            time.sleep(2)

        textarea = page.locator('textarea[placeholder="Message"], textarea').first
        textarea.fill(prompt)
        time.sleep(0.15)
        textarea.press("Enter")
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            # Check for activity item indicating image generated
            act_btns = page.locator('button:has-text("Generated"), button:has-text("image")').all()
            for b in act_btns:
                txt = b.inner_text()
                if "image" in txt.lower() and ("generated" in txt.lower() or "save" in txt.lower()):
                    b.click()
                    time.sleep(2)
                    # Check dialog
                    dialog = page.locator('[role="dialog"]').first
                    if dialog.is_visible():
                        img_el = dialog.locator('img').first
                        if img_el.is_visible():
                            img_el.screenshot(path=out_path)
                            page.keyboard.press("Escape")
                            return {"ok": True, "path": os.path.abspath(out_path), "type": "image"}
                    page.keyboard.press("Escape")

            # Also check if text confirmation came back
            asst_msgs = page.locator('[data-hatch-assistant-message-body="true"]').all()
            if asst_msgs and "Xong rồi" in asst_msgs[-1].inner_text():
                # Screenshot the chat area as image
                page.screenshot(path=out_path)
                return {"ok": True, "path": os.path.abspath(out_path), "type": "image", "note": "Captured from canvas/chat"}

        return {"ok": False, "error": "Image generation timeout"}

    def _handle_video_generation(self, page, prompt, out_path=None, ref_image=None, timeout=120):
        out_path = out_path or f"muse_video_{int(time.time())}.mp4"

        # If reference image provided, upload it first
        if ref_image and os.path.exists(ref_image):
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(os.path.abspath(ref_image))
            time.sleep(2)

        textarea = page.locator('textarea[placeholder="Message"], textarea').first
        textarea.fill(prompt)
        time.sleep(0.2)
        textarea.press("Enter")

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(3)
            # Check activity panel for video completion
            act_btns = page.locator('button:has-text("video"), button:has-text("Video")').all()
            for b in act_btns:
                txt = b.inner_text()
                if ("generated" in txt.lower() or "saved" in txt.lower() or "complete" in txt.lower()) and "video" in txt.lower():
                    b.click()
                    time.sleep(2)
                    dl_btn = page.locator('button[aria-label="Download video"]').first
                    if dl_btn.is_visible():
                        try:
                            with page.expect_download(timeout=15000) as download_info:
                                dl_btn.click(force=True)
                            download = download_info.value
                            download.save_as(os.path.abspath(out_path))
                            page.keyboard.press("Escape")
                            return {"ok": True, "path": os.path.abspath(out_path), "type": "video"}
                        except Exception:
                            pass
                    page.keyboard.press("Escape")

            # Check if assistant text said completed
            asst_msgs = page.locator('[data-hatch-assistant-message-body="true"]').all()
            if asst_msgs and any("Xong rồi" in m.inner_text() and "video" in m.inner_text().lower() for m in asst_msgs[-2:]):
                time.sleep(2)
                # Look for download button anywhere
                dl_btn = page.locator('button[aria-label="Download video"]').first
                if dl_btn.is_visible():
                    try:
                        with page.expect_download(timeout=15000) as download_info:
                            dl_btn.click(force=True)
                        download = download_info.value
                        download.save_as(os.path.abspath(out_path))
                        return {"ok": True, "path": os.path.abspath(out_path), "type": "video"}
                    except Exception:
                        pass

        return {"ok": False, "error": "Video generation timeout or still processing in Muse Library"}

    def chat(self, prompt, timeout=60):
        q = queue.Queue()
        self.cmd_queue.put({"cmd": "chat", "prompt": prompt, "timeout": timeout, "resp": q})
        return q.get(timeout=timeout + 5)

    def image(self, prompt, out_path=None, ref_image=None, timeout=90):
        q = queue.Queue()
        self.cmd_queue.put({"cmd": "generate_image", "prompt": prompt, "out_path": out_path, "ref_image": ref_image, "timeout": timeout, "resp": q})
        return q.get(timeout=timeout + 5)

    def video(self, prompt, out_path=None, ref_image=None, timeout=120):
        q = queue.Queue()
        self.cmd_queue.put({"cmd": "generate_video", "prompt": prompt, "out_path": out_path, "ref_image": ref_image, "timeout": timeout, "resp": q})
        return q.get(timeout=timeout + 5)

    def close(self):
        q = queue.Queue()
        self.cmd_queue.put({"cmd": "close", "resp": q})
        try:
            return q.get(timeout=5)
        except Exception:
            return {"ok": True}
