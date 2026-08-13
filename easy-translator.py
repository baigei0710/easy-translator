# --- macOS 下 pynput 兼容性补丁（解决 AXIsProcessTrusted 报错） ---
import sys
if sys.platform == 'darwin':
    try:
        import HIServices
        if not hasattr(HIServices, 'AXIsProcessTrusted'):
            import ctypes
            app_services = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
            ax_is_trusted = app_services.AXIsProcessTrusted
            ax_is_trusted.restype = ctypes.c_bool
            setattr(HIServices, 'AXIsProcessTrusted', lambda: ax_is_trusted())
    except Exception:
        try:
            import HIServices
            setattr(HIServices, 'AXIsProcessTrusted', lambda: True)
        except Exception:
            pass
# -----------------------------------------------------------------

import tkinter as tk
import urllib.request
import urllib.parse
import json
import threading
import sys
import time
import math
import subprocess

# 尝试导入 pynput 库用于全局快捷键、鼠标监听与键盘模拟
try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Controller as KeyboardController, Key
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class HotkeyTranslatorApp:
    def __init__(self):
        # 1. 创建并隐藏 Tkinter 根节点
        self.root = tk.Tk()
        self.root.withdraw()

        # 2. 创建 70% 半透明独立悬浮卡片窗口
        self.trans_window = tk.Toplevel(self.root)
        self.trans_window.withdraw()
        self.trans_window.overrideredirect(True)
        self.trans_window.attributes('-topmost', True)
        self.trans_window.attributes('-alpha', 0.70)
        self.trans_window.configure(bg="#0f172a")

        # 鼠标划词检测状态记录变量
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_click_time = 0

        if HAS_PYNPUT:
            self.keyboard_controller = KeyboardController()

        self.setup_ui()
        self.setup_listeners()

        # 绑定键盘 Esc 键快捷隐藏
        self.trans_window.bind("<Escape>", lambda e: self.hide_trans_window())

    def setup_ui(self):
        frame = tk.Frame(
            self.trans_window, 
            bg="#0f172a", 
            highlightbackground="#38bdf8", 
            highlightthickness=1, 
            padx=12, 
            pady=10
        )
        frame.pack(fill="both", expand=True)

        # 1. 顶部标题栏
        top_bar = tk.Frame(frame, bg="#0f172a")
        top_bar.pack(fill="x", pady=(0, 6))

        lbl = tk.Label(
            top_bar, 
            text="划词自动速译 (选中即译 / Esc关闭)", 
            fg="#38bdf8", 
            bg="#0f172a", 
            font=("Arial", 10, "bold")
        )
        lbl.pack(side="left")

        close_btn = tk.Button(
            top_bar, 
            text="✕", 
            command=self.hide_trans_window, 
            fg="#0f172a", 
            highlightbackground="#e2e8f0", 
            bd=0, 
            font=("Arial", 9, "bold")
        )
        close_btn.pack(side="right")

        # 2. 原文预览框
        self.src_preview = tk.Label(
            frame, 
            text="鼠标选中页面文字后释放即可直接翻译...", 
            fg="#94a3b8", 
            bg="#1e293b", 
            font=("Arial", 10), 
            anchor="w", 
            justify="left", 
            padx=6, 
            pady=4, 
            wraplength=320
        )
        self.src_preview.pack(fill="x", pady=(0, 6))

        # 3. 翻译结果展示框
        self.result_text = tk.Text(
            frame, 
            width=36, 
            height=7, 
            bg="#090d16", 
            fg="#38bdf8", 
            bd=0, 
            font=("Arial", 11), 
            wrap="word"
        )
        self.result_text.pack(fill="both", expand=True)

    def _get_clipboard(self):
        """macOS 原生安全读取剪贴板"""
        if sys.platform == 'darwin':
            try:
                return subprocess.check_output(['pbpaste'], text=True)
            except Exception:
                pass
        try:
            return self.root.clipboard_get()
        except Exception:
            return ""

    def _set_clipboard(self, text):
        """macOS 原生安全写入/清空剪贴板"""
        if sys.platform == 'darwin':
            try:
                subprocess.run(['pbcopy'], input=text, text=True)
                return
            except Exception:
                pass
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception:
            pass

    def setup_listeners(self):
        """配置并启动全局快捷键与鼠标划词监听器"""
        if not HAS_PYNPUT:
            return

        # A. 全局快捷键监听
        def _on_hotkey_trigger():
            self.root.after(100, self.get_selected_and_translate)

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<alt>+<shift>+t': _on_hotkey_trigger,
                '<cmd>+<shift>+x': _on_hotkey_trigger
            })
            self.hotkey_listener.start()
        except Exception:
            pass

        # B. 鼠标划词松开监听器
        def _on_mouse_click(x, y, button, pressed):
            if button != mouse.Button.left:
                return

            now = time.time()
            if pressed:
                self.drag_start_x = x
                self.drag_start_y = y
            else:
                distance = math.hypot(x - self.drag_start_x, y - self.drag_start_y)
                is_double_click = (now - self.last_click_time) < 0.35
                self.last_click_time = now

                # 拖拽超过 8 像素，或属于快速双击选词时，直接触发划词翻译
                if distance > 8 or is_double_click:
                    self.root.after(100, self.get_selected_and_translate)

        try:
            self.mouse_listener = mouse.Listener(on_click=_on_mouse_click)
            self.mouse_listener.start()
        except Exception:
            pass

    def get_selected_and_translate(self):
        """核心划词抓取与剪贴板保护逻辑"""
        self.hide_trans_window()

        # 1. 备份用户原有的剪贴板内容
        old_clipboard = self._get_clipboard()

        # 2. 清空剪贴板，用于精确检测 Cmd+C 是否成功写入了新文本
        self._set_clipboard("")

        # 3. 模拟系统复制快捷键 (Ctrl+C / Cmd+C)
        if HAS_PYNPUT:
            copy_key = Key.cmd if sys.platform == 'darwin' else Key.ctrl
            try:
                with self.keyboard_controller.pressed(copy_key):
                    self.keyboard_controller.press('c')
                    time.sleep(0.05)
                    self.keyboard_controller.release('c')
            except Exception:
                pass

        # 4. 【核心修复】：轮询等待目标软件响应 Cmd+C，最多等待 0.25 秒
        selected_text = ""
        for _ in range(5):
            time.sleep(0.05)
            text = self._get_clipboard().strip()
            if text:  # 读到了新复制的内容，立即退出等待
                selected_text = text
                break

        # 5. 无痕还原用户原本的剪贴板内容
        if old_clipboard:
            self._set_clipboard(old_clipboard)

        # 6. 未抓取到新文本（说明 Cmd+C 失败或未选中文字）时拦截退出
        if not selected_text:
            print("[DEBUG] 未抓取到新选中文本（Cmd+C 响应超时或未选中文字）")
            return

        preview = selected_text if len(selected_text) <= 50 else selected_text[:47] + "..."
        self.src_preview.config(text=preview)

        # 调整悬浮窗位置并显示
        x, y = self.root.winfo_pointerxy()
        self.trans_window.geometry(f"360x220+{x + 10}+{y + 10}")
        self.trans_window.deiconify()
        self.trans_window.lift()

        self.start_translation(selected_text)

    def hide_trans_window(self):
        self.trans_window.withdraw()

    def start_translation(self, text):
        """启动后台线程进行翻译，避免阻塞 UI 主线程"""
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在翻译...")

        def _translate():
            translated = self.api_translate(text)
            self.root.after(0, lambda: self.update_result_ui(translated))

        threading.Thread(target=_translate, daemon=True).start()

    def update_result_ui(self, translated_text):
        """专用 UI 更新函数：运行在主线程中，用于安全地向文本框写入内容"""
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, translated_text)
        print(f"[DEBUG] 翻译窗口已刷新，当前结果: '{translated_text}'")

    def api_translate(self, text):
        is_zh = any('\u4e00' <= c <= '\u9fff' for c in text)
        langpair = 'zh-CN|en' if is_zh else 'en|zh-CN'

        # 1. 优先通道：有道开放 API
        try:
            url = 'https://dict.youdao.com/jsonapi?q=' + urllib.parse.quote(text)
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                result_str = None
                if 'fanyi' in data and data['fanyi'].get('tran'):
                    result_str = data['fanyi'].get('tran')
                elif 'web_trans' in data and 'web-translation' in data['web_trans']:
                    result_str = data['web_trans']['web-translation'][0]['trans'][0]['value']
                elif 'ec' in data and 'word' in data['ec']:
                    trs = [t['tr'][0]['l']['i'][0] for t in data['ec']['word'][0].get('trs', [])]
                    if trs:
                        result_str = '; '.join(trs)
                elif 'ce' in data and 'word' in data['ce']:
                    trs = [t['tr'][0]['l']['i'][0] for t in data['ce']['word'][0].get('trs', [])]
                    if trs:
                        result_str = '; '.join(trs)
                
                if result_str:
                    return result_str
        except Exception:
            pass

        # 2. 备用通道：MyMemory API
        try:
            url = f'https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={langpair}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0'
            })
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                res = data.get('responseData', {}).get('translatedText')
                if res:
                    return res
        except Exception as e:
            return f"翻译失败: {e}"

        return "翻译失败，请检查网络状态。"


if __name__ == "__main__":
    app = HotkeyTranslatorApp()
    app.root.mainloop()
