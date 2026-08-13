import tkinter as tk
from tkinter import ttk
import urllib.request
import json
import threading
import time

OLLAMA_HOST = "http://localhost:11434"

class MinimalTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local AI Translator")
        self.root.geometry("460x460")
        self.root.configure(bg="#0f172a")
        
        # 窗口置顶
        self.root.attributes('-topmost', True)

        self.last_clipboard = ""
        self.auto_detect_enabled = tk.BooleanVar(value=True)

        self.setup_ui()
        self.load_models()
        self.start_clipboard_listener()

    def setup_ui(self):
        # 1. 顶部配置栏 (模型选择 + 自动检测开关)
        top_frame = tk.Frame(self.root, bg="#1e293b", padx=12, pady=10)
        top_frame.pack(fill="x", side="top")

        title_lbl = tk.Label(top_frame, text="⚡ Local Translator", fg="#38bdf8", bg="#1e293b", font=("Arial", 12, "bold"))
        title_lbl.pack(side="left")

        # 自动检测复选框
        auto_cb = tk.Checkbutton(
            top_frame, 
            text="⚡ 自动检测剪贴板", 
            variable=self.auto_detect_enabled,
            bg="#1e293b", 
            fg="#38bdf8", 
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#38bdf8",
            font=("Arial", 10)
        )
        auto_cb.pack(side="left", padx=(10, 0))

        self.model_var = tk.StringVar(value="正在检测...")
        self.model_combo = ttk.Combobox(top_frame, textvariable=self.model_var, state="readonly", width=14)
        self.model_combo.pack(side="right")

        refresh_btn = tk.Button(
            top_frame, 
            text="🔄", 
            command=self.load_models, 
            fg="#0f172a", 
            highlightbackground="#1e293b",
            font=("Arial", 11, "bold"),
            bd=0
        )
        refresh_btn.pack(side="right", padx=4)

        # 2. 核心文本输入输出区
        content_frame = tk.Frame(self.root, bg="#0f172a", padx=12, pady=8)
        content_frame.pack(fill="both", expand=True)

        # 原文输入框
        src_lbl = tk.Label(content_frame, text="原文 (剪贴板复制自动填充，或 Enter 手动翻译):", fg="#94a3b8", bg="#0f172a", font=("Arial", 10))
        src_lbl.pack(anchor="w", pady=(0, 4))

        self.src_text = tk.Text(content_frame, height=5, bg="#1e293b", fg="#f8fafc", insertbackground="white", bd=1, relief="solid", font=("Arial", 12), wrap="word")
        self.src_text.pack(fill="both", expand=True)
        self.src_text.bind("<Return>", self.on_enter)

        # 极简操作栏
        btn_frame = tk.Frame(content_frame, bg="#0f172a")
        btn_frame.pack(fill="x", pady=8)

        clear_btn = tk.Button(
            btn_frame, 
            text="🗑️ 清空", 
            command=self.clear_text, 
            fg="#0f172a", 
            highlightbackground="#e2e8f0", 
            font=("Arial", 11, "bold"),
            bd=0
        )
        clear_btn.pack(side="left")

        trans_btn = tk.Button(
            btn_frame, 
            text="🚀 翻译", 
            command=self.start_translation, 
            fg="#0f172a", 
            highlightbackground="#38bdf8", 
            font=("Arial", 11, "bold"), 
            bd=0, 
            padx=10
        )
        trans_btn.pack(side="right")

        # 译文显示框
        tgt_lbl = tk.Label(content_frame, text="译文结果:", fg="#94a3b8", bg="#0f172a", font=("Arial", 10))
        tgt_lbl.pack(anchor="w", pady=(6, 4))

        self.tgt_text = tk.Text(content_frame, height=6, bg="#090d16", fg="#38bdf8", insertbackground="white", bd=1, relief="solid", font=("Arial", 12), wrap="word")
        self.tgt_text.pack(fill="both", expand=True)

        copy_btn = tk.Button(
            content_frame, 
            text="📋 复制译文", 
            command=self.copy_result, 
            fg="#0f172a", 
            highlightbackground="#e2e8f0", 
            font=("Arial", 11, "bold"),
            bd=0
        )
        copy_btn.pack(anchor="e", pady=(8, 0))

    def start_clipboard_listener(self):
        """启动后台线程实时监听系统剪贴板变化"""
        def _listen():
            while True:
                time.sleep(0.6)
                if not self.auto_detect_enabled.get():
                    continue

                try:
                    clip_text = self.root.clipboard_get().strip()
                    if clip_text and clip_text != self.last_clipboard:
                        self.last_clipboard = clip_text
                        # 自动写入原文框并触发翻译
                        self.root.after(0, self._handle_auto_detected_text, clip_text)
                except Exception:
                    pass

        threading.Thread(target=_listen, daemon=True).start()

    def _handle_auto_detected_text(self, text):
        self.src_text.delete("1.0", tk.END)
        self.src_text.insert(tk.END, text)
        self.start_translation()

    def load_models(self):
        """自动请求本地 Ollama 11434 端口获取模型列表"""
        def _fetch():
            try:
                req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    models = [m['name'] for m in data.get('models', [])]
                    if models:
                        self.model_combo['values'] = models
                        self.model_combo.current(0)
                    else:
                        self.model_var.set("无可用模型")
            except Exception:
                self.model_var.set("未连接Ollama")

        threading.Thread(target=_fetch, daemon=True).start()

    def on_enter(self, event):
        if not event.state & 0x0001:  # 没有按下 Shift 键
            self.start_translation()
            return "break"

    def clear_text(self):
        self.src_text.delete("1.0", tk.END)
        self.tgt_text.delete("1.0", tk.END)

    def copy_result(self):
        result = self.tgt_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)

    def start_translation(self):
        text = self.src_text.get("1.0", tk.END).strip()
        model = self.model_var.get()

        if not text or not model or model.startswith("未") or model.startswith("无"):
            return

        self.tgt_text.delete("1.0", tk.END)
        self.tgt_text.insert(tk.END, "正在翻译中...")

        def _translate_thread():
            try:
                payload = json.dumps({
                    "model": model,
                    "prompt": f"You are a translator. Directly translate the following text into Chinese without extra explanation:{text}",
                    "stream": True
                }).encode('utf-8')

                req = urllib.request.Request(
                    f"{OLLAMA_HOST}/api/generate",
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )

                with urllib.request.urlopen(req) as resp:
                    self.tgt_text.delete("1.0", tk.END)
                    for line in resp:
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            chunk = data.get('response', '')
                            self.tgt_text.insert(tk.END, chunk)
                            self.tgt_text.see(tk.END)
            except Exception as e:
                self.tgt_text.delete("1.0", tk.END)
                self.tgt_text.insert(tk.END, f"翻译失败，请确认 Ollama 正在运行: {e}")

        threading.Thread(target=_translate_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MinimalTranslatorApp(root)
    root.mainloop()
