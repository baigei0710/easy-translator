"""
Easy Translator - 主程序与界面模块 (UI)
--------------------------------------
浅色系极简设计 (Light Modern Theme with Rounded UI)
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
    """浅色系半透明圆角划词翻译悬浮卡片"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)

        # 平台透明背景支持
        if sys.platform == 'darwin':
            try:
                self.window.config(bg='systemTransparent')
            except Exception:
                self.window.config(bg='#f8fafc')
        else:
            self.window.config(bg='#f8fafc')

        self.setup_ui()
        self.window.bind("<Escape>", lambda e: self.hide())

    def setup_ui(self):
        bg_color = 'systemTransparent' if sys.platform == 'darwin' else '#f8fafc'

        # Canvas 容器负责绘制圆角卡片与柔和边框
        self.canvas = tk.Canvas(
            self.window, 
            bg=bg_color, 
            bd=0, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._redraw_card)

        # 结果展示文本框（浅色纯白底 + 典雅深灰字）
        self.result_text = tk.Text(
            self.canvas, 
            bg="#ffffff", 
            fg="#0f172a",
            insertbackground="#2563eb",
            bd=0, 
            font=("Arial", 11), 
            wrap="word",
            highlightthickness=0
        )
        self.text_window_id = self.canvas.create_window(
            12, 12, anchor="nw", window=self.result_text
        )

    def _create_rounded_polygon(self, x1, y1, x2, y2, radius=12, **kwargs):
        """绘制平滑圆角多边形"""
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
        # 外层细腻浅灰阴影边框
        self._create_rounded_polygon(0, 0, w, h, radius=14, fill="#cbd5e1", tags="card_shape")
        # 内层纯白圆角卡片
        self._create_rounded_polygon(1.5, 1.5, w - 1.5, h - 1.5, radius=12.5, fill="#ffffff", tags="card_shape")
        self.canvas.itemconfig(self.text_window_id, width=max(w - 24, 10), height=max(h - 24, 10))

    def show(self, x, y, text):
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在翻译...")

        # 定位并显示
        self.window.geometry(f"320x140+{x + 10}+{y + 10}")
        self.window.deiconify()
        self.window.lift()

        # 异步网络请求
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
    """浅色系主窗口：包含日常翻译与偏好设置两大功能页"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.title("Easy Translator")
        self.window.geometry("620x540")
        self.window.minsize(520, 440)
        self.window.configure(bg="#f8fafc")

        # 拦截关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.bind("<Escape>", lambda e: self.hide())

        self.current_tab = "trans"
        self.setup_ui()

    def setup_ui(self):
        # 1. 顶部导航栏
        nav_bar = tk.Frame(self.window, bg="#ffffff", padx=20, pady=12, highlightbackground="#e2e8f0", highlightthickness=1)
        nav_bar.pack(fill="x")

        # 品牌图标与标题
        app_title = tk.Label(
            nav_bar, 
            text="Easy Translator", 
            fg="#0f172a", 
            bg="#ffffff", 
            font=("Arial", 14, "bold")
        )
        app_title.pack(side="left")

        # 标签页按钮容器（圆角分段选择卡外观）
        btn_box = tk.Frame(nav_bar, bg="#f1f5f9", padx=3, pady=3)
        btn_box.pack(side="right")

        self.tab_trans_btn = tk.Button(
            btn_box, 
            text="🌐 文本翻译", 
            font=("Arial", 10, "bold"),
            bd=0, 
            padx=14, 
            pady=4,
            command=lambda: self.switch_tab("trans")
        )
        self.tab_trans_btn.pack(side="left")

        self.tab_settings_btn = tk.Button(
            btn_box, 
            text="⚙️ 偏好设置", 
            font=("Arial", 10, "bold"),
            bd=0, 
            padx=14, 
            pady=4,
            command=lambda: self.switch_tab("settings")
        )
        self.tab_settings_btn.pack(side="left")

        # 2. 内容主容器
        self.content_container = tk.Frame(self.window, bg="#f8fafc", padx=20, pady=16)
        self.content_container.pack(fill="both", expand=True)

        # 两个独立的页面 Frame
        self.trans_page = tk.Frame(self.content_container, bg="#f8fafc")
        self.settings_page = tk.Frame(self.content_container, bg="#f8fafc")

        self.build_trans_page()
        self.build_settings_page()

        # 默认展示日常翻译页面
        self.switch_tab("trans")

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        if tab_name == "trans":
            self.settings_page.pack_forget()
            self.trans_page.pack(fill="both", expand=True)
            self.tab_trans_btn.config(bg="#ffffff", fg="#2563eb", highlightbackground="#cbd5e1")
            self.tab_settings_btn.config(bg="#f1f5f9", fg="#64748b", highlightbackground="#f1f5f9")
        else:
            self.trans_page.pack_forget()
            self.settings_page.pack(fill="both", expand=True)
            self.tab_settings_btn.config(bg="#ffffff", fg="#2563eb", highlightbackground="#cbd5e1")
            self.tab_trans_btn.config(bg="#f1f5f9", fg="#64748b", highlightbackground="#f1f5f9")

    # ---------------- 文本翻译页面 ----------------
    def build_trans_page(self):
        # A. 语言选择栏
        lang_bar = tk.Frame(self.trans_page, bg="#f8fafc")
        lang_bar.pack(fill="x", pady=(0, 10))

        tk.Label(lang_bar, text="源语言:", fg="#64748b", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=(0, 4))
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
            bg="#ffffff", 
            fg="#2563eb", 
            highlightbackground="#e2e8f0",
            bd=0, 
            font=("Arial", 10, "bold"),
            padx=4,
            pady=2
        )
        swap_btn.pack(side="left", padx=10)

        tk.Label(lang_bar, text="目标语言:", fg="#64748b", bg="#f8fafc", font=("Arial", 10)).pack(side="left", padx=(0, 4))
        self.tgt_lang_cb = ttk.Combobox(
            lang_bar, 
            values=list(TARGET_LANGUAGES.keys()), 
            state="readonly", 
            width=10, 
            font=("Arial", 10)
        )
        self.tgt_lang_cb.set("中文 (简体)")
        self.tgt_lang_cb.pack(side="left")

        # 状态指示标签
        self.status_lbl = tk.Label(lang_bar, text="就绪", fg="#94a3b8", bg="#f8fafc", font=("Arial", 9))
        self.status_lbl.pack(side="right")

        # B. 原文输入卡片
        src_card = tk.LabelFrame(
            self.trans_page, 
            text=" 原文输入 (Cmd+Enter 快速翻译) ", 
            fg="#475569", 
            bg="#ffffff", 
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            bd=0,
            font=("Arial", 9, "bold"),
            padx=8, 
            pady=6
        )
        src_card.pack(fill="both", expand=True, pady=(0, 10))

        self.src_text = tk.Text(
            src_card, 
            height=5, 
            bg="#ffffff", 
            fg="#0f172a", 
            insertbackground="#2563eb", 
            bd=0, 
            font=("Arial", 11), 
            wrap="word"
        )
        self.src_text.pack(fill="both", expand=True)
        self.src_text.bind("<Command-Return>", lambda e: self.do_manual_translate())
        self.src_text.bind("<Control-Return>", lambda e: self.do_manual_translate())

        # C. 操作按钮栏
        btn_bar = tk.Frame(self.trans_page, bg="#f8fafc")
        btn_bar.pack(fill="x", pady=(0, 10))

        trans_btn = tk.Button(
            btn_bar, 
            text="⚡ 立即翻译", 
            command=self.do_manual_translate, 
            bg="#2563eb", 
            fg="#ffffff", 
            highlightbackground="#2563eb",
            bd=0, 
            font=("Arial", 10, "bold"), 
            padx=16, 
            pady=5
        )
        trans_btn.pack(side="left")

        copy_btn = tk.Button(
            btn_bar, 
            text="📋 复制译文", 
            command=self.copy_result, 
            bg="#ffffff", 
            fg="#334155", 
            highlightbackground="#e2e8f0",
            bd=0, 
            font=("Arial", 9), 
            padx=12, 
            pady=5
        )
        copy_btn.pack(side="left", padx=8)

        clear_btn = tk.Button(
            btn_bar, 
            text="🗑️ 清空", 
            command=self.clear_all, 
            bg="#ffffff", 
            fg="#64748b", 
            highlightbackground="#e2e8f0",
            bd=0, 
            font=("Arial", 9), 
            padx=12, 
            pady=5
        )
        clear_btn.pack(side="left")

        # D. 译文输出卡片
        res_card = tk.LabelFrame(
            self.trans_page, 
            text=" 翻译结果 ", 
            fg="#475569", 
            bg="#ffffff", 
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            bd=0,
            font=("Arial", 9, "bold"),
            padx=8, 
            pady=6
        )
        res_card.pack(fill="both", expand=True)

        self.res_text = tk.Text(
            res_card, 
            height=5, 
            bg="#f8fafc", 
            fg="#0f172a", 
            insertbackground="#2563eb", 
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

        self.status_lbl.config(text="正在翻译...", fg="#2563eb")
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
        self.status_lbl.config(text=f"翻译完成 ({cost:.2f}s)", fg="#16a34a")

    def copy_result(self):
        result = self.res_text.get("1.0", tk.END).strip()
        if result:
            set_clipboard_text(result, self.root)
            self.status_lbl.config(text="译文已复制到剪贴板", fg="#2563eb")

    def clear_all(self):
        self.src_text.delete("1.0", tk.END)
        self.res_text.delete("1.0", tk.END)
        self.status_lbl.config(text="就绪", fg="#94a3b8")

    # ---------------- 偏好设置页面 ----------------
    def build_settings_page(self):
        # 卡片 1：划词速译设置
        card1 = tk.LabelFrame(
            self.settings_page, 
            text=" 划词速译偏好设置 ", 
            fg="#0f172a", 
            bg="#ffffff", 
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            bd=0,
            font=("Arial", 11, "bold"),
            padx=16, 
            pady=14
        )
        card1.pack(fill="x", pady=(0, 14))

        # 选项 1：是否启用鼠标划词自动翻译
        self.mouse_auto_var = tk.BooleanVar(value=config.popover_mouse_auto)
        mouse_auto_cb = tk.Checkbutton(
            card1, 
            text="启用鼠标划词自动翻译（选中文本后松开鼠标即刻自动弹出翻译框）", 
            variable=self.mouse_auto_var, 
            command=self.on_mouse_auto_toggle,
            fg="#0f172a", 
            bg="#ffffff", 
            selectcolor="#f1f5f9", 
            activebackground="#ffffff",
            activeforeground="#2563eb",
            font=("Arial", 10, "bold")
        )
        mouse_auto_cb.pack(anchor="w", pady=(0, 2))

        mouse_tip_lbl = tk.Label(
            card1, 
            text="开启后：鼠标拖选松开即自动翻译；关闭后：仅在按下快捷键时手动触发翻译悬浮窗。", 
            fg="#64748b", 
            bg="#ffffff", 
            font=("Arial", 9)
        )
        mouse_tip_lbl.pack(anchor="w", padx=(24, 0), pady=(0, 12))

        # 分割微线
        sep1 = tk.Frame(card1, bg="#f1f5f9", height=1)
        sep1.pack(fill="x", pady=(0, 12))

        # 选项 2：自动检测语言
        self.auto_lang_var = tk.BooleanVar(value=config.popover_auto_lang)
        auto_cb = tk.Checkbutton(
            card1, 
            text="启用自动检测语言（由软件自主决定目标语言，中英互译）", 
            variable=self.auto_lang_var, 
            command=self.on_auto_lang_toggle,
            fg="#0f172a", 
            bg="#ffffff", 
            selectcolor="#f1f5f9", 
            activebackground="#ffffff",
            activeforeground="#2563eb",
            font=("Arial", 10, "bold")
        )
        auto_cb.pack(anchor="w", pady=(0, 2))

        auto_tip_lbl = tk.Label(
            card1, 
            text="开启后：划词检测到中文自动译为英文，检测到英文及其他语言自动译为中文。", 
            fg="#64748b", 
            bg="#ffffff", 
            font=("Arial", 9)
        )
        auto_tip_lbl.pack(anchor="w", padx=(24, 0), pady=(0, 12))

        # 手动选择语言行（源语言与目标语言）
        manual_frame = tk.Frame(card1, bg="#ffffff")
        manual_frame.pack(anchor="w", padx=(24, 0), fill="x", pady=(0, 2))

        tk.Label(
            manual_frame, 
            text="要翻译的语言：", 
            fg="#334155", 
            bg="#ffffff", 
            font=("Arial", 10)
        ).pack(side="left")

        default_src_name = "自动检测"
        for k, v in LANGUAGES.items():
            if v == config.popover_source_lang:
                default_src_name = k
                break

        self.popover_src_lang_cb = ttk.Combobox(
            manual_frame, 
            values=list(LANGUAGES.keys()), 
            state="disabled" if config.popover_auto_lang else "readonly", 
            width=10, 
            font=("Arial", 10)
        )
        self.popover_src_lang_cb.set(default_src_name)
        self.popover_src_lang_cb.pack(side="left", padx=(0, 16))
        self.popover_src_lang_cb.bind("<<ComboboxSelected>>", self.on_popover_lang_selected)

        tk.Label(
            manual_frame, 
            text="目标语言：", 
            fg="#334155", 
            bg="#ffffff", 
            font=("Arial", 10)
        ).pack(side="left")

        default_tgt_name = "中文 (简体)"
        for k, v in TARGET_LANGUAGES.items():
            if v == config.popover_target_lang:
                default_tgt_name = k
                break

        self.popover_tgt_lang_cb = ttk.Combobox(
            manual_frame, 
            values=list(TARGET_LANGUAGES.keys()), 
            state="disabled" if config.popover_auto_lang else "readonly", 
            width=10, 
            font=("Arial", 10)
        )
        self.popover_tgt_lang_cb.set(default_tgt_name)
        self.popover_tgt_lang_cb.pack(side="left")
        self.popover_tgt_lang_cb.bind("<<ComboboxSelected>>", self.on_popover_lang_selected)

        # 卡片 2：快捷键速查卡片
        card2 = tk.LabelFrame(
            self.settings_page, 
            text=" 快捷键速查 ", 
            fg="#0f172a", 
            bg="#ffffff", 
            highlightbackground="#e2e8f0",
            highlightthickness=1,
            bd=0,
            font=("Arial", 11, "bold"),
            padx=16, 
            pady=14
        )
        card2.pack(fill="x")

        shortcuts = [
            ("划词悬浮速译", "鼠标划词拖选松开 / Alt + Shift + T / Cmd + Shift + X"),
            ("打开 / 隐藏主窗口", "Alt + Shift + M / Cmd + Shift + M"),
            ("快速关闭弹窗 / 窗口", "Esc 键"),
            ("主窗口快速翻译", "Cmd + Enter (macOS) / Ctrl + Enter")
        ]

        for title, key in shortcuts:
            row = tk.Frame(card2, bg="#ffffff")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"• {title}:", fg="#475569", bg="#ffffff", font=("Arial", 10, "bold"), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=key, fg="#2563eb", bg="#ffffff", font=("Arial", 10)).pack(side="left")

    def on_mouse_auto_toggle(self):
        """开启或关闭鼠标选词后自动弹窗翻译"""
        config.popover_mouse_auto = self.mouse_auto_var.get()

    def on_auto_lang_toggle(self):
        """勾选/取消勾选‘自动’选项时的联动逻辑"""
        is_auto = self.auto_lang_var.get()
        config.popover_auto_lang = is_auto

        if is_auto:
            self.popover_src_lang_cb.config(state="disabled")
            self.popover_tgt_lang_cb.config(state="disabled")
        else:
            self.popover_src_lang_cb.config(state="readonly")
            self.popover_tgt_lang_cb.config(state="readonly")
            self.on_popover_lang_selected(None)

    def on_popover_lang_selected(self, event):
        src_name = self.popover_src_lang_cb.get()
        tgt_name = self.popover_tgt_lang_cb.get()
        config.popover_source_lang = LANGUAGES.get(src_name, "auto")
        config.popover_target_lang = TARGET_LANGUAGES.get(tgt_name, "zh-CN")

    def show(self):
        if self.window.state() == "withdrawn" or self.window.state() == "iconic":
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            w, h = 620, 540
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
