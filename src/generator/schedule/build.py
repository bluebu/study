"""课程表 —— 一周一张 A4，贴在书桌前，装书包照着带书。

    storage/spec/schedule/week/<YYYYMMDD>.txt
    → dist/schedule/week/<YYYYMMDD>.html + .pdf + index.html

一个区块是一天，区块内一行一节，从第 1 节顺着往下数：

    term: 2026 秋季学期
    am: 4                  ← 上午几节（第 4 节之后画午休那条虚线）

    [周一]
    语文
    数学
    体育
    班队会
    书法 | 英语老师        ← 「科目 | 备注」：这节是别科老师来上的
    道法

两条界限：

  · **科目名连括号一起照抄原表**：「书法（英）」「劳动（体）」「综实（数）」
    原样印，不展开成「综合实践」，也不把括号拆成一行小字备注。
    家长手里那张纸上写的就是这几个字，表上不一致就得两边核。
    括号是什么意思由 spec 的 `note:` 一句话说清（印在页脚）
  · 上色只给语数英三门（`MAIN`），副科一律中性。这张表天天回答的是
    「明天带哪几本书」—— 十四门课全上色就没有重点了

**纸上是 A4 横版**（`schedule.css` 覆盖 print.css 的竖版 `@page`）：
竖版一列只有 37mm，「书法（英）」这种带括号的名字就得缩字号才放得下。
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("schedule", "week")

# 科目 → 色板变量名。三科色沿用家族取值（palette.css 是单一真源）
MAIN = {"语文": "chinese", "数学": "math", "英语": "english"}

# 空节：spec 里写 - 或 — 都算
BLANK = {"-", "—", "－"}


# 一格课就是模板要的三个键，**别做成 @dataclass** —— 这个文件是被
# build.py 用 importlib 动态加载的顶层模块，没进 sys.modules，
# dataclasses 那边 `sys.modules.get(cls.__module__)` 会拿到 None 当场炸。
# （英语那边的 dataclass 没事：它们是 english/build.py 正常 import 进来的子模块。）
EMPTY = {"name": "", "who": "", "key": "", "long": False}


def cell(text: str) -> dict:
    """一行 spec → 一格课。`科目 | 备注`（备注可省），`-` 是空节。

    `long`：带括号的名字（「书法（英）」）比「语文」宽一倍，模板据此换小一档
    字号 —— 手机上一列只有 62px，不换档就顶出格子。**长度判断留在这儿，
    别写进 CSS**：CSS 量不到字数，只能靠类名。
    """
    name, _, who = text.partition("|")
    name = name.strip()
    if name in BLANK:
        return dict(EMPTY)
    return {"name": name, "who": who.strip(), "key": MAIN.get(name, ""),
            "long": len(name) >= 4}


def columns(sp: spec_lib.Spec) -> list[tuple[str, list[dict]]]:
    """每个 [区块] 是一天，区块内一行一节。"""
    out = []
    for block in sp.blocks:
        cells = [cell(ln.strip()) for ln in block.lines if ln.strip()]
        out.append((block.name, cells))
    if not out:
        spec_lib.die(f"{sp.path.name}：一天都没有（要有 [周一] 这样的区块）")
    return out


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int, int]:
    cols = columns(sp)
    periods = max(len(cells) for _, cells in cols)
    am = sp.int_("am", 0)

    # 一行是一节课，横着摆五天 —— 各天节数不一样就补空格，别让 grid 错位
    rows = [{"no": i + 1,
             "cells": [cells[i] if i < len(cells) else EMPTY for _, cells in cols]}
            for i in range(periods)]

    subjects = {c["name"] for r in rows for c in r["cells"] if c["name"]}
    heading = sp.title or "课程表"
    pm = periods - am
    meta = " · ".join(x for x in (
        f"{len(cols)} 天",
        f"每天 {periods} 节" if not am else f"上午 {am} 节 · 下午 {pm} 节",
        f"{len(subjects)} 门课") if x)

    body = tmpl.body(
        "schedule/sheet.html",
        heading=heading,
        meta=meta,
        term=sp.get("term", ""),
        days=[name for name, _ in cols],
        rows=rows,
        am=am,
        foot=sp.get("note", ""),
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} · {sp.get('term', '')}".rstrip(" ·"),
            description=f"一周 {len(cols)} 天 {periods} 节的课程表，"
                        f"{len(subjects)} 门课，语数英按三科色标出来。A4 打印。",
            body=body,
            emoji="🗓️",
            css=("print.css", "schedule.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → week/{out.name}  （{len(cols)} 天 · {periods} 节 · {len(subjects)} 门课）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, periods, len(subjects)


def build_index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="一周课表 · 课程表",
        description="一周的课程表，一张 A4 打印出来贴在书桌前，装书包照着带书。",
        emoji="🗓️",
        h1="一周课表",
        sub=f"一张纸看完一周，装书包照着带书 · 共 {len(entries)} 份",
        sections=[(None, [
            {"href": f'{e["stem"]}.html',
             "label": e["title"],
             "small": " · ".join(x for x in (e["term"], f'{e["periods"]} 节',
                                             f'{e["subjects"]} 门课') if x),
             "pdf": f'{e["stem"]}.pdf' if e["pdf"] else None}
            for e in entries])],
        empty="还没有课表 —— 往 storage/spec/schedule/week/ 放一份 spec",
        accent="c-drill",
        pdf_label="打印单",
    )
    print(f"    → week/index.html  （{len(entries)} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "week"
    specs = spec_lib.specs(SPECS, reverse=True)     # 新的排前面
    if not specs:
        print("    · 一周课表：storage/spec/schedule/week/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, periods, subjects = render(sp, out_dir, pdf)
        entries.append({"stem": path.stem, "title": sp.title or path.stem,
                        "term": sp.get("term", ""), "periods": periods,
                        "subjects": subjects, "pdf": pdf_ok})

    build_index(out_dir, entries)
