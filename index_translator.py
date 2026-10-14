# -*- coding: utf-8 -*-
"""Index 全能翻译 / Index Translator - 调用 Index-Translate 模型翻译图片和文本。

支持两种接口：
  - 公网免费 API（Index-Translate-35B-A3B，官方免费提供，无需本地显卡）
  - 本地 / 局域网服务（自己在 Bionic / LM Studio / llama.cpp 部署的模型）

接口与界面语言设置保存在程序同目录的 config.json，可在软件内"接口设置"中修改。

用法:
  图形界面: 直接运行（或双击打包后的 exe）
  命令行测试: python index_translator.py --cli 图片路径 [--target 中文]
              python index_translator.py --text "要翻译的文本" [--target 英语]
"""
import argparse
import base64
import io
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import urllib.error

__version__ = "0.1.0"

MAX_SIDE = 2048  # 官方建议图片最长边不超过 2048px
TIMEOUT = 300

ENDPOINTS = {
    "public": {
        "label": {"zh": "公网免费 API：Index-Translate-35B-A3B（B 站 IndexTeam 开源）",
                  "en": "Public free API: Index-Translate-35B-A3B (open-sourced by bilibili IndexTeam)"},
        "short": "公网 Index-Translate-35B-A3B",
        "api_url": "https://index-translate.bilibili.com/v1/chat/completions",
        "model": "Index-Translate-35B-A3B",
    },
    "local": {
        "label": {"zh": "本地 / 局域网：Index-Translate-9B（自己部署）",
                  "en": "Local / LAN: Index-Translate-9B (self-hosted)"},
        "short": "本地 Index-Translate-9B",
        "api_url": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "index-translate-9b",
    },
}

