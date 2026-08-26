"""A4 打印单 → PDF。

和老站的差别只有一条，但很关键：**Chrome 路径是探测出来的，不是写死的**。
老站三科都硬编码 /Applications/Google Chrome.app/...，
所以只能在这台 mac 上生成 PDF，GitHub Actions 的 ubuntu runner 一跑就炸。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# 按优先级探测。环境变量 CHROME 最高，方便本地临时换浏览器
_MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
_PATH_CANDIDATES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
]


def find_chrome() -> str | None:
    """找一个能用的 Chrome/Chromium，找不到返回 None。"""
    env = os.environ.get("CHROME")
    if env and Path(env).exists():
        return env

    for p in _MAC_CANDIDATES:
        if Path(p).exists():
            return p

    for name in _PATH_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found

    return None


def to_pdf(html_path: str | Path, pdf_path: str | Path, *, quiet: bool = False) -> bool:
    """把本地 HTML 导成 A4 PDF。成功返回 True。

    找不到 Chrome 时**不报错退出** —— 只跳过 PDF、留下 HTML。
    页面本身能看，PDF 是附加产物，不该因为环境缺浏览器就让整个构建失败。
    """
    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome()
    if not chrome:
        if not quiet:
            print(f"  ⚠️  没找到 Chrome，跳过 PDF：{pdf_path.name}"
                  f"（可设环境变量 CHROME=/path/to/chrome）", file=sys.stderr)
        return False

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",              # CI 里以 root 跑必须加
        "--no-pdf-header-footer",    # 不要页眉的 URL 和页脚的页码
        "--virtual-time-budget=3000",  # 等样式/字体落地再截
        f"--print-to-pdf={pdf_path.resolve()}",
        html_path.as_uri(),
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not pdf_path.exists():
        if not quiet:
            print(f"  ✗ 导 PDF 失败：{pdf_path.name}\n{r.stderr.strip()[:400]}", file=sys.stderr)
        return False

    if not quiet:
        kb = pdf_path.stat().st_size // 1024
        print(f"  → {pdf_path}  ({kb} KB)")
    return True
