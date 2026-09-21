"""英语 · 语法练习 —— 语法书上的练习题整理成 A4 打印单，末页附答案。

    storage/spec/english/grammar/<slug>.txt
        → dist/english/grammar/<slug>.html + .pdf + index.html

书上一个单元的练习分散在两三页上，边角还压着别的单元的题；抄成一份 spec 之后
一个单元一张（多了自动续页），**答案单独印在最后一张纸上** —— 孩子拿前几页写，
家长留最后一页对。原先那种「答案印在题目旁边」的版式这儿不做：一眼扫到答案，
这份练习就白做了。

## spec 怎么写

一个 `[区块]` 是书上的一个大题，**区块名就是书上的题号**（三 / 四 / 五），
照抄不重排 —— 孩子手上还有那本书，题号对不上就翻不回去。

    [三] 从方框中选择最恰当的副词填空，每个词只能用一次。 | 10 题
    词库: often, why, away, politely, again, outside, too, how, early
    例: I *often* go to school by bus. | 我经常乘公共汽车上学。
    Tom speaks __ to his teacher. | politely
    –__ did you throw away the cake? | Why
        –It tastes sour.

    [四] 写出下列副词的比较级和最高级。 | 15 词  type=table  cols=副词原级 | 比较级 | 最高级
    例: late | later | latest
    fast | faster | fastest

两种形状，靠 `type=` 分（默认 `fill`）：

  · **fill** 填空题：一行一题，`题面 | 答案`。题面里**一处 `__` 就是一处空**
  · **table** 变形表：一行一项，`给出的 | 答案 | 答案`，列头写在 `cols=` 里

三条额外的行，都靠行首认（和 retell 的 `?` 行一个路子，不用配置）：

  · `词库:` 开头 —— 方框里的备选词，`,` `，` `、` 都能当分隔
  · `例:` 开头 —— 书上印好的例句 / 例行，填好的词用 `*词*` 标出来，印成本栏目的青色
  · 缩进行 —— 这一题的附属行：中文提示（有汉字，印成小字灰色）
    或者对话的下一句（没汉字，跟题面同一档字号）

## 两条定死的

1. **一处空画几条线，由答案的词数定**（`as high as` → 三条线）。
   线宽是固定的 —— 跟着答案长短走等于把答案印在纸上，`too` 和 `suddenly`
   的空一样宽，孩子才得靠句子判断
2. **答案在自己那一张纸上**，不在题面页的角落里。题面页几张由内容定
   （一个大题不劈成两半，Chrome 自己排），答案页永远是最后一张

页头在每一页重复（`<table>` + `<thead>`，和写字单同一套，原委见 writing.css）。
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("english", "grammar")

DEFAULTS = {
    "title": "语法练习",
    "hint": "每处空画了几条线，就填几个词。填完把整句小声读一遍。",
}

BLANK = re.compile(r"_{2,}")            # 题面里的一处空
STRESS = re.compile(r"\*([^*\n]+)\*")   # 例句里已经填好的词
CJK = re.compile(r"[\u4e00-\u9fff]")    # 缩进行是中文提示还是对话的下一句
TAILS = ".,?!;:"                        # 空后面紧跟这些就把线和标点收紧

BANK_LEAD = ("词库",)
EG_LEAD = ("例",)
KINDS = ("fill", "table")


def _lead(line: str, names: tuple[str, ...]) -> str | None:
    """行首是不是 `词库:` / `例:` 这样的前缀，是就返回冒号后面的内容。"""
    for name in names:
        for sep in (":", "："):
            if line.startswith(name + sep):
                return line[len(name) + len(sep):].strip()
    return None


def _rich(text: str) -> str:
    """escape 之后还原 `*词*` —— 例句里书上已经填好的那几个词。"""
    return STRESS.sub(lambda m: f"<em>{m.group(1)}</em>", html.escape(text))


def _blanks(n: int, tight: bool) -> str:
    """n 条横线。**宽度是固定的**，见文件头第 1 条。

    `tight`：后面紧跟标点（`Lucy sings __.`）时，收掉最后一条线右边那点间距 ——
    不收的话纸上是「____ .」，句号飘在线外头。
    """
    return f'<span class="bl{" tight" if tight else ""}">' + "<i></i>" * n + "</span>"


def _fill(q: str, n: int, where: str) -> str:
    """题面里那处 `__` 换成 n 条横线。"""
    parts = BLANK.split(html.escape(q))
    if len(parts) != 2:
        spec_lib.die(f"{where}：一题只留一处 __，现在有 {len(parts) - 1} 处：{q!r}")
    return parts[0] + _blanks(n, parts[1][:1] in TAILS) + parts[1]


@dataclass
class Item:
    """一道小题。"""
    q: str                                    # 题面（原文，还没插横线）
    a: str                                    # 答案
    subs: list[str] = field(default_factory=list)   # 缩进行


@dataclass
class Group:
    """书上的一个大题。"""
    no: str                                   # 题号，照抄书上的（三 / 四 / 五）
    title: str
    tag: str
    kind: str = "fill"
    cols: list[str] = field(default_factory=list)
    bank: list[str] = field(default_factory=list)
    eg: list[str] = field(default_factory=list)     # 例：fill 是 [句子, 中文]，table 是各列
    items: list[Item] = field(default_factory=list)


def _group(block: spec_lib.Block, where: str) -> Group:
    kind = block.attr("type", "fill")
    if kind not in KINDS:
        spec_lib.die(f"{where}：[{block.name}] 的 type={kind} 不认识，只有 {' / '.join(KINDS)}")

    cols = [c.strip() for c in (block.attr("cols") or "").split("|") if c.strip()]
    if kind == "table" and len(cols) < 2:
        spec_lib.die(f"{where}：[{block.name}] 是变形表，得写 cols=列头 | 列头 …")

    g = Group(no=block.name, title=block.head, tag=block.tag, kind=kind, cols=cols)
    for raw in block.lines:
        line = raw.strip()
        if not line:
            continue

        if raw[:1].isspace():                         # 缩进行：附在上一题下面
            if not g.items:
                spec_lib.die(f"{where}：[{block.name}] 的缩进行 {line!r} 前面还没有题")
            g.items[-1].subs.append(line)
            continue

        if (bank := _lead(line, BANK_LEAD)) is not None:
            g.bank = [w.strip() for w in
                      re.split(f"[{re.escape(spec_lib.ITEM_SEPS)}]", bank) if w.strip()]
            continue

        if (eg := _lead(line, EG_LEAD)) is not None:
            g.eg = [c.strip() for c in eg.split("|")]
            continue

        left, sep, right = line.partition("|")
        if kind == "table":
            cells = [c.strip() for c in line.split("|")]
            if len(cells) != len(cols):
                spec_lib.die(f"{where}：[{block.name}] 这一行 {len(cells)} 格、"
                             f"列头有 {len(cols)} 格：{line!r}")
            g.items.append(Item(q=cells[0], a=" | ".join(cells[1:])))
        else:
            if not sep or not right.strip():
                spec_lib.die(f"{where}：[{block.name}] 这一题没写答案（`题面 | 答案`）：{line!r}")
            g.items.append(Item(q=left.strip(), a=right.strip()))

    if not g.items:
        spec_lib.die(f"{where}：[{block.name}] 里一道题都没有")
    return g


def _sub_ctx(text: str) -> dict:
    """缩进行：有汉字就是中文提示（小字灰），没有就是对话的下一句。"""
    return {"text": text, "cn": bool(CJK.search(text))}


def _group_ctx(g: Group, where: str) -> dict:
    used = {w.lower() for w in STRESS.findall(g.eg[0])} if g.eg else set()
    ctx = {
        "no": g.no,
        "title": g.title,
        "tag": g.tag,
        "kind": g.kind,
        "cols": g.cols,
        "bank": [{"text": w, "used": w.lower() in used} for w in g.bank],
        "eg": None,
        "rows": [],
    }

    if g.kind == "table":
        if g.eg:
            ctx["eg"] = {"cells": g.eg}
        ctx["rows"] = [{"no": i, "term": it.q, "blanks": len(g.cols) - 1}
                       for i, it in enumerate(g.items, 1)]
    else:
        if g.eg:
            ctx["eg"] = {"q": _rich(g.eg[0]),
                         "cn": g.eg[1] if len(g.eg) > 1 else ""}
        ctx["rows"] = [{"no": i,
                        "q": _fill(it.q, len(it.a.split()), where),
                        "subs": [_sub_ctx(s) for s in it.subs]}
                       for i, it in enumerate(g.items, 1)]
    return ctx


def _ans_ctx(g: Group) -> dict:
    """答案页上的一节。变形表照着原样排，填空题一行一条。"""
    if g.kind == "table":
        rows = [{"cells": [it.q, *it.a.split(" | ")]} for it in g.items]
    else:
        rows = [{"no": i, "a": it.a} for i, it in enumerate(g.items, 1)]
    return {"no": g.no, "title": g.title, "kind": g.kind, "cols": g.cols, "rows": rows}


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, str]:
    where = sp.path.name
    if not sp.blocks:
        spec_lib.die(f"{where} 里没有任何 [大题]")

    groups = [_group(b, where) for b in sp.blocks]
    total = sum(len(g.items) for g in groups)
    tally = f"{len(groups)} 大题 · {total} 题"

    heading = sp.title or DEFAULTS["title"]
    sub = " · ".join(x for x in (sp.get("book", ""),
                                 f'第 {sp.get("pages")} 页' if sp.get("pages") else "") if x)

    body = tmpl.body(
        "grammar/sheet.html",
        heading=heading,
        sub=sub,
        info=page.sheet_info("得分"),
        hint=sp.get("hint", DEFAULTS["hint"]),
        groups=[_group_ctx(g, where) for g in groups],
        answers=[_ans_ctx(g) for g in groups],
        tally=tally,
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} 语法练习",
            description=f"{heading} 的语法练习单，{tally}，末页附答案，A4 打印。",
            body=body,
            emoji="🔤",
            css=("print.css", "grammar.css"),
            root="../..",
            noindex=True,          # 练习单不进搜索引擎
        ),
    )
    print(f"    → grammar/{out.name}  （{tally}）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, tally


def build_index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="语法练习 · 英语",
        description="语法书上的练习题整理成 A4 打印单，最后一张是答案，家长留着对。",
        emoji="🔤",
        h1="语法练习",
        sub=f"一个单元一份，末页附答案 · 共 {len(entries)} 份",
        sections=[(None, [{"href": f'{e["stem"]}.html',
                           "label": e["label"],
                           "small": " · ".join(x for x in (e["tally"], e["pages"]) if x),
                           "pdf": f'{e["stem"]}.pdf' if e["pdf"] else None}
                          for e in entries])],
        empty="还没有语法练习 —— 往 storage/spec/english/grammar/ 放一份 spec",
        pdf_label="PDF",
    )
    print(f"    → grammar/index.html  （{len(entries)} 份）")


def build_grammar(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "grammar"
    specs = spec_lib.specs(SPECS)          # 按单元顺序排，不倒序
    if not specs:
        print("    · 语法练习：specs/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, tally = render(sp, out_dir, pdf)
        entries.append({"stem": path.stem, "label": sp.title or path.stem,
                        "tally": tally,
                        "pages": f'第 {sp.get("pages")} 页' if sp.get("pages") else "",
                        "pdf": pdf_ok})

    build_index(out_dir, entries)
