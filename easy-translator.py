"""
Easy Translator - 主程序与界面模块 (UI)
--------------------------------------
包含：
1. 划词速译悬浮窗 (PopoverWindow)
2. 设置与日常翻译主窗口 (MainWindow)
3. 应用程序主入口 (HotkeyTranslatorApp)
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import sys

# 导入核心功能模块（API、剪贴板、配置与事件监听）
from translator_core import (
    config,
    LANGUAGES,
    TARGET_LANGUAGES,
    api_translate,
    get_clipboard_text,
    set_clipboard_text,
    InputListenerManager
)


class PopoverWindow:
    """半透明圆角划词翻译悬浮卡片"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.90)

        # 区分平台背景透明色
        if sys.platform == 'darwin':
            try:
                self.window.config(bg='systemTransparent')
            except Exception:
                self.window.config(bg='#0f172a')
        else:
            self.window.config(bg='#0f172a')

        self.setup_ui()
        self.window.bind("<Escape>", lambda e: self.hide())

    def setup_ui(self):
        bg_color = 'systemTransparent' if sys.platform == 'darwin' else '#0f172a'

        # Canvas 容器负责绘制圆角与边框
        self.canvas = tk.Canvas(
            self.window, 
            bg=bg_color, 
            bd=0, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._redraw_card)

        # 结果文本框
        self.result_text = tk.Text(
            self.canvas, 
            bg="#090d16", 
            fg="#f8fafc",
            insertbackground="#ffffff",
            bd=0, 
            font=("Arial", 11), 
            wrap="word",
            highlightthickness=0
        )
        self.text_window_id = self.canvas.create_window(
            10, 10, anchor="nw", window=self.result_text
        )

    def _create_rounded_polygon(self, x1, y1, x2, y2, radius=12, **kwargs):
        points = [
            x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1, x2, y1,
            x2, y1 + radius, x2, y1 + radius, x2, y2 - radius, x2, y2 - radius, x2, y2,
            x2 - radius, y2, x2 - radius, y2, x1 + radius, y2, x1 + radius, y2, x1, y2,
            x1, y2 - radius, x1, y2 - radius, x1, y1 + radius, x1, y1 + radius, x1, y1
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _redraw_card(self, event):
        self.canvas.delete("card_shape")
        w, h = event.width, event.height
        # 外层白色圆角边框
        self._create_rounded_polygon(0, 0, w, h, radius=14, fill="#ffffff", tags="card_shape")
        # 内层暗色背景
        self._create_rounded_polygon(1.5, 1.5, w - 1.5, h - 1.5, radius=12.5, fill="#090d16", tags="card_shape")
        self.canvas.itemconfig(self.text_window_id, width=max(w - 20, 10), height=max(h - 20, 10))

    def show(self, x, y, text):
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在翻译...")

        # 定位并显示
        self.window.geometry(f"320x140+{x + 10}+{y + 10}")
        self.window.deiconify()
        self.window.lift()

        # 异步翻译
        def _do_trans():
            res = api_translate(text)
            self.root.after(0, lambda: self._update_result(res))

        threading.Thread(target=_do_trans, daemon=True).start()

    def _update_result(self, translated_text):
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, translated_text)

    def hide(self):
        self.window.withdraw()

    def is_visible(self):
        return self.window.state() == "normal"