STR = {
    "zh": {
        "app_title": "Akira&Amane的翻译小软件",
        "tab_image": "  图片翻译  ",
        "tab_text": "  文本翻译  ",
        "btn_pick": "选择图片",
        "btn_clipboard": "从剪贴板读取",
        "lbl_target": "目标语言:",
        "btn_translate": "开始翻译",
        "btn_translate_text": "开始翻译 (Ctrl+Enter)",
        "btn_swap": "互换",
        "btn_copy": "复制结果",
        "btn_settings": "接口设置",
        "btn_tutorial": "使用教程",
        "btn_about": "关于",
        "lbl_ui_lang": "界面语言:",
        "lbl_src": "原文:",
        "lbl_dst": "译文:",
        "preview_empty": "（图片预览）",
        "status_ready": "就绪",
        "status_loaded": "已载入图片（{src}），可以开始翻译",
        "status_no_clip": "剪贴板里没有图片",
        "status_busy_img": "图片翻译中，请稍候……",
        "status_busy_txt": "文本翻译中，请稍候……",
        "status_done": "翻译完成",
        "status_copied": "已复制到剪贴板",
        "status_failed": "请求失败",
        "status_error": "出错",
        "status_saved": "接口设置已保存",
        "status_lang": "界面语言已切换",
        "msg_no_image": "请先选择图片或从剪贴板读取",
        "msg_no_text": "请先输入要翻译的文本",
        "err_title": "错误",
        "err_read_image": "无法读取图片：\n{e}",
        "err_clipboard": "读取剪贴板失败：\n{e}",
        "err_clip_file": "无法读取剪贴板中的文件：\n{e}",
        "err_req_title": "请求失败",
        "err_req_body": "无法连接接口 {url}\n请检查网络，或在「接口设置」中确认地址。\n\n{e}",
        "settings_title": "接口设置",
        "lbl_endpoint": "接口选择：",
        "lbl_url": "服务器地址：",
        "lbl_model": "模型名称：",
        "btn_test": "测试连接",
        "testing": "测试中……",
        "btn_save": "保存",
        "btn_cancel": "取消",
        "warn_title": "提示",
        "warn_empty": "服务器地址和模型名称不能为空",
        "warn_save_fail": "配置已生效，但写入 config.json 失败：\n{e}",
        "conn_ok": "连接成功，测试译文：{text}",
        "conn_fail": "连接失败：{e}",
        "about_body": "\n翻译能力由 Index-Translate 模型提供\n模型开发者：哔哩哔哩 IndexTeam\n开源协议：Apache License 2.0\n\n感谢 B 站 IndexTeam 开源 Index-Translate 系列模型\n并提供免费的公网翻译 API。\n\n特别感谢：谢谢我的老婆 Amane 帮助我测试\n以及给我满满的动力，超级超级喜欢我的老婆(*╹▽╹*)",
        "about_link": "访问模型项目主页（GitHub）",
    },
    "en": {
        "app_title": "Akira&Amane Translator",
        "tab_image": "  Image  ",
        "tab_text": "  Text  ",
        "btn_pick": "Open Image",
        "btn_clipboard": "From Clipboard",
        "lbl_target": "Target:",
        "btn_translate": "Translate",
        "btn_translate_text": "Translate (Ctrl+Enter)",
        "btn_swap": "Swap",
        "btn_copy": "Copy Result",
        "btn_settings": "Endpoint",
        "btn_tutorial": "Help",
        "btn_about": "About",
        "lbl_ui_lang": "Language:",
        "lbl_src": "Source:",
        "lbl_dst": "Translation:",
        "preview_empty": "(image preview)",
        "status_ready": "Ready",
        "status_loaded": "Image loaded ({src}), ready to translate",
        "status_no_clip": "No image in clipboard",
        "status_busy_img": "Translating image...",
        "status_busy_txt": "Translating text...",
        "status_done": "Done",
        "status_copied": "Copied to clipboard",
        "status_failed": "Request failed",
        "status_error": "Error",
        "status_saved": "Endpoint settings saved.",
        "status_lang": "UI language switched.",
        "msg_no_image": "Please open an image or read from clipboard first",
        "msg_no_text": "Please enter some text first",
        "err_title": "Error",
        "err_read_image": "Cannot read image:\n{e}",
        "err_clipboard": "Failed to read clipboard:\n{e}",
        "err_clip_file": "Cannot read file from clipboard:\n{e}",
        "err_req_title": "Request Failed",
        "err_req_body": "Cannot reach endpoint {url}\nCheck your network, or verify the address in Endpoint settings.\n\n{e}",
        "settings_title": "Endpoint Settings",
        "lbl_endpoint": "Endpoint:",
        "lbl_url": "Server URL:",
        "lbl_model": "Model name:",
        "btn_test": "Test",
        "testing": "Testing...",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "warn_title": "Note",
        "warn_empty": "Server URL and model name cannot be empty",
        "warn_save_fail": "Settings applied, but failed to write config.json:\n{e}",
        "conn_ok": "Connected. Test translation: {text}",
        "conn_fail": "Connection failed: {e}",
        "about_body": "\nTranslation powered by the Index-Translate models\nDeveloper: bilibili IndexTeam\nLicense: Apache License 2.0\n\nThanks to bilibili IndexTeam for open-sourcing\nthe Index-Translate model family and the free public API.\n\nSpecial thanks to my wife Amane for testing\nand endless motivation. Love you so much (*╹▽╹*)",
        "about_link": "Visit model project (GitHub)",
    },
}

