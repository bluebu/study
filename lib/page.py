"""HTML 页面骨架 —— 全站每一页都从这里出去。

把 <head> 里那堆容易漏的东西（viewport / og / favicon / 资产链接）
收成一处。老站是每个栏目模板各抄一份，漏一行就少一个分享缩略图。
"""

from __future__ import annotations

import html
from pathlib import Path

# og:title / og:description 逐字照抄本页 title / description。
# 这是老站定下来的约定：微信/群里分享出去的卡片和页面标题必须一致。


def render(
    *,
    title: str,
    description: str = "",
    body: str = "",
    emoji: str = "📚",
    theme: str = "#FBF6EB",
    css: tuple[str, ...] | list[str] = (),
    root: str = ".",
    noindex: bool = False,
    lang: str = "zh-CN",
    extra_head: str = "",
) -> str:
    """渲染一整页 HTML。

    title/description  —— 同时用于 <title>/<meta> 和 og:*，别分开写
    css                —— assets/ 下要额外引的样式（palette.css 总是引）
    root               —— 本页到站点根的相对路径（根上是 "."，子目录是 ".."）
    noindex            —— 打印讲义这类不想被搜到的页面设 True，
                          用 meta 而不是 robots.txt Disallow
                          （Disallow 会让爬虫读不到 noindex，反而收录）
    """
    t = html.escape(title)
    d = html.escape(description)

    sheets = ["palette.css", *css]
    links = "\n".join(f'<link rel="stylesheet" href="{root}/assets/{s}" />' for s in sheets)

    robots = '\n<meta name="robots" content="noindex, nofollow, noarchive" />' if noindex else ""
    desc = f'\n<meta name="description" content="{d}" />' if d else ""
    og_desc = f'\n<meta property="og:description" content="{d}" />' if d else ""

    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>{t}</title>{desc}{robots}
<meta name="theme-color" content="{theme}" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{t}" />{og_desc}
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>{emoji}</text></svg>" />
{links}
{extra_head}</head>
<body>
{body}
</body>
</html>
"""


def write(path: str | Path, content: str) -> Path:
    """写文件，顺手建目录。返回写好的路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
