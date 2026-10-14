# Akira&Amane的翻译小软件

一个 Windows 桌面小工具：调用 [Index-Translate](https://github.com/bilibili/Index-Translate)（B 站开源的多语言多模态翻译模型）进行**文本翻译**和**图片翻译**。图片翻译支持选择本地图片或直接读取剪贴板截图，支持公网免费 API 和本地私有化部署两种接口。

基于官方文档的 OpenAI 兼容 `image_url` 多模态调用方式实现，原生视觉端到端翻译，零 OCR 依赖。

## 功能

- **文本翻译**：粘贴即翻，支持 Ctrl+Enter 快捷翻译、译文接力（互换）
- **选择图片翻译**：支持 PNG / JPG / WEBP / BMP / GIF
- **剪贴板直翻**：截图（Win+Shift+S）后一键读取翻译
- **双接口切换**（软件内「接口设置」）：
  - 公网免费 API（Index-Translate-35B-A3B 旗舰模型，官方免费提供，无需本地显卡）
  - 本地 / 局域网服务（自己部署的模型，离线可用，图片不出本机）
- 目标语言：中文 / English / 日本語 / 한국어 / Deutsch / Français / Español / Русский
- 大图自动缩放至官方建议的 2048px 以内；自动抑制模型思考输出
- 内置中英双语使用教程；界面语言支持中文 / English 切换
- 设置持久化到同目录 `config.json`

## 使用

双击 `Akira&Amane的翻译小软件.exe` 即可（Windows 10/11 64 位）。首次打开默认使用公网免费 API，开箱即用。

- 首次运行可能触发 SmartScreen 提示（未签名），点"更多信息 → 仍要运行"
- 命令行测试模式：`python index_translator.py --cli 图片路径` / `python index_translator.py --text "文本"`（打包的 exe 为窗口模式，命令行测试请用脚本）

## 接口配置

软件内点「接口设置」修改，保存到 `config.json`：

```json
{
  "endpoint": "local",
  "api_url": "http://127.0.0.1:1234/v1/chat/completions",
  "model": "index-translate-9b"
}
```

| 接口 | api_url | model |
| --- | --- | --- |
| 公网免费 API | `https://index-translate.bilibili.com/v1/chat/completions` | `Index-Translate-35B-A3B` |
| 本机 LM Studio/Bionic | `http://127.0.0.1:1234/v1/chat/completions` | `index-translate-9b` |
| 局域网其他电脑 | `http://<内网IP>:1234/v1/chat/completions` | `index-translate-9b` |

## 本地部署环境（作者的机器配置，供复现参考）

- 推理服务：LM Studio Bionic（内置 LM Studio 运行时），模型通过 GUI 下载
- 模型：`IndexTeam/Index-Translate-9B-GGUF`
  - 主模型 `Index-Translate-9B.Q4_K_S.gguf`（5.2GB）
  - 视觉投影层 `Index-Translate-9B.mmproj-f16.gguf`（876MB，必须和主模型放同一目录）
  - 存放路径：`~/.lmstudio/models/IndexTeam/Index-Translate-9B-GGUF/`
- 硬件参考：RX 6750 XT 12GB 显存可全量 offload；8GB+ 显存的显卡均可流畅运行 9B Q4
- 启动本地服务：`lms server start --cors`（`lms` CLI 在 `~/.lmstudio/bin/`）
- 局域网共享：`lms server start --cors --bind 0.0.0.0`，并放行防火墙 TCP 1234 端口

## 相关：沉浸式翻译公网代理（可选）

浏览器「沉浸式翻译」插件直连官方 API 需经本地代理（绕过 CORS 并关闭思考输出）：

- 脚本：`~/index-translate-proxy/call_api.py`（来自官方仓库 `inference/llm/call_api.py`，零依赖）
- 启动：`python call_api.py --serve`（监听 127.0.0.1:8080）
- 开机自启：计划任务 `IndexTranslateProxy` → `run_proxy.vbs`（隐藏窗口，日志写入 `proxy.log`）
- 沉浸式翻译配置：自定义 OpenAI 服务，URL `http://127.0.0.1:8080/v1`，模型 `Index-Translate-35B-A3B`，Key 任意

## 从源码构建

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pillow pyinstaller   # Windows
.venv/Scripts/python -m PyInstaller --onefile --windowed --name "Akira&Amane的翻译小软件" index_translator.py
# 产物在 dist/Akira&Amane的翻译小软件.exe
```

macOS / Linux 无需打包，直接 `pip install pillow` 后运行 `python index_translator.py`。

## 常见问题

- **无法连接**：公网模式检查网络；本地模式确认服务已启动、地址端口正确。Clash/v2ray 等代理工具（尤其 TUN 模式）需将 `127.0.0.1` 及局域网地址设为直连
- **译文夹带 `<think>` 思考内容**：在 Bionic/LM Studio 模型加载配置中关闭 Reasoning 输出（程序已做兜底剥离）
- **首次翻译慢**：本地模型约 6GB，首次请求需加载进显存，之后即快

## 致谢与许可

- 模型与接口：[bilibili/Index-Translate](https://github.com/bilibili/Index-Translate)（Apache 2.0）
- 本程序仅供学习交流使用