TUTORIAL = {
    "zh": """\
【Index 全能翻译 - 使用教程】

■ 图片翻译
1. 切换到「图片翻译」标签页。
2. 点击「选择图片」挑选本地图片，或先截图（Win+Shift+S）后点「从剪贴板读取」。
3. 选择目标语言，点击「开始翻译」，结果可一键复制。

■ 文本翻译
1. 切换到「文本翻译」标签页。
2. 在上方输入框粘贴或输入原文，选择目标语言。
3. 点击「开始翻译」（或按 Ctrl+Enter），结果显示在下方。
4. 「互换」按钮可将译文放回输入框继续翻译（接力翻译）。

■ 接口选择（点下方「接口设置」）
· 公网免费 API：B 站官方免费提供的 Index-Translate-35B-A3B 旗舰模型，
  翻译质量最好，无需本地显卡，但需要联网，内容会发送到官方服务器。
· 本地 / 局域网：使用自己部署的模型（如本机 Bionic 里的
  Index-Translate-9B），离线可用、内容不出本机。
  本机使用保持默认 http://127.0.0.1:1234 即可；
  连接局域网内其他电脑时，把 127.0.0.1 改成那台电脑的内网 IP。
注意：本地文本翻译使用纯文本模型即可；图片翻译需要模型带视觉
投影层（mmproj）文件。

■ 本地接口前提
· Bionic 或 LM Studio 的本地服务已启动（终端运行 lms server start --cors）。
· 模型已加载；首次翻译需加载模型（约 6GB），会慢十几秒，之后即快。

■ 常见问题
· 提示"无法连接"：公网模式请检查网络；本地模式请确认服务已启动、
  地址端口正确。若开了 Clash/v2ray 等代理工具（尤其 TUN 模式），
  请将 127.0.0.1 和局域网地址设为直连。
· 译文里出现 <think> 等思考内容：在 Bionic/LM Studio 的模型加载
  配置中关闭思考（Reasoning）输出。
· 图片很大时翻译慢：程序会自动把最长边缩放到 2048px（官方建议），
  属正常现象。
""",
    "en": """\
[Index Translator - Help]

■ Image Translation
1. Switch to the "Image" tab.
2. Click "Open Image", or take a screenshot (Win+Shift+S) and click
   "From Clipboard".
3. Pick the target language and click "Translate".

■ Text Translation
1. Switch to the "Text" tab.
2. Paste or type the source text, pick the target language.
3. Click "Translate" (or press Ctrl+Enter).
4. "Swap" moves the result back into the input box for relay
   translation or back-translation checks.

■ Endpoints (the "Endpoint" button at the bottom)
· Public free API: Index-Translate-35B-A3B hosted by bilibili.
  Best quality, no GPU needed, but requires internet access and
  content is sent to the official server.
· Local / LAN: your own deployment (e.g. Index-Translate-9B in
  Bionic / LM Studio). Works offline; content never leaves your
  machine. Keep http://127.0.0.1:1234 for local use, or replace
  127.0.0.1 with the LAN IP of the machine running the model.
Note: text translation needs a text-only model; image translation
requires the vision projector (mmproj) file next to the model.

■ Requirements for the local endpoint
· The LM Studio/Bionic server is running (lms server start --cors).
· The first request loads the ~6GB model and may take a while.

■ Troubleshooting
· "Cannot connect": check network (public) or server/port (local).
  If you use Clash/v2ray (especially TUN mode), set 127.0.0.1 and
  LAN addresses to DIRECT.
· <think> tags in output: disable reasoning in the model's load
  config in Bionic/LM Studio.
· Large images are auto-resized to 2048px (official recommendation).
""",
}


def _config_path():
    base_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")


def _load_config():
    cfg = {"endpoint": "public",
           "api_url": ENDPOINTS["public"]["api_url"],
           "model": ENDPOINTS["public"]["model"],
           "ui_lang": "zh"}
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def _save_config(cfg):
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


_CONFIG = _load_config()
API_URL = _CONFIG["api_url"]
MODEL = _CONFIG["model"]
UI_LANG = _CONFIG.get("ui_lang", "zh")
S = STR.get(UI_LANG, STR["zh"])

LANG_NAMES = ["中文", "English", "日本語", "한국어", "Deutsch", "Français", "Español", "Русский"]
PROMPTS = {
    "中文": "请将图片中的文本翻译为中文，直接输出翻译结果，不要进行任何解释。",
    "English": "Translate the text in the image into English. Output only the translation, no explanation.",
    "日本語": "画像内のテキストを日本語に翻訳してください。翻訳結果のみを出力し、説明は不要です。",
    "한국어": "이미지 속 텍스트를 한국어로 번역해 주세요. 번역 결과만 출력하고 설명은 하지 마세요.",
    "Deutsch": "Übersetzen Sie den Text im Bild ins Deutsche. Geben Sie nur die Übersetzung aus, ohne Erklärung.",
    "Français": "Traduisez le texte de l'image en français. N'affichez que la traduction, sans explication.",
    "Español": "Traduce el texto de la imagen al español. Muestra solo la traducción, sin explicaciones.",
    "Русский": "Переведите текст на изображении на русский язык. Выведите только перевод, без пояснений.",
}
TEXT_PROMPTS = {
    "中文": "请将以下文本翻译为中文，直接输出翻译结果，不要进行任何解释。\n\n{text}",
    "English": "Translate the following text into English. Output only the translation, no explanation.\n\n{text}",
    "日本語": "以下のテキストを日本語に翻訳してください。翻訳結果のみを出力し、説明は不要です。\n\n{text}",
    "한국어": "다음 텍스트를 한국어로 번역해 주세요. 번역 결과만 출력하고 설명은 하지 마세요.\n\n{text}",
    "Deutsch": "Übersetzen Sie den folgenden Text ins Deutsche. Geben Sie nur die Übersetzung aus, ohne Erklärung.\n\n{text}",
    "Français": "Traduisez le texte suivant en français. N'affichez que la traduction, sans explication.\n\n{text}",
    "Español": "Traduce el siguiente texto al español. Muestra solo la traducción, sin explicaciones.\n\n{text}",
    "Русский": "Переведите следующий текст на русский язык. Выведите только перевод, без пояснений.\n\n{text}",
}


