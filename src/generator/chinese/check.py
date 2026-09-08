"""语文 · 抽查单 —— 学完一课，家长照着单子问一遍，十分钟知道哪儿没记住。

spec 在 storage/spec/chinese/check/<课号>.txt，产物落在 dist/chinese/check/：

    <课号>.html / .pdf   一课一张，答案全印（家长照着问、照着改）
    index.html           目录页（一条一课，右边挂「打印单」）

**一份 spec 只出一版。** 原先出两版（答案不印的「题面版」+ 答案全印的
「家长版」），但家长照着问的永远是印答案那份，孩子手上不需要一张
写着题目的纸 —— 两版并存只是让目录页多一个按钮、PDF 多一份。

**一课一张，一张一页。** 混着问，孩子累，也看不出是哪一课没记住。
spec 按课号命名：`01.txt` = 第 1 课；语文园地写 `<课号>y`，**严格照课本目录
排在它所属单元最后一课的后面** —— `03y` 是语文园地一（第一单元末，第 3 课后），
不是「所有园地堆到最后」。目录页的顺序就是 `_order()` 算出来的这个顺序。

区块内四种行（`lib/spec.py` 只解析骨架，这几行的语义是这个栏目自己的）：

    note:   块说明，灰色小字
    汉字=答案  网格项，两列排，一项一个勾选框（`,` `，` `、` 分隔，可跨行写）
    ask: 题面 | 参考答案     整行问答，题面或答案长的用它
    lines: N                留 N 条空白横线，配 `answer:` 写参考答案

`=` 右边的答案、`ask` 的答案、`answer:` 都印出来；听写的空白横线压到一行
（够家长记个错字，不是给孩子写字用的）。
"""

from __future__ import annotations

import re
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "check")

DEFAULTS = {"title": "抽查单"}

# 区块内的 key: 行。**其余非空行都是网格项** —— 所以这四个名字是保留的
KEYS = ("note", "answer", "lines", "ask")


def _block(b: spec_lib.Block, sp: spec_lib.Spec) -> dict:
    """一个 [题块] → 模板要的形状。

    键叫 `grid` 不叫 `items`：Jinja 的 `a.b` 先找属性，`b.items` 会拿到 dict
    自带的方法（`lib/tmpl.py` 的第三条）。`pass_` 同理避开 Python 关键字。
    """
    out = {"name": b.name, "head": b.head,
           "time": b.attr("time", ""), "pass_": b.attr("pass", ""),
           "note": "", "answer": "", "lines": 0, "grid": [], "asks": []}
    cells: list[str] = []

    for raw in b.lines:
        line = raw.strip()
        if not line:
            continue
        key, sep, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if sep and key in KEYS:
            if key == "lines":
                if not val.isdigit():
                    spec_lib.die(f"{sp.path.name}「{b.name}」的 lines: 要写数字，"
                                 f"现在是 {val!r}")
                out["lines"] = int(val)
            elif key == "ask":
                q, _, a = val.partition("|")
                out["asks"].append({"q": q.strip(), "a": a.strip()})
            else:
                out[key] = val
            continue
        cells.append(line)

    for chunk in re.split(f"[{re.escape(spec_lib.ITEM_SEPS)}]", " ".join(cells)):
        chunk = chunk.strip()
        if not chunk:
            continue
        q, _, a = chunk.partition("=")
        out["grid"].append({"q": q.strip(), "a": a.strip()})

    if not (out["grid"] or out["asks"] or out["lines"]):
        spec_lib.die(f"{sp.path.name}「{b.name}」是空的："
                     f"至少要有网格项、ask: 或 lines:")
    return out


def _label(stem: str, lesson: str = "") -> str:
    """文件名 → 课次名。`01` → 第 1 课；`03y` → 语文园地（名字取 spec 的 lesson:）。"""
    if re.fullmatch(r"\d{1,2}", stem):
        return f"第 {int(stem)} 课"
    if re.fullmatch(r"\d{1,2}y", stem):
        return lesson or "语文园地"
    return stem


def _order(path: Path) -> tuple:
    """照课本目录排：语文园地跟在它所属单元最后一课后面。

    `03y` = 第 3 课之后的语文园地一 → 排在 `03` 和 `04` 之间。
    """
    m = re.fullmatch(r"(\d{1,2})(y?)", path.stem)
    if m:
        return (0, int(m.group(1)), 1 if m.group(2) else 0)
    return (1, 0, 0)


def _render(sp: spec_lib.Spec, out_dir: Path, *, pdf: bool) -> bool:
    """渲染一份抽查单。返回 PDF 是否真的生成出来了。"""
    if not sp.blocks:
        spec_lib.die(f"{sp.path.name} 里没有任何 [题块]")

    blocks = [_block(b, sp) for b in sp.blocks]
    for b in blocks:
        # 听写的横线压到一行：够家长记个错字，不是给孩子写字用的
        b["ln"] = 1 if b["lines"] else 0
    total = sum(len(b["grid"]) + len(b["asks"]) + (1 if b["lines"] else 0)
                for b in blocks)

    heading = sp.get("title", DEFAULTS["title"])
    body = tmpl.body(
        "check/sheet.html",
        heading=heading,
        sub=sp.get("range", ""),
        minutes=sp.get("minutes", ""),
        hint=sp.get("hint", ""),           # 使用说明，印在页头下面
        blocks=blocks,
        total=total,
        tally=f"共 {len(blocks)} 题块 / {total} 项",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f'{heading}　{sp.get("range", "")}'.strip(),
            body=body,
            emoji="✅",
            css=("print.css", "check.css"),
            root="../..",
            noindex=True,          # 打印单不需要被搜索引擎收录
        ),
    )
    print(f"    → check/{out.name}  （{len(blocks)} 题块 / {total} 项）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="抽查单 · 语文",
        description="学完一课，家长照着单子问一遍，十分钟知道哪儿没记住。一课一张 A4。",
        emoji="✅",
        h1="抽查单",
        sub=f"一课一张，家长照着问 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有抽查单 —— 往 storage/spec/chinese/check/ 放一份 spec",
        accent="chinese",
    )
    print(f"    → check/index.html  （{len(entries)} 份）")


def build_check(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "check"
    specs = sorted(spec_lib.specs(SPECS), key=_order)
    if not specs:
        print("    · 抽查单：storage/spec/chinese/check/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok = _render(sp, out_dir, pdf=pdf)

        lesson = sp.get("lesson", "")
        label = _label(path.stem, lesson)
        if lesson and "园地" not in label:
            label += f"　{lesson}"
        entries.append({
            "href": f"{path.stem}.html",
            "label": label,
            "small": " ".join(b.name for b in sp.blocks),
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
