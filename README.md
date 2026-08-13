# AITools - 极简划词速译与桌面 AI 工具集

一个轻量、无感、高效的桌面划词翻译与 AI 工具集合，专为提升日常阅读与办公效率而设计。

---

## 🌟 核心特性

### 1. 主推插件：划词速译悬浮窗 (`popover_translator.py`)
* ⚡ **选中文本即译**：选中任意网页或文档中的文本，按下快捷键（`Alt + Shift + T` 或 `Cmd + Shift + X`）即可自动提取并翻译，无需手动按下 `Cmd + C`。
* 🛡️ **剪贴板无痕保护**：提取选中文本后**自动还原用户原有的剪贴板内容**，绝不污染您此前复制的历史数据。
* 🌐 **免 Key 免费翻译 API**：集成国内访问极速的有道开放 API（主通道）与 MyMemory 翻译 API（备用通道），免注册、免配置 API Key、国内直连畅通。
* 🔀 **智能中英双向识别**：自动检测文本语言，中文自动译为英文，英文及其他语言自动译为中文。
* 🎨 **90% 半透明悬浮窗口**：天蓝色边框 + 深蓝黑夜卡片（`#0f172a`），跟随鼠标指针位置精准弹出，支持按 `Esc` 键或点击右上角 `✕` 快捷关闭。

### 2. 面板式应用 (`app.py`)
* 带有模型下拉选择、剪贴板自动检测及按钮控制的经典窗口。
* 支持连接本地 Ollama 服务（默认端口 `http://localhost:11434`），可搭配 `qwen2.5:0.5b` 或 `qwen2.5:1.5b` 等轻量本地模型使用。

### 3. 网页版组件 (`translator_app.html`)
* 纯 HTML/CSS/JS 构建的极简 Web 界面组件，支持直接双击在浏览器中打开使用。

---

## 📁 项目文件结构

```text
AITools/
├── popover_translator.py   # [主推] 全局快捷键划词速译悬浮插件 (在线 API + 剪贴板保护)
├── app.py                  # 面板式桌面应用 (支持 Ollama 本地 AI 模型)
├── translator_app.html     # Web UI 网页版界面
└── README.md               # 项目使用说明文档
```

---

## 🚀 快速开始

### 运行主推划词速译插件 (`popover_translator.py`)

#### 1. 安装依赖
工具使用 `pynput` 监听全局快捷键及模拟复制操作：

```bash
pip3 install pynput
```

#### 2. 启动程序
在终端中运行以下命令：

```bash
python3 /Users/pingguo/Documents/Project/AITools/popover_translator.py
```

#### 3. 使用快捷键
* **划词翻译**：在任意应用（浏览器、PDF 阅读器、编辑器等）中鼠标**选中文本**，然后按下 `Alt + Shift + T`（或 `Cmd + Shift + X`）。
* **关闭悬浮窗**：按 `Esc` 键或点击窗口右上角 `✕` 按钮。

---

## 💡 其他使用方式

### 运行本地 AI 模型版 (`app.py`)
若您希望配合本地 Ollama AI 模型使用：
1. 确保本地已启动 Ollama 服务（`http://localhost:11434`）。
2. 在终端运行：
   ```bash
   python3 /Users/pingguo/Documents/Project/AITools/app.py
   ```

### 打开网页版 (`translator_app.html`)
直接双击 `translator_app.html` 文件，即可在默认浏览器中打开并使用 Web 界面。
