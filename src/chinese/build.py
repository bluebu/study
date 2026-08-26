"""语文 · 今日练习 —— 看拼音写汉字的 A4 打印单。

spec 在 specs/<YYYYMMDD>.txt，产物落在 dist/chinese/practice/：

    <日期>.html / .pdf              题面版（格子空着）
    <日期>-answers.html / .pdf      答案版（格子里印楷体字，给家长批改）
    index.html                      目录页（**答案版不列进去**）

这个栏目的核心职责是**标对拼音**，也是唯一容易出错的地方：
脚本只排版、不判断读音。多音字必须在 spec 里手写，按课文语境定音
（`单=dān` 不是 shàn、`悄悄=qiāo qiāo` 不是 qiǎo）。
"""

from __future__ import annotations

import html
from pathlib import Path

from lib import page, sheet, spec as spec_lib

HERE = Path(__file__).parent
SPECS = HERE / "specs"

# 排版旋钮的默认值。cell 和 copies 是「排满一页 A4」的两个主要旋钮：
# 装不满就加大，快溢出到第二页就调小。
DEFAULTS = {"title": "今日练习", "hint": "看拼音，在田字格里写汉字。",
            "copies": 1, "cell": 15, "gap": 4, "py": 11}

INFO = ('姓名 <span class="blank"></span> 日期 <span class="blank"></span> '
        '得分 <span class="blank"></span>')

try:                                     # 可选增强：只用来补单音字
    from pypinyin import Style, pinyin
except ImportError:
    pinyin = None


def _syllables(word: str, raw: str, sp: spec_lib.Spec) -> list[str]:
    """取一个词的拼音音节，并校验音节数 == 字数。"""
    syl = raw.split()

    if not syl:
        if pinyin is None:
            spec_lib.die(
                f"{sp.path.name}：「{word}」没写拼音，而且没装 pypinyin。\n"
                f"   请在 spec 里写 {word}=" + " ".join(["?"] * len(word)) +
                "\n   （或 pip3 install pypinyin，但多音字仍须手写）")
        syl = [s[0] for s in pinyin(word, style=Style.TONE)]

    if len(syl) != len(word):
        spec_lib.die(
            f"{sp.path.name}：「{word}={raw}」音节数 {len(syl)} 与字数 {len(word)} 不符。\n"
            f"   应该写成 {word}=" + " ".join(["?"] * len(word)))
    return syl


def _item(word: str, syl: list[str], copies: int, answers: bool) -> str:
    """一项 = 拼音行 + copies 行田字格。抄多遍时拼音只标在最上面一行。"""
    py = "".join(f"<span>{html.escape(s)}</span>" for s in syl)
    cells = "".join(
        '<div class="tian-row">'
        + "".join(f'<i class="tian">{html.escape(c) if answers else ""}</i>' for c in word)
        + "</div>"
        for _ in range(copies)
    )
    return f'<div class="item"><div class="py">{py}</div>{cells}</div>'


def _render(sp: spec_lib.Spec, out_dir: Path, *, pdf: bool, answers: bool) -> bool:
    """渲染一份练习单。返回 PDF 是否真的生成出来了。"""
    copies_all = sp.int_("copies", DEFAULTS["copies"])
    cell = sp.int_("cell", DEFAULTS["cell"])
    gap = sp.int_("gap", DEFAULTS["gap"])
    py_size = sp.int_("py", DEFAULTS["py"])

    if not sp.blocks:
        spec_lib.die(f"{sp.path.name} 里没有任何 [区块]")

    blocks, total = [], 0
    for b in sp.blocks:
        items = b.items()
        if not items:
            continue
        n = int(b.attr("copies", copies_all))
        rows = "\n      ".join(
            _item(w, _syllables(w, raw, sp), n, answers) for w, raw in items
        )
        label = html.escape(" ".join(x for x in (b.name, b.head) if x))
        blocks.append(
            f'  <div class="block">\n    <h2>{label}</h2>\n'
            f'    <div class="items">\n      {rows}\n    </div>\n  </div>'
        )
        total += len(items)

    heading = sp.get("title", DEFAULTS["title"]) + ("（答案）" if answers else "")
    if sp.get("date"):
        heading += f'　{sp.get("date")}'

    hint_text = sp.get("hint", DEFAULTS["hint"])
    hint = f'  <p class="hint">{html.escape(hint_text)}</p>\n' if hint_text and not answers else ""

    body = (
        f'<div class="sheet" style="--cell:{cell}mm; --gap:{gap}mm; --py:{py_size}px">\n'
        f'  <div class="head">\n'
        f'    <h1>{html.escape(heading)}</h1>\n'
        f'    <div class="info">{"" if answers else INFO}</div>\n'
        f"  </div>\n"
        f"{hint}"
        + "\n".join(blocks)
        + f'\n  <div class="foot">共 {total} 项</div>\n</div>'
    )

    name = sp.path.stem + ("-answers" if answers else "")
    out = page.write(
        out_dir / f"{name}.html",
        page.render(
            title=heading,
            body=body,
            emoji="📖",
            css=("print.css", "grid.css", "practice.css"),
            root="../..",
            noindex=True,          # 练习单不需要被搜索引擎收录
        ),
    )
    print(f"    → {out.relative_to(out.parent.parent.parent)}  （{total} 项）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


def _index(out_dir: Path, entries: list[dict]) -> None:
    """目录页。GitHub Pages 不列目录，所以必须自己生成一份。"""
    rows = "\n".join(
        f'    <li><a class="main" href="{e["href"]}">{html.escape(e["label"])}'
        f'<small>{html.escape(e["sub"])}</small></a>'
        + (f'<a class="pdf" href="{e["pdf"]}">打印单</a>' if e["pdf"] else "")
        + "</li>"
        for e in entries
    ) or '    <li><span class="empty">还没有练习单 —— 往 src/chinese/specs/ 放一份 spec</span></li>'

    body = f"""<main class="wrap">
  <header class="hero">
    <a class="back" href="../../">‹ 学习小站</a>
    <h1>今日练习</h1>
    <p class="sub">看拼音写汉字 · 共 {len(entries)} 份</p>
  </header>
  <ul class="list">
{rows}
  </ul>
</main>"""

    page.write(
        out_dir / "index.html",
        page.render(
            title="今日练习 · 语文",
            description="看拼音写汉字的 A4 打印单，点进去直接打印。",
            body=body,
            emoji="📖",
            css=("site.css",),
            root="../..",
        ),
    )
    print(f"    → practice/index.html  （{len(entries)} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "practice"
    specs = sorted(SPECS.glob("*.txt"), reverse=True)   # 新的排前面

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok = _render(sp, out_dir, pdf=pdf, answers=False)
        _render(sp, out_dir, pdf=pdf, answers=True)

        counts = {}
        for b in sp.blocks:
            if b.items():
                counts[b.name] = counts.get(b.name, 0) + len(b.items())
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("title", DEFAULTS["title"]) + (f'　{sp.get("date")}' if sp.get("date") else ""),
            "sub": " · ".join(f"{k} {v} 项" for k, v in counts.items()),
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