class MainWindow:
    """主窗口：包含日常翻译与偏好设置两大功能页"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.title("Easy Translator")
        self.window.geometry("620x520")
        self.window.minsize(520, 420)
        self.window.configure(bg="#0f172a")

        # 窗口关闭事件拦截
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.bind("<Escape>", lambda e: self.hide())

        self.current_tab = "trans" # 'trans' 或 'settings'
        self.setup_ui()

    def setup_ui(self):
        # 1. 顶部导航栏 (Tab 切换区)
        nav_bar = tk.Frame(self.window, bg="#0f172a", padx=16, pady=12)
        nav_bar.pack(fill="x")

        # 品牌图标与标题
        app_title = tk.Label(
            nav_bar, 
            text="Easy Translator", 
            fg="#38bdf8", 
            bg="#0f172a", 
            font=("Arial", 14, "bold")
        )
        app_title.pack(side="left")

        # 标签页按钮容器
        btn_box = tk.Frame(nav_bar, bg="#1e293b", padx=2, pady=2)
        btn_box.pack(side="right")

        self.tab_trans_btn = tk.Button(
            btn_box, 
            text="🌐 文本翻译", 
            font=("Arial", 10, "bold"),
            bd=0, 
            padx=12, 
            pady=4,
            command=lambda: self.switch_tab("trans")
        )
        self.tab_trans_btn.pack(side="left")

        self.tab_settings_btn = tk.Button(
            btn_box, 
            text="⚙️ 偏好设置", 
            font=("Arial", 10, "bold"),
            bd=0, 
            padx=12, 
            pady=4,
            command=lambda: self.switch_tab("settings")
        )
        self.tab_settings_btn.pack(side="left")

        # 分割线
        sep = tk.Frame(self.window, bg="#1e293b", height=1)
        sep.pack(fill="x")

        # 2. 内容主容器
        self.content_container = tk.Frame(self.window, bg="#0f172a", padx=16, pady=12)
        self.content_container.pack(fill="both", expand=True)

        # 创建两个独立的页面 Frame
        self.trans_page = tk.Frame(self.content_container, bg="#0f172a")
        self.settings_page = tk.Frame(self.content_container, bg="#0f172a")

        self.build_trans_page()
        self.build_settings_page()

        # 默认展示日常翻译页面
        self.switch_tab("trans")

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        if tab_name == "trans":
            self.settings_page.pack_forget()
            self.trans_page.pack(fill="both", expand=True)
            self.tab_trans_btn.config(bg="#38bdf8", fg="#0f172a", highlightbackground="#38bdf8")
            self.tab_settings_btn.config(bg="#1e293b", fg="#94a3b8", highlightbackground="#1e293b")
        else:
            self.trans_page.pack_forget()
            self.settings_page.pack(fill="both", expand=True)
            self.tab_settings_btn.config(bg="#38bdf8", fg="#0f172a", highlightbackground="#38bdf8")
            self.tab_trans_btn.config(bg="#1e293b", fg="#94a3b8", highlightbackground="#1e293b")

    # ---------------- 日常翻译页面 ----------------
    def build_trans_page(self):
        # A. 语言选择工具栏
        lang_bar = tk.Frame(self.trans_page, bg="#0f172a")
        lang_bar.pack(fill="x", pady=(0, 8))

        # 源语言
        tk.Label(lang_bar, text="源语言:", fg="#94a3b8", bg="#0f172a", font=("Arial", 10)).pack(side="left", padx=(0, 4))
        self.src_lang_cb = ttk.Combobox(
            lang_bar, 
            values=list(LANGUAGES.keys()), 
            state="readonly", 
            width=10, 
            font=("Arial", 10)
        )
        self.src_lang_cb.set("自动检测")
        self.src_lang_cb.pack(side="left")

        # 交换语言按钮
        swap_btn = tk.Button(
            lang_bar, 
            text=" ⇄ ", 
            command=self.swap_languages, 
            bg="#1e293b", 
            fg="#38bdf8", 
            bd=0, 
            font=("Arial", 10, "bold")
        )
        swap_btn.pack(side="left", padx=8)

        # 目标语言
        tk.Label(lang_bar, text="目标语言:", fg="#94a3b8", bg="#0f172a", font=("Arial", 10)).pack(side="left", padx=(0, 4))
        self.tgt_lang_cb = ttk.Combobox(
            lang_bar, 
            values=list(TARGET_LANGUAGES.keys()), 
            state="readonly", 
            width=10, 
            font=("Arial", 10)
        )
        self.tgt_lang_cb.set("中文 (简体)")
        self.tgt_lang_cb.pack(side="left")

        # 翻译状态标签
        self.status_lbl = tk.Label(lang_bar, text="就绪", fg="#64748b", bg="#0f172a", font=("Arial", 9))
        self.status_lbl.pack(side="right")

        # B. 原文输入框
        src_frame = tk.LabelFrame(
            self.trans_page, 
            text=" 输入原文 (支持快捷键 Cmd+Enter 快速翻译) ", 
            fg="#94a3b8", 
            bg="#0f172a", 
            font=("Arial", 9),
            padx=6, 
            pady=4
        )
        src_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.src_text = tk.Text(
            src_frame, 
            height=6, 
            bg="#1e293b", 
            fg="#f8fafc", 
            insertbackground="#ffffff", 
            bd=0, 
            font=("Arial", 11), 
            wrap="word"
        )
        self.src_text.pack(fill="both", expand=True)
        self.src_text.bind("<Command-Return>", lambda e: self.do_manual_translate())
        self.src_text.bind("<Control-Return>", lambda e: self.do_manual_translate())

        # C. 操作按钮区
        btn_bar = tk.Frame(self.trans_page, bg="#0f172a")
        btn_bar.pack(fill="x", pady=(0, 8))

        trans_btn = tk.Button(
            btn_bar, 
            text="⚡ 立即翻译", 
            command=self.do_manual_translate, 
            bg="#38bdf8", 
            fg="#0f172a", 
            bd=0, 
            font=("Arial", 10, "bold"), 
            padx=14, 
            pady=4
        )
        trans_btn.pack(side="left")

        copy_btn = tk.Button(
            btn_bar, 
            text="📋 复制译文", 
            command=self.copy_result, 
            bg="#1e293b", 
            fg="#e2e8f0", 
            bd=0, 
            font=("Arial", 9), 
            padx=10, 
            pady=4
        )
        copy_btn.pack(side="left", padx=8)

        clear_btn = tk.Button(
            btn_bar, 
            text="🗑️ 清空", 
            command=self.clear_all, 
            bg="#1e293b", 
            fg="#e2e8f0", 
            bd=0, 
            font=("Arial", 9), 
            padx=10, 
            pady=4
        )
        clear_btn.pack(side="left")

        # D. 译文输出框
        res_frame = tk.LabelFrame(
            self.trans_page, 
            text=" 翻译结果 ", 
            fg="#94a3b8", 
            bg="#0f172a", 
            font=("Arial", 9),
            padx=6, 
            pady=4
        )
        res_frame.pack(fill="both", expand=True)

        self.res_text = tk.Text(
            res_frame, 
            height=6, 
            bg="#090d16", 
            fg="#38bdf8", 
            insertbackground="#ffffff", 
            bd=0, 
            font=("Arial", 11), 
            wrap="word"
        )
        self.res_text.pack(fill="both", expand=True)

    def swap_languages(self):
        src_name = self.src_lang_cb.get()
        tgt_name = self.tgt_lang_cb.get()

        if src_name == "自动检测":
            self.src_lang_cb.set(tgt_name)
            self.tgt_lang_cb.set("英语" if tgt_name == "中文 (简体)" else "中文 (简体)")
        else:
            if src_name in TARGET_LANGUAGES:
                self.tgt_lang_cb.set(src_name)
            self.src_lang_cb.set(tgt_name)

    def do_manual_translate(self):
        text = self.src_text.get("1.0", tk.END).strip()
        if not text:
            return

        src_code = LANGUAGES.get(self.src_lang_cb.get(), "auto")
        tgt_code = TARGET_LANGUAGES.get(self.tgt_lang_cb.get(), "zh-CN")

        self.status_lbl.config(text="正在翻译...", fg="#38bdf8")
        self.res_text.delete("1.0", tk.END)
        self.res_text.insert(tk.END, "正在翻译中...")

        start_time = time.time()

        def _translate_worker():
            res = api_translate(text, source_lang=src_code, target_lang=tgt_code)
            cost = time.time() - start_time
            self.root.after(0, lambda: self._on_manual_trans_finished(res, cost))

        threading.Thread(target=_translate_worker, daemon=True).start()

    def _on_manual_trans_finished(self, result_text, cost):
        self.res_text.delete("1.0", tk.END)
        self.res_text.insert(tk.END, result_text)
        self.status_lbl.config(text=f"翻译完成 ({cost:.2f}s)", fg="#4ade80")

    def copy_result(self):
        result = self.res_text.get("1.0", tk.END).strip()
        if result:
            set_clipboard_text(result, self.root)
            self.status_lbl.config(text="译文已复制到剪贴板", fg="#38bdf8")

    def clear_all(self):
        self.src_text.delete("1.0", tk.END)
        self.res_text.delete("1.0", tk.END)
        self.status_lbl.config(text="就绪", fg="#64748b")

    # ---------------- 设置页面 ----------------
    def build_settings_page(self):
        # 卡片 1：划词翻译语言偏好设置
        card1 = tk.LabelFrame(
            self.settings_page, 
            text=" 划词速译偏好设置 ", 
            fg="#38bdf8", 
            bg="#0f172a", 
            font=("Arial", 11, "bold"),
            padx=14, 
            pady=12
        )
        card1.pack(fill="x", pady=(0, 14))

        # “自动”复选框变量
        self.auto_lang_var = tk.BooleanVar(value=config.popover_auto_lang)

        auto_cb = tk.Checkbutton(
            card1, 
            text="启用自动检测语言（由软件自主决定目标语言，中英互译）", 
            variable=self.auto_lang_var, 
            command=self.on_auto_lang_toggle,
            fg="#f8fafc", 
            bg="#0f172a", 
            selectcolor="#1e293b", 
            activebackground="#0f172a",
            activeforeground="#38bdf8",
            font=("Arial", 10, "bold")
        )
        auto_cb.pack(anchor="w", pady=(0, 4))

        tip_lbl = tk.Label(
            card1, 
            text="开启后：划词检测到中文自动译为英文，检测到英文及其他语言自动译为中文。", 
            fg="#94a3b8", 
            bg="#0f172a", 
            font=("Arial", 9)
        )
        tip_lbl.pack(anchor="w", padx=(24, 0), pady=(0, 10))

        # 手动选择固定语言行
        manual_frame = tk.Frame(card1, bg="#0f172a")
        manual_frame.pack(anchor="w", padx=(24, 0), fill="x")

        tk.Label(
            manual_frame, 
            text="固定目标语言：", 
            fg="#e2e8f0", 
            bg="#0f172a", 
            font=("Arial", 10)
        ) .pack(side="left")

        # 获取默认目标语言对应的中文名称
        default_name = "中文 (简体)"
        for k, v in TARGET_LANGUAGES.items():
            if v == config.popover_target_lang:
                default_name = k
                break

        self.popover_lang_cb = ttk.Combobox(
            manual_frame, 
            values=list(TARGET_LANGUAGES.keys()), 
            state="disabled" if config.popover_auto_lang else "readonly", 
            width=12, 
            font=("Arial", 10)
        )
        self.popover_lang_cb.set(default_name)
        self.popover_lang_cb.pack(side="left", padx=(4, 0))
        self.popover_lang_cb.bind("<<ComboboxSelected>>", self.on_popover_lang_selected)

        # 卡片 2：快捷键参考卡片
        card2 = tk.LabelFrame(
            self.settings_page, 
            text=" 快捷键速查 ", 
            fg="#38bdf8", 
            bg="#0f172a", 
            font=("Arial", 11, "bold"),
            padx=14, 
            pady=12
        )
        card2.pack(fill="x")

        shortcuts = [
            ("划词悬浮速译", "鼠标划词拖选松开 / Alt + Shift + T / Cmd + Shift + X"),
            ("打开 / 隐藏主窗口", "Alt + Shift + M / Cmd + Shift + M"),
            ("快速关闭弹窗 / 窗口", "Esc 键"),
            ("主窗口快速翻译", "Cmd + Enter (macOS) / Ctrl + Enter")
        ]

        for idx, (title, key) in enumerate(shortcuts):
            row = tk.Frame(card2, bg="#0f172a")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"• {title}:", fg="#e2e8f0", bg="#0f172a", font=("Arial", 10, "bold"), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=key, fg="#38bdf8", bg="#0f172a", font=("Arial", 10)).pack(side="left")

    def on_auto_lang_toggle(self):
        """勾选/取消勾选‘自动’选项时的联动逻辑"""
        is_auto = self.auto_lang_var.get()
        config.popover_auto_lang = is_auto

        if is_auto:
            # 勾选自动后：禁用手动选择下拉列表
            self.popover_lang_cb.config(state="disabled")
        else:
            # 取消自动后：解除禁用，允许用户自主选择固定语言
            self.popover_lang_cb.config(state="readonly")
            # 同步更新当前选中的语言
            selected_name = self.popover_lang_cb.get()
            config.popover_target_lang = TARGET_LANGUAGES.get(selected_name, "zh-CN")

    def on_popover_lang_selected(self, event):
        selected_name = self.popover_lang_cb.get()
        config.popover_target_lang = TARGET_LANGUAGES.get(selected_name, "zh-CN")

    def show(self):
        if self.window.state() == "withdrawn" or self.window.state() == "iconic":
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            w, h = 620, 520
            x = (screen_width - w) // 2
            y = (screen_height - h) // 2
            self.window.geometry(f"{w}x{h}+{x}+{y}")

        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def hide(self):
        self.window.withdraw()

    def toggle(self):
        if self.window.state() == "normal":
            self.hide()
        else:
            self.show()

    def is_visible(self):
        return self.window.state() == "normal"


class HotkeyTranslatorApp:
    """应用程序主控制器：协调 UI 与全局输入监听"""
    def __init__(self):
        # 1. 隐藏 Tkinter 根节点
        self.root = tk.Tk()
        self.root.withdraw()

        # 2. 构建悬浮卡片与主窗口
        self.popover = PopoverWindow(self.root)
        self.main_window = MainWindow(self.root)

        # 3. 注册并启动全局监听器
        self.listener_mgr = InputListenerManager(
            on_popover_trigger=lambda: self.root.after(100, self.get_selected_and_translate),
            on_main_window_toggle=lambda: self.root.after(0, self.main_window.toggle),
            is_inside_window_func=self.is_pointer_inside_windows
        )
        self.listener_mgr.start()

        # 4. 程序启动时直接显示主窗口
        self.main_window.show()

    def is_pointer_inside_windows(self, x, y):
        """判断光标是否在任一程序窗口内，防止误触划词"""
        for win_obj in (self.popover.window, self.main_window.window):
            if win_obj.state() == "normal":
                try:
                    wx = win_obj.winfo_rootx()
                    wy = win_obj.winfo_rooty()
                    ww = win_obj.winfo_width()
                    wh = win_obj.winfo_height()
                    if wx <= x <= wx + ww and wy <= y <= wy + wh:
                        return True
                except Exception:
                    pass
        return False

    def get_selected_and_translate(self):
        """划词抓取与剪贴板保护逻辑"""
        self.popover.hide()

        # A. 备份原剪贴板
        old_clipboard = get_clipboard_text(self.root)
        set_clipboard_text("", self.root)

        # B. 模拟系统复制快捷键
        self.listener_mgr.simulate_copy()

        # C. 轮询读取新复制内容
        selected_text = ""
        for _ in range(5):
            time.sleep(0.05)
            text = get_clipboard_text(self.root).strip()
            if text:
                selected_text = text
                break

        # D. 恢复原剪贴板
        if old_clipboard:
            set_clipboard_text(old_clipboard, self.root)

        if not selected_text:
            return

        # E. 在光标位置显示悬浮翻译
        x, y = self.root.winfo_pointerxy()
        self.popover.show(x, y, selected_text)


if __name__ == "__main__":
    app = HotkeyTranslatorApp()
    app.root.mainloop()
