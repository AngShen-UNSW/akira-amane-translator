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

__version__ = "0.2.0"

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
【Akira&Amane的翻译小软件 - 使用教程】

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
[Akira&Amane Translator - Help]

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
    from tkinter import filedialog, messagebox
    import customtkinter as ctk
    from PIL import Image, ImageGrab

    global S, UI_LANG

    # 小清新粉色系配色
    PINK = "#FF8FB5"          # 主按钮粉
    PINK_HOVER = "#FF6FA3"
    PINK_SOFT = "#FFE4EE"     # 次按钮浅粉
    PINK_SOFT_HOVER = "#FFD5E4"
    BG = "#FFF7FA"            # 窗口背景：腮红粉白
    CARD = "#FFFFFF"          # 卡片/标签页体：纯白
    TEXT = "#5C4350"          # 柔和深梅灰文字
    BORDER = "#F2CBDC"        # 输入框浅粉描边
    STATUS_BG = "#FFE9F1"     # 状态栏

    ctk.set_appearance_mode("light")

    root = ctk.CTk(fg_color=BG)
    root.geometry("820x760")

    # 运行窗口图标（打包时 --add-data 会把 icon.ico 放进 _MEIPASS）
    try:
        _base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        root.iconbitmap(os.path.join(_base, "icon.ico"))
    except Exception:
        pass

    state = {"png_bytes": None, "pil_img": None, "ctk_img": None, "busy": False,
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

    def pink_btn(master, text, command, primary=False, **kw):
        return ctk.CTkButton(
            master, text=text, command=command, corner_radius=8,
            fg_color=PINK if primary else PINK_SOFT,
            hover_color=PINK_HOVER if primary else PINK_SOFT_HOVER,
            text_color="#FFFFFF" if primary else "#B04A72",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13,
                             weight="bold" if primary else "normal"),
            **kw)

    # ---------- 接口设置窗口 ----------
    def open_settings():
        global API_URL, MODEL
        win = ctk.CTkToplevel(root, fg_color=BG)
        win.title(S["settings_title"])
        win.transient(root)
        win.after(150, lambda: (win.lift(), win.attributes("-topmost", True),
                                win.attributes("-topmost", False), win.focus_force(),
                                win.grab_set()))
        win.resizable(False, False)

        endpoint_var = tk.StringVar(value=_CONFIG.get("endpoint", "public"))
        result_var = tk.StringVar(value="")

        frm = ctk.CTkFrame(win, fg_color="transparent")
        frm.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        ctk.CTkLabel(frm, text=S["lbl_endpoint"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold")).pack(anchor=tk.W, pady=(0, 8))

        def apply_preset():
            ep = ENDPOINTS[endpoint_var.get()]
            url_entry.delete(0, tk.END)
            url_entry.insert(0, ep["api_url"])
            model_entry.delete(0, tk.END)
            model_entry.insert(0, ep["model"])

        for key in ["public", "local"]:
            ctk.CTkRadioButton(frm, text=ENDPOINTS[key]["label"].get(UI_LANG, ENDPOINTS[key]["label"]["zh"]),
                               value=key, variable=endpoint_var, command=apply_preset,
                               fg_color=PINK, hover_color=PINK_HOVER).pack(anchor=tk.W, pady=2)

        ctk.CTkLabel(frm, text=S["lbl_url"]).pack(anchor=tk.W, pady=(12, 2))
        url_entry = ctk.CTkEntry(frm, width=460, fg_color=CARD, border_color=BORDER, text_color=TEXT)
        url_entry.pack(anchor=tk.W)
        url_entry.insert(0, API_URL)
        ctk.CTkLabel(frm, text=S["lbl_model"]).pack(anchor=tk.W, pady=(8, 2))
        model_entry = ctk.CTkEntry(frm, width=460, fg_color=CARD, border_color=BORDER, text_color=TEXT)
        model_entry.pack(anchor=tk.W)
        model_entry.insert(0, MODEL)

        ctk.CTkLabel(frm, textvariable=result_var, text_color="gray", wraplength=440).pack(anchor=tk.W, pady=(10, 0))

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.pack(anchor=tk.W, pady=(12, 0))

        test_btn = pink_btn(btn_row, S["btn_test"], None)
        test_btn.pack(side=tk.LEFT, padx=(0, 8))

        def on_test():
            result_var.set(S["testing"])
            test_btn.configure(state=tk.DISABLED)

            def worker():
                ok, info = test_connection(url_entry.get().strip(), model_entry.get().strip())
                msg = S["conn_ok"].format(text=info) if ok else S["conn_fail"].format(e=info)
                win.after(0, lambda: (result_var.set(msg), test_btn.configure(state=tk.NORMAL)))

            threading.Thread(target=worker, daemon=True).start()

        def on_save():
            global API_URL, MODEL
            url = url_entry.get().strip()
            model = model_entry.get().strip()
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
        pink_btn(btn_row, S["btn_save"], on_save, primary=True).pack(side=tk.LEFT, padx=8)
        pink_btn(btn_row, S["btn_cancel"], win.destroy).pack(side=tk.LEFT)

    # ---------- 使用教程窗口 ----------
    def open_tutorial():
        win = ctk.CTkToplevel(root, fg_color=BG)
        win.title(S["btn_tutorial"])
        win.geometry("640x580")
        win.after(150, lambda: (win.lift(), win.attributes("-topmost", True),
                                win.attributes("-topmost", False), win.focus_force()))
        box = ctk.CTkTextbox(win, wrap="word", font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), fg_color=CARD, text_color=TEXT, border_width=1, border_color=BORDER)
        box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        box.insert("1.0", TUTORIAL.get(UI_LANG, TUTORIAL["zh"]))
        box.configure(state=tk.DISABLED)

    # ---------- 关于窗口 ----------
    def open_about():
        import webbrowser
        win = ctk.CTkToplevel(root, fg_color=BG)
        win.title(S["btn_about"])
        win.transient(root)
        win.after(150, lambda: (win.lift(), win.attributes("-topmost", True),
                                win.attributes("-topmost", False), win.focus_force()))
        win.resizable(False, False)
        frm = ctk.CTkFrame(win, fg_color="transparent")
        frm.pack(fill=tk.BOTH, expand=True, padx=18, pady=16)
        ctk.CTkLabel(frm, text=f"{S['app_title']}  v{__version__}",
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold")).pack(anchor=tk.W)
        ctk.CTkLabel(frm, text=S["about_body"], justify=tk.LEFT,
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=12)).pack(anchor=tk.W, pady=6)
        pink_btn(frm, S["about_link"],
                 lambda: webbrowser.open("https://github.com/bilibili/Index-Translate")).pack(anchor=tk.W, pady=(8, 0))

    # ---------- 界面构建（语言切换时整体重建） ----------
    def build_ui():
        # 重建前保住正在编辑的内容
        if "src_box" in refs:
            state["src_text"] = refs["src_box"].get("1.0", tk.END)
            state["dst_text"] = refs["dst_box"].get("1.0", tk.END)
            state["img_result"] = refs["img_result_box"].get("1.0", tk.END)
            state["tab"] = 0 if refs["tabview"].get() == S["tab_image"].strip() else 1
        for w in root.winfo_children():
            w.destroy()
        refs.clear()

        tabview = ctk.CTkTabview(root, fg_color=CARD, corner_radius=10,
                                 segmented_button_fg_color=STATUS_BG,
                                 segmented_button_unselected_color=STATUS_BG,
                                 segmented_button_unselected_hover_color=PINK_SOFT_HOVER,
                                 segmented_button_selected_color=PINK,
                                 segmented_button_selected_hover_color=PINK_HOVER,
                                 text_color=TEXT)
        tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        tab_img = tabview.add(S["tab_image"].strip())
        tab_txt = tabview.add(S["tab_text"].strip())
        refs["tabview"] = tabview

        # ===== 图片翻译页 =====
        img_top = ctk.CTkFrame(tab_img, fg_color="transparent")
        img_top.pack(fill=tk.X, pady=(0, 6))

        preview_lbl = ctk.CTkLabel(tab_img, text=S["preview_empty"],
                                   font=ctk.CTkFont(family="Microsoft YaHei UI", size=12))
        preview_lbl.pack(fill=tk.X, pady=4)
        refs["preview_lbl"] = preview_lbl

        def load_image(img, source_desc):
            state["png_bytes"] = normalize_image(img)
            state["pil_img"] = img.copy()
            thumb = img.copy()
            thumb.thumbnail((700, 220))
            state["ctk_img"] = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            refs["preview_lbl"].configure(image=state["ctk_img"], text="")
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
            img_result_box.delete("1.0", tk.END)
            run_async(lambda: translate_image(state["png_bytes"], target),
                      lambda text: img_result_box.insert("1.0", text),
                      S["status_busy_img"])

        def on_copy_image():
            text = img_result_box.get("1.0", tk.END).strip()
            if text:
                root.clipboard_clear()
                root.clipboard_append(text)
                set_status(S["status_copied"])

        pink_btn(img_top, S["btn_pick"], on_pick_file).pack(side=tk.LEFT, padx=4)
        pink_btn(img_top, S["btn_clipboard"], on_clipboard).pack(side=tk.LEFT, padx=4)
        ctk.CTkLabel(img_top, text=S["lbl_target"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), text_color=TEXT).pack(side=tk.LEFT, padx=(16, 4))
        img_lang_var = tk.StringVar(value="中文")
        ctk.CTkComboBox(img_top, variable=img_lang_var, values=LANG_NAMES, width=100, state="readonly", fg_color=CARD, border_color=BORDER, text_color=TEXT,
                        button_color=PINK, button_hover_color=PINK_HOVER,
                        dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                        dropdown_hover_color=PINK_SOFT).pack(side=tk.LEFT)
        pink_btn(img_top, S["btn_translate"], do_translate_image, primary=True).pack(side=tk.LEFT, padx=16)
        pink_btn(img_top, S["btn_copy"], on_copy_image).pack(side=tk.LEFT, padx=4)

        img_result_box = ctk.CTkTextbox(tab_img, wrap="word",
                                        font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
                                        fg_color=CARD, text_color=TEXT, border_width=1, border_color=BORDER)
        img_result_box.pack(fill=tk.BOTH, expand=True, pady=4)
        refs["img_result_box"] = img_result_box

        # ===== 文本翻译页 =====
        ctk.CTkLabel(tab_txt, text=S["lbl_src"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), text_color=TEXT).pack(anchor=tk.W, pady=(0, 4))

        src_box = ctk.CTkTextbox(tab_txt, wrap="word", height=150,
                                 font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
                                 fg_color=CARD, text_color=TEXT, border_width=1, border_color=BORDER)
        src_box.pack(fill=tk.BOTH, expand=True)
        refs["src_box"] = src_box

        txt_mid = ctk.CTkFrame(tab_txt, fg_color="transparent")
        txt_mid.pack(fill=tk.X, pady=6)
        ctk.CTkLabel(txt_mid, text=S["lbl_target"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), text_color=TEXT).pack(side=tk.LEFT, padx=(0, 4))
        txt_lang_var = tk.StringVar(value="中文")
        ctk.CTkComboBox(txt_mid, variable=txt_lang_var, values=LANG_NAMES, width=100, state="readonly", fg_color=CARD, border_color=BORDER, text_color=TEXT,
                        button_color=PINK, button_hover_color=PINK_HOVER,
                        dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                        dropdown_hover_color=PINK_SOFT).pack(side=tk.LEFT)

        def do_translate_text():
            text = src_box.get("1.0", tk.END).strip()
            if not text:
                messagebox.showinfo(S["warn_title"], S["msg_no_text"])
                return
            target = txt_lang_var.get()
            dst_box.delete("1.0", tk.END)
            run_async(lambda: translate_text(text, target),
                      lambda result: dst_box.insert("1.0", result),
                      S["status_busy_txt"])

        def on_swap():
            """把译文放回原文框，方便接力翻译。"""
            result = dst_box.get("1.0", tk.END).strip()
            if result:
                src_box.delete("1.0", tk.END)
                src_box.insert("1.0", result)

        def on_copy_text():
            text = dst_box.get("1.0", tk.END).strip()
            if text:
                root.clipboard_clear()
                root.clipboard_append(text)
                set_status(S["status_copied"])

        pink_btn(txt_mid, S["btn_translate_text"], do_translate_text, primary=True).pack(side=tk.LEFT, padx=16)
        pink_btn(txt_mid, S["btn_swap"], on_swap).pack(side=tk.LEFT, padx=4)
        pink_btn(txt_mid, S["btn_copy"], on_copy_text).pack(side=tk.LEFT, padx=4)

        ctk.CTkLabel(tab_txt, text=S["lbl_dst"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), text_color=TEXT).pack(anchor=tk.W)
        dst_box = ctk.CTkTextbox(tab_txt, wrap="word", height=150,
                                 font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
                                 fg_color=CARD, text_color=TEXT, border_width=1, border_color=BORDER)
        dst_box.pack(fill=tk.BOTH, expand=True)
        refs["dst_box"] = dst_box

        src_box.bind("<Control-Return>", lambda e: (do_translate_text(), "break"))

        # ---------- 底部全局按钮与状态栏 ----------
        bottom = ctk.CTkFrame(root, fg_color="transparent")
        bottom.pack(fill=tk.X, padx=10, pady=6)
        pink_btn(bottom, S["btn_settings"], open_settings).pack(side=tk.LEFT, padx=4)
        pink_btn(bottom, S["btn_tutorial"], open_tutorial).pack(side=tk.LEFT, padx=4)
        pink_btn(bottom, S["btn_about"], open_about).pack(side=tk.LEFT, padx=4)

        ctk.CTkLabel(bottom, text=S["lbl_ui_lang"],
                     font=ctk.CTkFont(family="Microsoft YaHei UI", size=13), text_color=TEXT).pack(side=tk.LEFT, padx=(24, 4))
        lang_display_var = tk.StringVar(value="中文" if UI_LANG == "zh" else "English")
        lang_var_holder.var = lang_display_var
        ctk.CTkComboBox(bottom, variable=lang_display_var, values=["中文", "English"], width=100,
                        state="readonly", command=on_ui_lang_change, fg_color=CARD, border_color=BORDER,
                        text_color=TEXT, button_color=PINK, button_hover_color=PINK_HOVER,
                        dropdown_fg_color=CARD, dropdown_text_color=TEXT,
                        dropdown_hover_color=PINK_SOFT).pack(side=tk.LEFT)

        status_bar = ctk.CTkLabel(root, textvariable=status_var, anchor=tk.W,
                                  font=ctk.CTkFont(family="Microsoft YaHei UI", size=11),
                                  fg_color=STATUS_BG, text_color="#A64B70", corner_radius=6)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 8))

        # 恢复重建前的内容
        if state["ctk_img"] is not None:
            preview_lbl.configure(image=state["ctk_img"], text="")
        if state["img_result"].strip():
            img_result_box.insert("1.0", state["img_result"])
        if state["src_text"].strip():
            src_box.insert("1.0", state["src_text"])
        if state["dst_text"].strip():
            dst_box.insert("1.0", state["dst_text"])
        tabview.set(S["tab_image"].strip() if state["tab"] == 0 else S["tab_text"].strip())

    # ---------- 界面语言实时切换 ----------
    def on_ui_lang_change(*_):
        global S, UI_LANG
        lang = "en" if lang_var_holder.get() == "English" else "zh"
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

    # 测试钩子：设置 IT_TEST_TUTORIAL=1 时自动打开教程窗口后退出
    if os.environ.get("IT_TEST_TUTORIAL"):
        root.after(500, open_tutorial)
        root.after(2500, root.destroy)

    root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv or "--text" in sys.argv:
        cli_main()
    else:
        gui_main()