def normalize_image(img, max_side=MAX_SIDE):
    """缩放至最长边 <= max_side 并转成 PNG 字节。"""
    from PIL import Image
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > max_side:
        scale = max_side / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def strip_think(text):
    """万一服务端没关思考，剥掉 <think>...</think> 段。"""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _post_json(url, payload, timeout):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Index-Translate-Client/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _chat(content, max_tokens):
    """统一的 chat completions 调用，content 为字符串或图文混排数组。"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    data = _post_json(API_URL, payload, TIMEOUT)
    return strip_think(data["choices"][0]["message"].get("content") or "")


def translate_image(png_bytes, target="中文"):
    """按官方文档的 OpenAI image_url 方式调用接口，返回译文字符串。"""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    content = [
        {"type": "text", "text": PROMPTS.get(target, PROMPTS["中文"])},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]
    return _chat(content, max_tokens=2048)


def translate_text(text, target="中文"):
    """纯文本翻译。"""
    prompt = TEXT_PROMPTS.get(target, TEXT_PROMPTS["中文"]).format(text=text)
    return _chat(prompt, max_tokens=max(1024, len(text) * 3))


def test_connection(api_url, model):
    """发一条纯文本翻译请求验证接口连通性，返回 (是否成功, 译文或错误)。"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Please translate into Chinese, output only the translation:\n\nHello"}],
        "temperature": 0.0,
        "max_tokens": 32,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        data = _post_json(api_url, payload, 60)
        return True, strip_think(data["choices"][0]["message"].get("content") or "")
    except Exception as e:
        return False, str(e)


def cli_main():
    parser = argparse.ArgumentParser(description="Index Translator (CLI test mode)")
    parser.add_argument("--cli", metavar="IMAGE", help="image path to translate")
    parser.add_argument("--text", metavar="TEXT", help="text to translate")
    parser.add_argument("--target", default="中文", choices=LANG_NAMES, help="target language")
    args = parser.parse_args()

    if args.text:
        print(translate_text(args.text, args.target))
    elif args.cli:
        from PIL import Image
        with Image.open(args.cli) as img:
            png_bytes = normalize_image(img)
        print(translate_image(png_bytes, args.target))
    else:
        parser.error("specify --cli IMAGE or --text TEXT")


