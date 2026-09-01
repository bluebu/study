"""HTML 页面骨架 —— 全站每一页都从这里出去。

把 <head> 里那堆容易漏的东西（viewport / og / favicon / 资产链接）
收成一处。老站是每个栏目模板各抄一份，漏一行就少一个分享缩略图。

标记在 `src/templates/page.html`，这儿只算「引哪几张样式、挂不挂页脚」。
"""

from __future__ import annotations

from pathlib import Path

from . import site, tmpl


def render(
    *,
    title: str,
    description: str = "",
    body: str = "",
    emoji: str = "📚",
    theme: str = "#FBF6EB",
    css: tuple[str, ...] | list[str] = (),
    js: tuple[str, ...] | list[str] = (),
    root: str = ".",
    noindex: bool = False,
    lang: str = "zh-CN",
    extra_head: str = "",
    footer: bool | None = None,
) -> str:
    """渲染一整页 HTML。

    title/description  —— 同时用于 <title>/<meta> 和 og:*，别分开写
    css                —— assets/ 下要额外引的样式
                          （palette.css 色板 + base.css 全站基线总是引）
    js                 —— assets/ 下要引的脚本，挂在 body 末尾、带 defer。
                          **全站几乎用不上** —— 页面是静态的，只有打卡评价
                          要点词听读音。别拿它做本来 CSS 就能做的事
    root               —— 本页到站点根的相对路径（根上是 "."，子目录是 ".."）
    noindex            —— 打印讲义这类不想被搜到的页面设 True，
                          用 meta 而不是 robots.txt Disallow
                          （Disallow 会让爬虫读不到 noindex，反而收录）
    footer             —— 备案号 + 访问统计那一条（配置在 lib/site.py）。
                          默认：**引了 print.css 的算打印单，不挂**，其余都挂。
                          noindex 的页面只出备案号、不挂统计
    """
    if footer is None:
        footer = "print.css" not in css
    foot = site.foot_html(analytics=not noindex) if footer else ""

    return tmpl.render(
        "page.html",
        title=title,
        description=description,
        body=body,
        emoji=emoji,
        theme=theme,
        sheets=["palette.css", "base.css", *css] + (["foot.css"] if foot else []),
        scripts=list(js),
        root=root,
        noindex=noindex,
        lang=lang,
        extra_head=extra_head,
        foot=foot,
    )


def sheet_info(third: str = "得分", *, show: bool = True) -> str:
    """打印单页眉右边那行「姓名 ___ 日期 ___ <third> ___」。

    三个栏目共用（语文 / 数学 / 词汇默写），第三格的名字不同（得分 / 用时）。
    原先各栏目存一份 INFO 常量，改一处要改三个文件。
    """
    return tmpl.render("sheet-info.html", third=third, show=show).rstrip("\n")


def listing(
    out_dir: str | Path,
    *,
    title: str,
    description: str,
    emoji: str,
    h1: str,
    sub: str,
    sections: list[tuple[str | None, list[dict]]],
    empty: str = "",
    pdf_label: str = "打印单",
    accent: str | None = None,
    back_href: str = "../../",
    back_label: str = "学习小站",
    root: str = "../..",
) -> Path:
    """写一个栏目的目录页（`src/templates/list.html`）。

    五个栏目的目录页是同一张页面，原先各拼一遍 —— 改一处 hero 要改五个文件。
    这儿只做两件事：把条目补齐成模板要的形状、把 sections 的元组换成有名字的字段。

    sections   —— [(小标题 或 None, [条目…])]。只有词汇默写分了组，
                  其余栏目传一节、小标题给 None
    条目       —— {href, label, small, pdf}，`pdf` 给 None 就不出打印单按钮
    empty      —— 一条都没有时显示的话（「往 …/ 放一份 spec」）
    """
    # 键叫 rows 不叫 items —— Jinja 的 `sec.items` 会取到 dict 自带的方法
    secs = [
        {"title": name,
         "rows": [{"href": it["href"], "label": it["label"],
                   "small": it.get("small", ""), "pdf": it.get("pdf")}
                  for it in items]}
        for name, items in sections
    ]
    body = tmpl.body(
        "list.html",
        accent=accent, back_href=back_href, back_label=back_label,
        h1=h1, sub=sub, sections=secs, empty=empty, pdf_label=pdf_label,
    )

    return write(
        Path(out_dir) / "index.html",
        render(title=title, description=description, body=body,
               emoji=emoji, css=("site.css",), root=root),
    )


def write(path: str | Path, content: str) -> Path:
    """写文件，顺手建目录。返回写好的路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
