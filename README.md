# AITools - 本地极简 AI 翻译小工具

一个基于本地 Ollama 服务的极简悬浮翻译小工具。

## 目录结构
- `app.py`: 原生 Python (Tkinter) 桌面悬浮应用，零第三方依赖，开箱即用。
- `translator_app.html`: 网页版轻量 UI，可在浏览器中直接双击打开或嵌入 Web 框架。

## 使用方法

### 方式 1: 运行原生桌面程序 (推荐)
无需安装额外的 Python 库，直接在终端中运行：

```bash
python3 app.py
```

### 方式 2: 使用网页版
直接双击打开 `translator_app.html` 即可在浏览器中使用。

> **注意**：使用前请确保本地已开启 Ollama 服务（默认端口 `http://localhost:11434`）。
