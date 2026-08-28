"""数学 · 计算秘籍 —— 一个错因两页 A4。

    第 1 页  昨天错在哪：错题清单 + 每组一句错因
    第 2 页  秘籍：口诀卡 + 换了数的同类题

诊断和练习分开印，是因为清单上写着正确答案 —— 和练习题印在一起，
孩子会照着抄。所以第 2 页的题都换了数字，只留题型。

spec 在 storage/spec/math/miji/<slug>.txt，产物落在 dist/math/miji/：

    <slug>.html / .pdf              题面版（横线空着）
    <slug>-answers.html / .pdf      答案版（横线上印答案，给家长批改）
    index.html                      目录页（**答案版不列进去**）

练习题的答案不写在 spec 里，由脚本算 —— 抄一遍就多一次抄错的机会。
所以 spec 只写题面，除法必须整除，除不尽直接报错。
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("math", "miji")

# 示范行：「算式 | 注解」，算式里 <x> 表示这个字符被划掉
CUT = re.compile(r"&lt;(.+?)&gt;")


def _mark(text: str) -> str:
    """转义之后再把 <x> 还原成划掉记号 —— 顺序反了会把标记也转义掉。"""
    return CUT.sub(r'<span class="cut">\1</span>', html.escape(text))


def _answer(expr: str, sp: spec_lib.Spec) -> str:
    """算一道练习题的答案。只认 ÷ 和 ×，除法必须整除。"""
    for op, fn in (("÷", lambda a, b: a // b), ("×", lambda a, b: a * b)):
        if op in expr:
            left, _, right = expr.partition(op)
            try:
                a, b = int(left.strip()), int(right.strip())
            except ValueError:
                spec_lib.die(f"{sp.path.name}：「{expr}」两边要是整数")
            if op == "÷" and (b == 0 or a % b):
                spec_lib.die(f"{sp.path.name}：「{expr}」除不尽，口算单不出这种题")
            return str(fn(a, b))
    spec_lib.die(f"{sp.path.name}：「{expr}」里没有 ÷ 或 ×")


# ── 第 1 页：昨天错在哪 ────────────────────────────────────

def _wrong(block: spec_lib.Block, sp: spec_lib.Spec) -> dict:
    """一组同因错题。行格式「题, 你写的, 正确的」，抬头是错因。"""
    rows = []
    for line in block.lines:
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) != 3:
            spec_lib.die(f"{sp.path.name}：错题行要写成「题, 你写的, 正确的」：{line.strip()!r}")
        rows.append(dict(zip(("q", "bad", "good"), parts)))
    return {"head": block.head, "tag": block.tag, "rows": rows}


def _compare(block: spec_lib.Block) -> dict:
    """错在哪一步：两行并置，✗ 那行灰掉，✓ 那行是正解。"""
    rows = []
    for line in block.lines:
        expr, _, why = line.strip().partition("|")
        why = why.strip()
        rows.append({"cls": "row bad" if why.startswith("✗") else "row",
                     "ex": _mark(expr.strip()), "why": why})
    return {"head": block.head, "rows": rows}


def _page_diag(sp: spec_lib.Spec, wrongs: list[spec_lib.Block],
               compare: spec_lib.Block | None) -> str:
    groups = [_wrong(b, sp) for b in wrongs]

    heading = sp.get("diag", "错在哪")
    if sp.get("date"):
        heading += f'　{sp.get("date")}'

    return tmpl.body(
        "miji/diag.html",
        heading=heading,
        score=sp.get("score", ""),
        wrongs=groups,
        compare=_compare(compare) if compare else None,
        tip=sp.get("tip", ""),
        total=sum(len(g["rows"]) for g in groups),
    )


# ── 第 2 页：秘籍 ──────────────────────────────────────────

def _demo(block: spec_lib.Block) -> list[dict]:
    """口诀卡：每行一条示范，左边算式、右边一句为什么。"""
    return [{"ex": _mark(expr.strip()), "why": why.strip()}
            for expr, _, why in (line.strip().partition("|") for line in block.lines)]


def _group(block: spec_lib.Block, sp: spec_lib.Spec, answers: bool) -> dict:
    """一组练习题。**答案脚本算**，spec 里只写题面 —— 抄一遍就多一次抄错的机会。"""
    return {
        "name": block.name,
        "head": block.head,
        "qs": [{"expr": e, "ans": _answer(e, sp) if answers else ""}
               for e, _ in block.items()],
    }


def _page_drill(sp: spec_lib.Spec, demo: spec_lib.Block | None,
                groups: list[spec_lib.Block], answers: bool) -> str:
    grps = [_group(b, sp, answers) for b in groups]

    heading = sp.title + ("（答案）" if answers else "")
    if sp.get("date"):
        heading += f'　{sp.get("date")}'

    return tmpl.body(
        "miji/drill.html",
        heading=heading,
        info=page.sheet_info("用时", show=not answers),
        card={"rows": _demo(demo), "verify": sp.get("verify", "")} if demo else None,
        groups=grps,
        total=sum(len(g["qs"]) for g in grps),
    )


def _render(sp: spec_lib.Spec, out_dir: Path, *, pdf: bool, answers: bool) -> bool:
    demo = next((b for b in sp.blocks if b.name == "示范"), None)
    wrongs = [b for b in sp.blocks if b.name == "错题" and b.lines]
    compare = next((b for b in sp.blocks if b.name == "对照"), None)
    groups = [b for b in sp.blocks
              if b.name not in ("示范", "错题", "对照") and b.items()]
    if not groups:
        spec_lib.die(f"{sp.path.name} 里没有练习题区块")

    pages = []
    if wrongs and not answers:          # 诊断页本身就带答案，答案版不重复印
        pages.append(_page_diag(sp, wrongs, compare))
    pages.append(_page_drill(sp, demo, groups, answers))

    heading = sp.title + ("（答案）" if answers else "")
    name = sp.path.stem + ("-answers" if answers else "")
    out = page.write(
        out_dir / f"{name}.html",
        page.render(
            title=heading,
            body="\n".join(pages),
            emoji="🔢",
            css=("print.css", "miji.css"),
            root="../..",
            noindex=True,
        ),
    )
    n = sum(len(b.items()) for b in groups)
    print(f"    → {out.relative_to(out.parent.parent.parent)}  （{len(pages)} 页 · {n} 题）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="计算秘籍 · 数学",
        description="一个错因两页 A4：先看错在哪，再用一条口诀重做同类题。",
        emoji="🔢",
        h1="计算秘籍",
        sub=f"一个错因两页 A4 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有秘籍 —— 往 storage/spec/math/miji/ 放一份 spec",
        accent="math",
    )
    print(f"    → miji/index.html  （{len(entries)} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "miji"
    entries = []
    for path in spec_lib.specs(SPECS, reverse=True):
        sp = spec_lib.parse(path)
        pdf_ok = _render(sp, out_dir, pdf=pdf, answers=False)
        _render(sp, out_dir, pdf=pdf, answers=True)

        n = sum(len(b.items()) for b in sp.blocks if b.name not in ("示范", "错题", "对照"))
        bad = sum(len(b.lines) for b in sp.blocks if b.name == "错题")
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.title + (f'　{sp.get("date")}' if sp.get("date") else ""),
            "small": f"错题 {bad} 题 · 重练 {n} 题",
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
