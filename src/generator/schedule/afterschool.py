"""放学检查 —— 放学回来照着过一遍：作业抄没抄下来，三科逐项核。

    storage/spec/schedule/afterschool/<YYYYMMDD>.txt
    → dist/schedule/afterschool/<YYYYMMDD>.html + .pdf + index.html

**一天一张，打印一叠放书桌上。** 名字按学期起那天命名（和一周课表一样）——
作业类型一个学期不怎么变，变了改 spec 重出一叠。

顺序就是检查顺序，纸上第一栏上底色：

1. **作业抄下来了吗** —— 放学前要把老师留的作业抄在作业本上带回家。
   这一栏只做入口检查、**不编号也不再抄一遍**：作业本就是原始记录，
   照着它去填下面各科的横线。没抄下来，后面全是空的
2. **三科逐项过** —— 每一项两个格子：**今天留了** ｜ **已完成**。
   作业是这些项目的组合（语文那天可能是「小卷 + 生字本 + 背诵」），
   所以**每一项都要过一遍**：今天没留这一类，「今天留了」那格画一横 ——
   空着分不出「没留」和「没检查」。
   **项的顺序就是做的顺序**，纸上自动编号（预习、复习排在末尾）；
   项多的栏在 spec 里写 `cols=2` 排两列 —— 语文 9 项排一列要占 9 行
3. **收拾书包** —— 照明天的课表装，家长签字

spec 的形状：**一个区块 = 纸上一栏**，区块里两种行混着写都行 ——
缩进行是说明（每条前面一个圈），项行是作业类型（`,` `，` `、` 分隔）。
区块属性 `lines=N` 给这一栏留 N 行横线。想加一栏（比如「明天要带的东西」）
直接在 spec 里加区块，代码一行不用改。
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("schedule", "afterschool")

DEFAULTS = {"title": "放学检查"}


def _columns(sp: spec_lib.Spec) -> list[dict]:
    """区块 → 纸上一栏。说明行、项行、横线三样都是可选的。"""
    out = []
    for b in sp.blocks:
        # 项行的左边就是项目名（`小卷, 书后习题, 背`），没有 `=` 右边
        items = [left for left, _ in b.items() if left]
        lines = b.attr("lines", "0")
        if not str(lines).isdigit():
            spec_lib.die(f"{sp.path.name}：[{b.name}] 的 lines= 要写数字，"
                         f"现在是 {lines!r}")
        # 键叫 `rows` 不叫 `items` —— Jinja 的 `a.b` 先找属性，`col.items`
        # 会拿到 dict 自带的那个方法，渲染时当场 TypeError（`lib/tmpl.py`
        # 的第三条，这儿是第三次踩）
        cols = b.attr("cols", "1")
        if cols not in ("1", "2"):
            spec_lib.die(f"{sp.path.name}：[{b.name}] 的 cols= 只能是 1 或 2，"
                         f"现在是 {cols!r}")
        col = {"name": b.name, "head": b.head, "notes": b.notes(),
               "rows": items, "lines": int(lines), "cols": int(cols)}
        if col["notes"] or col["rows"] or col["lines"]:
            out.append(col)

    if not out:
        spec_lib.die(f"{sp.path.name} 里没有任何区块")

    # **第一栏不编号**：它是入口检查（作业抄没抄下来），不是清单里的一项 ——
    # 编号从三科那栏起，数出来的是「要逐项过的有几栏」
    for col in out:
        col["show_cols"] = False
        col["no"] = None
    for i, col in enumerate(out[1:], 1):
        col["no"] = i
    first = next((c for c in out if c["rows"]), None)
    if first:
        first["show_cols"] = True
    return out


def _render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, dict]:
    cols = _columns(sp)
    total = sum(len(c["rows"]) for c in cols)

    heading = sp.get("title", DEFAULTS["title"])
    body = tmpl.body(
        "afterschool/sheet.html",
        heading=heading,
        who=sp.get("who", "姓名"),
        columns=cols,
        total=total,
        tally=f"{len(cols)} 栏 / {total} 项",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} · {sp.get('term', '')}".rstrip(" ·"),
            description="放学回来照着过一遍：作业抄没抄下来，三科逐项核 ——"
                        "每项两个格子，今天留了 ｜ 已完成。A4 打印。",
            body=body,
            emoji="🎒",
            css=("print.css", "afterschool.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → afterschool/{out.name}  （{len(cols)} 栏 / {total} 项）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, {"cols": len(cols), "items": total}


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="放学检查 · 课程表",
        description="放学回来照着过一遍：作业抄没抄下来，三科逐项核。每项两个格子，今天留了 ｜ 已完成。",
        emoji="🎒",
        h1="放学检查",
        sub=f"作业抄没抄，三科逐项过 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有检查单 —— 往 storage/spec/schedule/afterschool/ 放一份 spec",
        accent="c-drill",
    )
    print(f"    → afterschool/index.html  （{len(entries)} 份）")


def build_afterschool(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "afterschool"
    specs = spec_lib.specs(SPECS, reverse=True)     # 新的排前面
    if not specs:
        print("    · 放学检查：storage/spec/schedule/afterschool/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, n = _render(sp, out_dir, pdf)
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.title or path.stem,
            "small": " · ".join(x for x in (sp.get("term", ""),
                                            f"{n['items']} 项") if x),
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