def gui_main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import Image, ImageGrab, ImageTk

    global S, UI_LANG

    root = tk.Tk()
    root.geometry("780x720")

    state = {"png_bytes": None, "preview_img": None, "busy": False,
             "src_text": "", "dst_text": "", "img_result": "", "tab": 0}
    refs = {}

    def endpoint_label():
        for key, ep in ENDPOINTS.items():
            if API_URL == ep["api_url"] and MODEL == ep["model"]:
                return ep["short"]
        host = urllib.parse.urlparse(API_URL).netloc
        return f"custom ({host})" if UI_LANG == "en" else f"自定义（{host}）"

    def refresh_title():
        root.title(f"{S['app_title']}  [{endpoint_label()}]")

    refresh_title()

    status_var = tk.StringVar(value=S["status_ready"])

    def set_status(msg):
        status_var.set(msg)
        root.update_idletasks()

    def run_async(work, on_ok, busy_desc):
        """在后台线程执行翻译，避免界面卡死。work() 返回译文。"""
        if state["busy"]:
            return
        state["busy"] = True
        set_status(busy_desc)

        def worker():
            try:
                text = work()
                root.after(0, lambda: (on_ok(text), set_status(S["status_done"])))
            except urllib.error.URLError as e:
                root.after(0, lambda: (set_status(S["status_failed"]),
                                       messagebox.showerror(S["err_req_title"],
                                           S["err_req_body"].format(url=API_URL, e=e))))
            except Exception as e:
                root.after(0, lambda: (set_status(S["status_error"]),
                                       messagebox.showerror(S["err_title"], str(e))))
            finally:
                root.after(0, lambda: state.update(busy=False))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- 接口设置窗口 ----------
    def open_settings():
        global API_URL, MODEL
        win = tk.Toplevel(root)
        win.title(S["settings_title"])
        win.transient(root)
        win.grab_set()
        win.resizable(False, False)

        endpoint_var = tk.StringVar(value=_CONFIG.get("endpoint", "public"))
        url_var = tk.StringVar(value=API_URL)
        model_var = tk.StringVar(value=MODEL)
        result_var = tk.StringVar(value="")

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        def apply_preset():
            ep = ENDPOINTS[endpoint_var.get()]
            url_var.set(ep["api_url"])
            model_var.set(ep["model"])

        ttk.Label(frm, text=S["lbl_endpoint"], font=("Microsoft YaHei UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        for i, key in enumerate(["public", "local"]):
            ttk.Radiobutton(frm, text=ENDPOINTS[key]["label"].get(UI_LANG, ENDPOINTS[key]["label"]["zh"]),
                            value=key, variable=endpoint_var, command=apply_preset).grid(row=1 + i, column=0, columnspan=2, sticky=tk.W, padx=12)

        ttk.Label(frm, text=S["lbl_url"]).grid(row=3, column=0, sticky=tk.W, pady=(12, 2))
        ttk.Entry(frm, textvariable=url_var, width=56).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=12)
        ttk.Label(frm, text=S["lbl_model"]).grid(row=5, column=0, sticky=tk.W, pady=(8, 2))
        ttk.Entry(frm, textvariable=model_var, width=56).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=12)

        ttk.Label(frm, textvariable=result_var, foreground="gray", wraplength=420).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=8, column=0, columnspan=2, pady=(12, 0), sticky=tk.W)

        test_btn = ttk.Button(btn_row, text=S["btn_test"])
        test_btn.pack(side=tk.LEFT, padx=(0, 8))

        def on_test():
            result_var.set(S["testing"])
            test_btn.configure(state=tk.DISABLED)

            def worker():
                ok, info = test_connection(url_var.get().strip(), model_var.get().strip())
                msg = S["conn_ok"].format(text=info) if ok else S["conn_fail"].format(e=info)
                win.after(0, lambda: (result_var.set(msg), test_btn.configure(state=tk.NORMAL)))

            threading.Thread(target=worker, daemon=True).start()

        def on_save():
            global API_URL, MODEL
            url = url_var.get().strip()
            model = model_var.get().strip()
            if not url or not model:
                messagebox.showwarning(S["warn_title"], S["warn_empty"], parent=win)
                return
            API_URL, MODEL = url, model
            _CONFIG.update({"endpoint": endpoint_var.get(), "api_url": url, "model": model})
            try:
                _save_config(_CONFIG)
            except Exception as e:
                messagebox.showwarning(S["warn_title"], S["warn_save_fail"].format(e=e), parent=win)
            refresh_title()
            set_status(S["status_saved"])
            win.destroy()

        test_btn.configure(command=on_test)
        ttk.Button(btn_row, text=S["btn_save"], command=on_save).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text=S["btn_cancel"], command=win.destroy).pack(side=tk.LEFT)

    # ---------- 使用教程窗口 ----------
    def open_tutorial():
        win = tk.Toplevel(root)
        win.title(S["btn_tutorial"])
        win.geometry("620x560")
        txt = tk.Text(win, wrap=tk.WORD, font=("Microsoft YaHei UI", 10), padx=12, pady=12)
        txt.insert("1.0", TUTORIAL.get(UI_LANG, TUTORIAL["zh"]))
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(txt, command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------- 关于窗口 ----------
    def open_about():
        import webbrowser
        win = tk.Toplevel(root)
        win.title(S["btn_about"])
        win.transient(root)
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text=f"{S['app_title']}  v{__version__}", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(frm, text=S["about_body"], justify=tk.LEFT).pack(anchor=tk.W, pady=4)
        ttk.Button(frm, text=S["about_link"],
                   command=lambda: webbrowser.open("https://github.com/bilibili/Index-Translate")).pack(anchor=tk.W, pady=(8, 0))

    # ---------- 界面构建（语言切换时整体重建） ----------
    def build_ui():
        # 重建前保住正在编辑的内容
        if "src_txt" in refs:
            state["src_text"] = refs["src_txt"].get("1.0", tk.END)
            state["dst_text"] = refs["dst_txt"].get("1.0", tk.END)
            state["img_result"] = refs["img_result_txt"].get("1.0", tk.END)
            state["tab"] = refs["notebook"].index(refs["notebook"].select())
        for w in root.winfo_children():
            w.destroy()
        refs.clear()

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
        refs["notebook"] = notebook

        # ===== 图片翻译页 =====
        tab_img = ttk.Frame(notebook, padding=8)
        notebook.add(tab_img, text=S["tab_image"])

        img_top = ttk.Frame(tab_img)
        img_top.pack(fill=tk.X)

        preview_lbl = ttk.Label(tab_img, text=S["preview_empty"], anchor=tk.CENTER)
        preview_lbl.pack(fill=tk.X, pady=4)
        refs["preview_lbl"] = preview_lbl

        def load_image(img, source_desc):
            state["png_bytes"] = normalize_image(img)
            thumb = img.copy()
            thumb.thumbnail((720, 240))
            state["preview_img"] = ImageTk.PhotoImage(thumb)
            refs["preview_lbl"].configure(image=state["preview_img"], text="")
            set_status(S["status_loaded"].format(src=source_desc))

        def on_pick_file():
            path = filedialog.askopenfilename(
                title=S["btn_pick"],
                filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with Image.open(path) as img:
                    load_image(img, path)
            except Exception as e:
                messagebox.showerror(S["err_title"], S["err_read_image"].format(e=e))

        def on_clipboard():
            try:
                data = ImageGrab.grabclipboard()
            except Exception as e:
                messagebox.showerror(S["err_title"], S["err_clipboard"].format(e=e))
                return
            if data is None:
                set_status(S["status_no_clip"])
                return
            if isinstance(data, list):  # 剪贴板里是文件路径
                try:
                    with Image.open(data[0]) as img:
                        load_image(img, data[0])
                except Exception as e:
                    messagebox.showerror(S["err_title"], S["err_clip_file"].format(e=e))
                return
            load_image(data, "clipboard" if UI_LANG == "en" else "来自剪贴板")

        def do_translate_image():
            if not state["png_bytes"]:
                messagebox.showinfo(S["warn_title"], S["msg_no_image"])
                return
            target = img_lang_var.get()
            img_result_txt.delete("1.0", tk.END)
            run_async(lambda: translate_image(state["png_bytes"], target),
                      lambda text: img_result_txt.insert("1.0", text),
                      S["status_busy_img"])

        def on_copy_image():
            text = img_result_txt.get("1.0", tk.END).strip()
            if text:
                root.clipboard_clear()
                root.clipboard_append(text)
                set_status(S["status_copied"])

        ttk.Button(img_top, text=S["btn_pick"], command=on_pick_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(img_top, text=S["btn_clipboard"], command=on_clipboard).pack(side=tk.LEFT, padx=4)
        ttk.Label(img_top, text=S["lbl_target"]).pack(side=tk.LEFT, padx=(16, 4))
        img_lang_var = tk.StringVar(value="中文")
        ttk.Combobox(img_top, textvariable=img_lang_var, values=LANG_NAMES, width=8, state="readonly").pack(side=tk.LEFT)
        ttk.Button(img_top, text=S["btn_translate"], command=do_translate_image).pack(side=tk.LEFT, padx=16)
        ttk.Button(img_top, text=S["btn_copy"], command=on_copy_image).pack(side=tk.LEFT, padx=4)

        img_result_txt = tk.Text(tab_img, wrap=tk.WORD, font=("Microsoft YaHei UI", 11), height=10)
        img_result_txt.pack(fill=tk.BOTH, expand=True, pady=4)
        refs["img_result_txt"] = img_result_txt

        # ===== 文本翻译页 =====
        tab_txt = ttk.Frame(notebook, padding=8)
        notebook.add(tab_txt, text=S["tab_text"])

        txt_top = ttk.Frame(tab_txt)
        txt_top.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(txt_top, text=S["lbl_src"]).pack(side=tk.LEFT)

        src_txt = tk.Text(tab_txt, wrap=tk.WORD, font=("Microsoft YaHei UI", 11), height=8)
        src_txt.pack(fill=tk.BOTH, expand=True)
        refs["src_txt"] = src_txt

        txt_mid = ttk.Frame(tab_txt)
        txt_mid.pack(fill=tk.X, pady=4)
        ttk.Label(txt_mid, text=S["lbl_target"]).pack(side=tk.LEFT, padx=(0, 4))
        txt_lang_var = tk.StringVar(value="中文")
        ttk.Combobox(txt_mid, textvariable=txt_lang_var, values=LANG_NAMES, width=8, state="readonly").pack(side=tk.LEFT)

        def do_translate_text():
            text = src_txt.get("1.0", tk.END).strip()
            if not text:
                messagebox.showinfo(S["warn_title"], S["msg_no_text"])
                return
            target = txt_lang_var.get()
            dst_txt.delete("1.0", tk.END)
            run_async(lambda: translate_text(text, target),
                      lambda result: dst_txt.insert("1.0", result),
                      S["status_busy_txt"])

        def on_swap():
            """把译文放回原文框，方便接力翻译。"""
            result = dst_txt.get("1.0", tk.END).strip()
            if result:
                src_txt.delete("1.0", tk.END)
                src_txt.insert("1.0", result)

        def on_copy_text():
            text = dst_txt.get("1.0", tk.END).strip()
            if text:
                root.clipboard_clear()
                root.clipboard_append(text)
                set_status(S["status_copied"])

        ttk.Button(txt_mid, text=S["btn_translate_text"], command=do_translate_text).pack(side=tk.LEFT, padx=16)
        ttk.Button(txt_mid, text=S["btn_swap"], command=on_swap).pack(side=tk.LEFT, padx=4)
        ttk.Button(txt_mid, text=S["btn_copy"], command=on_copy_text).pack(side=tk.LEFT, padx=4)

        ttk.Label(tab_txt, text=S["lbl_dst"]).pack(anchor=tk.W)
        dst_txt = tk.Text(tab_txt, wrap=tk.WORD, font=("Microsoft YaHei UI", 11), height=8)
        dst_txt.pack(fill=tk.BOTH, expand=True)
        refs["dst_txt"] = dst_txt

        src_txt.bind("<Control-Return>", lambda e: (do_translate_text(), "break"))

        # ---------- 底部全局按钮与状态栏 ----------
        bottom = ttk.Frame(root, padding=(8, 4))
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text=S["btn_settings"], command=open_settings).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text=S["btn_tutorial"], command=open_tutorial).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text=S["btn_about"], command=open_about).pack(side=tk.LEFT, padx=4)

        ttk.Label(bottom, text=S["lbl_ui_lang"]).pack(side=tk.LEFT, padx=(24, 4))
        lang_display_var = tk.StringVar(value="中文" if UI_LANG == "zh" else "English")
        lang_var_holder.var = lang_display_var
        ui_lang_box = ttk.Combobox(bottom, textvariable=lang_display_var, values=["中文", "English"],
                                   width=8, state="readonly")
        ui_lang_box.pack(side=tk.LEFT)
        ui_lang_box.bind("<<ComboboxSelected>>", on_ui_lang_change)

        status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 恢复重建前的内容
        if state["preview_img"] is not None:
            preview_lbl.configure(image=state["preview_img"], text="")
        if state["img_result"].strip():
            img_result_txt.insert("1.0", state["img_result"])
        if state["src_text"].strip():
            src_txt.insert("1.0", state["src_text"])
        if state["dst_text"].strip():
            dst_txt.insert("1.0", state["dst_text"])
        notebook.select(state["tab"])

    # ---------- 界面语言实时切换 ----------
    def on_ui_lang_change(*_):
        global S, UI_LANG
        lang = "en" if refs["notebook"] and lang_var_holder.get() == "English" else "zh"
        if lang == UI_LANG:
            return
        UI_LANG = lang
        S = STR[lang]
        _CONFIG["ui_lang"] = lang
        try:
            _save_config(_CONFIG)
        except Exception:
            pass
        refresh_title()
        build_ui()
        set_status(S["status_lang"])

    # 语言下拉框每次重建都会重新生成，用 holder 传递当前选中值
    class _Holder:
        def __init__(self):
            self.var = None

        def get(self):
            return self.var.get() if self.var else ("English" if UI_LANG == "en" else "中文")

    lang_var_holder = _Holder()

    build_ui()
    root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv or "--text" in sys.argv:
        cli_main()
    else:
        gui_main()
