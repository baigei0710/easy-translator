"""
划词翻译悬浮插件 (Popover Translator)
------------------------------------
功能特点：
1. 划词速译：无需手动复制，选中文本后按下快捷键即可自动抓取选中的文本。
2. 剪贴板无痕保护：抓取选中文本后自动恢复用户原有的剪贴板内容，不污染剪贴板。
3. 免 Key 免费翻译 API：优先使用国内访问极速的有道开放 API，备用 MyMemory API。
4. 智能双向检测：自动识别中英文，进行中译英或英译中。
5. 90% 半透明悬浮窗：跟随鼠标指针位置弹框，按 Esc 键或点击右上角关闭。
"""

import tkinter as tk
import urllib.request
import urllib.parse
import json
import threading
import sys
import time

# 尝试导入 pynput 库用于监听全局快捷键和模拟系统按键
try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class HotkeyTranslatorApp:
    """
    划词翻译主应用类，包含 UI 界面构建、全局快捷键注册、划词抓取与接口翻译逻辑。
    """

    def __init__(self):
        # 1. 创建 Tkinter 主窗口（主根节点），并将其隐藏
        self.root = tk.Tk()
        self.root.withdraw()

        # 2. 创建真正的悬浮翻译窗口 (Toplevel 独立顶层窗口)
        self.trans_window = tk.Toplevel(self.root)
        self.trans_window.withdraw()             # 初始状态隐藏窗口
        self.trans_window.overrideredirect(True) # 移除系统原生标题栏和边框，打造极简卡片外观
        self.trans_window.attributes('-topmost', True) # 保持在所有窗口最前端
        self.trans_window.attributes('-alpha', 0.90)   # 设置 90% 不透明度 (10% 半透明效果)
        self.trans_window.configure(bg="#0f172a")       # 设置暗色深蓝背景颜色 (#0f172a)

        # 3. 初始化键盘控制器对象，用于模拟 Cmd+C / Ctrl+C
        if HAS_PYNPUT:
            self.keyboard_controller = Controller()

        # 4. 构建组件界面与注册快捷键监听
        self.setup_ui()
        self.setup_hotkey()

        # 5. 绑定键盘 Esc 键事件，实现一键隐藏翻译悬浮窗
        self.trans_window.bind("<Escape>", lambda e: self.hide_trans_window())

    def setup_ui(self):
        """
        初始化悬浮卡片的 UI 组件布局：顶部栏、原文预览框、翻译结果展示区域
        """
        # 外层主容器 Frame：添加天蓝色微弱边框 (highlightbackground) 与内边距
        frame = tk.Frame(
            self.trans_window, 
            bg="#0f172a", 
            highlightbackground="#38bdf8", 
            highlightthickness=1, 
            padx=12, 
            pady=10
        )
        frame.pack(fill="both", expand=True)

        # ---------------- 1. 顶部栏 (Top Bar) ----------------
        top_bar = tk.Frame(frame, bg="#0f172a")
        top_bar.pack(fill="x", pady=(0, 6))

        # 顶部标题提示 Label
        lbl = tk.Label(
            top_bar, 
            text="⚡ 半透明 划词速译 (Alt+Shift+T / Esc关闭)", 
            fg="#38bdf8", 
            bg="#0f172a", 
            font=("Arial", 10, "bold")
        )
        lbl.pack(side="left")

        # 右上角快捷关闭按钮 (✕)
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

        # ---------------- 2. 原文预览区域 (Source Preview Label) ----------------
        self.src_preview = tk.Label(
            frame, 
            text="选中文本后按下快捷键直接翻译...", 
            fg="#94a3b8", 
            bg="#1e293b", 
            font=("Arial", 10), 
            anchor="w", 
            justify="left", 
            padx=6, 
            pady=4, 
            wraplength=320  # 自动折行宽度限制为 320 像素
        )
        self.src_preview.pack(fill="x", pady=(0, 6))

        # ---------------- 3. 翻译结果展示区域 (Result Text Widget) ----------------
        self.result_text = tk.Text(
            frame, 
            width=36, 
            height=7, 
            bg="#090d16", 
            fg="#38bdf8", 
            bd=0, 
            font=("Arial", 11), 
            wrap="word"     # 按单词折行
        )
        self.result_text.pack(fill="both", expand=True)

    def setup_hotkey(self):
        """
        配置并启动全局快捷键监听器 (pynput.keyboard.GlobalHotKeys)
        支持 Alt+Shift+T 或 Cmd+Shift+X 两种组合键
        """
        if HAS_PYNPUT:
            def _on_trigger():
                # 快捷键触发时，将获取划词与翻译任务调度给 Tkinter 主线程处理
                self.root.after(0, self.get_selected_and_translate)

            try:
                # 注册全局组合按键
                self.hotkey_listener = keyboard.GlobalHotKeys({
                    '<alt>+<shift>+t': _on_trigger,
                    '<cmd>+<shift>+x': _on_trigger
                })
                # 启动后台守护线程进行监听
                self.hotkey_listener.start()
            except Exception as e:
                print(f"快捷键注册失败: {e}")
        else:
            print("未检测到 pynput 库，请运行: pip install pynput")

    def get_selected_and_translate(self):
        """
        核心方法：提取当前选中的文本，同时恢复保护原剪贴板内容
        步骤：1. 备份原剪贴板 -> 2. 模拟复制键 -> 3. 提取新文本 -> 4. 恢复原剪贴板 -> 5. 触发翻译
        """
        # 第一步：备份用户当前剪贴板中已保存的内容（若为空或异常则记为 None）
        try:
            old_clipboard = self.root.clipboard_get()
        except Exception:
            old_clipboard = None

        # 第二步：根据操作系统模拟按键组合复制文本 (macOS 使用 Cmd+C，Windows/Linux 使用 Ctrl+C)
        if HAS_PYNPUT:
            copy_key = Key.cmd if sys.platform == 'darwin' else Key.ctrl
            try:
                with self.keyboard_controller.pressed(copy_key):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
            except Exception:
                pass

        # 短暂休眠 120 毫秒，确保系统完成按键响应与剪贴板更新
        time.sleep(0.12)

        # 第三步：读取刚刚复制到剪贴板的选中文本
        try:
            selected_text = self.root.clipboard_get().strip()
        except Exception:
            selected_text = ""

        # 第四步：将剪贴板内容还原为备份的原内容，避免覆盖用户的历史剪贴板数据
        if old_clipboard is not None:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(old_clipboard)
                self.root.update() # 立即刷新系统剪贴板
            except Exception:
                pass

        # 若未成功抓取到有效文本，则不弹出窗口
        if not selected_text:
            return

        # 第五步：截取前 50 字更新原文预览区域
        preview = selected_text if len(selected_text) <= 50 else selected_text[:47] + "..."
        self.src_preview.config(text=f"原文: {preview}")

        # 第六步：获取鼠标指针的当前屏幕坐标 (x, y)，将悬浮窗定位在光标右下方 (+10, +10) 处
        x, y = self.root.winfo_pointerxy()
        self.trans_window.geometry(f"360x220+{x + 10}+{y + 10}")
        self.trans_window.deiconify() # 显示悬浮窗口

        # 第七步：开启后台线程请求翻译接口
        self.start_translation(selected_text)

    def hide_trans_window(self):
        """
        隐藏悬浮翻译窗口
        """
        self.trans_window.withdraw()

    def start_translation(self, text):
        """
        清空文本框并启动子线程异步调用网络翻译接口，避免界面卡顿
        """
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在翻译...")

        def _translate():
            translated = self.api_translate(text)
            # 在文本框中显示最终翻译结果
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, translated)

        # 以守护线程 (daemon thread) 异步运行网络请求
        threading.Thread(target=_translate, daemon=True).start()

    def api_translate(self, text):
        """
        免费在线翻译逻辑（双通道）：
        1. 首选国内有道开放词典 JSON API (响应极速，免密钥)
        2. 备选 MyMemory 免费翻译 API
        3. 支持智能检测语言（中译英 / 英译中）
        """
        # 1. 语言类型检测：判断文本中是否包含中文字符，决定翻译方向 (zh-CN|en 或 en|zh-CN)
        is_zh = any('\u4e00' <= c <= '\u9fff' for c in text)
        langpair = 'zh-CN|en' if is_zh else 'en|zh-CN'

        # 2. 优先通道：有道开放词典 API (适用于国内网络，无频率封禁限制)
        try:
            url = 'https://dict.youdao.com/jsonapi?q=' + urllib.parse.quote(text)
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
                # 情况 A: 返回句子翻译结果
                if 'fanyi' in data and data['fanyi'].get('tran'):
                    return data['fanyi'].get('tran')
                # 情况 B: 返回网络释义翻译结果
                if 'web_trans' in data and 'web-translation' in data['web_trans']:
                    return data['web_trans']['web-translation'][0]['trans'][0]['value']
                # 情况 C: 英译中词条释义
                if 'ec' in data and 'word' in data['ec']:
                    trs = [t['tr'][0]['l']['i'][0] for t in data['ec']['word'][0].get('trs', [])]
                    if trs:
                        return '; '.join(trs)
                # 情况 D: 中译英词条释义
                if 'ce' in data and 'word' in data['ce']:
                    trs = [t['tr'][0]['l']['i'][0] for t in data['ce']['word'][0].get('trs', [])]
                    if trs:
                        return '; '.join(trs)
        except Exception:
            pass  # 若有道接口请求超时或报错，自动进入备用通道

        # 3. 备用通道：MyMemory 免费翻译接口
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


# 程序入口
if __name__ == "__main__":
    app = HotkeyTranslatorApp()
    app.root.mainloop() # 启动 Tkinter 事件循环
