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

import urllib.request
import urllib.parse
import json
import threading
import time
import math
import subprocess

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Controller as KeyboardController, Key
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


# 语言代码映射表
LANGUAGES = {
    "自动检测": "auto",
    "中文 (简体)": "zh-CN",
    "英语": "en",
    "日语": "ja",
    "韩语": "ko",
    "法语": "fr",
    "德语": "de",
    "西班牙语": "es",
    "俄语": "ru",
    "意大利语": "it",
    "葡萄牙语": "pt"
}

# 仅用于目标语言的选择列表（不含自动检测）
TARGET_LANGUAGES = {k: v for k, v in LANGUAGES.items() if v != "auto"}


class AppConfig:
    """应用全局配置类，管理划词与主窗口翻译偏好"""
    def __init__(self):
        # 划词翻译：是否由软件自主决定目标语言（自动检测）
        self.popover_auto_lang = True
        # 划词翻译：手动指定的固定目标语言代码
        self.popover_target_lang = "zh-CN"


# 全局配置单例
config = AppConfig()


def get_clipboard_text(root_tk=None):
    """跨平台原生安全读取剪贴板内容"""
    if sys.platform == 'darwin':
        try:
            return subprocess.check_output(['pbpaste'], text=True)
        except Exception:
            pass
    if root_tk:
        try:
            return root_tk.clipboard_get()
        except Exception:
            pass
    return ""


def set_clipboard_text(text, root_tk=None):
    """跨平台原生安全写入/清空剪贴板内容"""
    if sys.platform == 'darwin':
        try:
            subprocess.run(['pbcopy'], input=text, text=True)
            return
        except Exception:
            pass
    if root_tk:
        try:
            root_tk.clipboard_clear()
            root_tk.clipboard_append(text)
            root_tk.update()
        except Exception:
            pass


def api_translate(text, source_lang="auto", target_lang=None):
    """
    通用在线翻译函数（双通道：有道开放 API + MyMemory 备用 API）
    :param text: 待翻译文本
    :param source_lang: 源语言代码 ('auto', 'zh-CN', 'en', ...)
    :param target_lang: 目标语言代码 ('zh-CN', 'en', ...)
    :return: 翻译结果字符串
    """
    if not text or not text.strip():
        return ""

    text = text.strip()

    # 1. 确定目标语言与翻译方向
    if target_lang is None or target_lang == "auto":
        if config.popover_auto_lang:
            # 智能判断：包含中文则译为英文，否则译为中文
            is_zh = any('\u4e00' <= c <= '\u9fff' for c in text)
            tgt = 'en' if is_zh else 'zh-CN'
            src = 'zh-CN' if is_zh else 'auto'
        else:
            tgt = config.popover_target_lang
            src = source_lang
    else:
        tgt = target_lang
        src = source_lang

    # 2. 优先通道：有道开放词典 API
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

    # 3. 备用通道：MyMemory 免费 API
    try:
        src_code = 'auto' if src == 'auto' else src
        langpair = f"{src_code}|{tgt}"
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

    return "翻译失败，请检查网络连接。"


class InputListenerManager:
    """全局按键与鼠标事件监听管理类"""
    def __init__(self, on_popover_trigger, on_main_window_toggle, is_inside_window_func):
        self.on_popover_trigger = on_popover_trigger
        self.on_main_window_toggle = on_main_window_toggle
        self.is_inside_window_func = is_inside_window_func

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_click_time = 0
        self.keyboard_controller = KeyboardController() if HAS_PYNPUT else None

    def start(self):
        if not HAS_PYNPUT:
            return

        # 1. 注册全局快捷键
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<alt>+<shift>+t': self.on_popover_trigger,       # 划词翻译悬浮卡片
                '<cmd>+<shift>+x': self.on_popover_trigger,       # 划词翻译悬浮卡片
                '<alt>+<shift>+m': self.on_main_window_toggle,    # 打开/隐藏主窗口
                '<cmd>+<shift>+m': self.on_main_window_toggle     # 打开/隐藏主窗口
            })
            self.hotkey_listener.start()
        except Exception:
            pass

        # 2. 注册鼠标松开监听
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

                # 拖动距离大于 8 像素或双击触发
                if distance > 8 or is_double_click:
                    if self.is_inside_window_func(x, y):
                        return
                    self.on_popover_trigger()

        try:
            self.mouse_listener = mouse.Listener(on_click=_on_mouse_click)
            self.mouse_listener.start()
        except Exception:
            pass

    def simulate_copy(self):
        """模拟按下复制快捷键 (macOS: Cmd+C, 其他: Ctrl+C)"""
        if not self.keyboard_controller:
            return
        copy_key = Key.cmd if sys.platform == 'darwin' else Key.ctrl
        try:
            with self.keyboard_controller.pressed(copy_key):
                self.keyboard_controller.press('c')
                time.sleep(0.05)
                self.keyboard_controller.release('c')
        except Exception:
            pass
