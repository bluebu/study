"""语文 · 教材总览 —— 一册一份的宏观总表：每课一行，**哪篇要背、哪首要默写一眼看到**。

spec 在 storage/spec/chinese/overview/<册>.txt，产物落在 dist/chinese/overview/：

    <册>.html / .pdf     A4 打印单，一页装完，夹在语文书里；
                         屏幕上（尤其手机）同一份就是速查页，表格自己横滚
    index.html           目录页

**一册一份，所以 spec 按册命名**（`g4a` = 四年级上册），不按日期 —— 练习单、
抽查单是一天/一课一份，这个栏目一整册只有一份。

三种区块（`lib/spec.py` 只解析骨架，这三种的语义是这个栏目自己的）：

    [摘要]      顶部摘要框，一行一条 `标题 | 详情`
    [<课号>]    一课一行：read= 朗读、recite= 背诵、copy= 默写、write= 写字数，
                缩进行 = 「其他要求」列。课号带 `*` 是略读课文（只认字、不写字），
                `[园地N]` 自动认成语文园地（课号和课文名换灰、底色略淡）
    [小结]      底部小结，一行一条

内容准则（搬内容前先读，每条都踩过）：

- **要求一律照课后题原话**：「有感情地朗读课文。背诵第 3~4 自然段。」就写这个，
  别自己发明「熟悉」「掌握」「熟读成诵」—— 书上根本没有这些词
- **背诵和默写分两列**：书上要求背的不一定要默写。四上 1~14 课只有《题西林壁》
  写了「默写」
- **课本没覆盖的单元写 `recite=待补`**，印灰字不加圆点。不猜、不从别的版本抄 ——
  2024 版和 2019 版课次编号不一样（《走月亮》2024 版已删），混用错得很隐蔽
- 日积月累算「要背」，但和课文背诵**分开统计** —— 页头分别显示两个数
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "overview")

DEFAULTS = {"title": "教材总览"}

SUMMARY = "摘要"          # 顶部摘要框那个区块的名字
TAIL = "小结"             # 底部小结那个区块的名字
TODO = "待补"             # 课本还没到手的单元：印灰字，不算进「要背」


def _mark(val: str) -> dict:
    """背诵 / 默写格：有要求就上底色加圆点，没要求淡灰一杠，待补印灰字。

    圆点是这张表的全部用处 —— 扫一眼就知道哪几行有活儿。所以「有没有要求」
    这个判断留在 Python，模板只管把 ● 摆上去。
    """
    if not val:
        return {"val": "", "cls": "off", "dot": False}
    if val == TODO:
        return {"val": val, "cls": "todo", "dot": False}
    return {"val": val, "cls": "on", "dot": True}


def _write(val: str, *, skim: bool) -> dict:
    """写字格：略读课文和 `write=0` 印「只认字」，`write=-` 是语文园地行。"""
    if val in ("-", "—") or not val:
        return {"val": "—", "cls": "off"}
    if skim or val == "0":
        return {"val": "只认字", "cls": "todo"}
    return {"val": f"{val} 字", "cls": ""}


def _rows(sp: spec_lib.Spec) -> tuple[list[dict], list[dict], list[str]]:
    """区块 → (课文行, 顶部摘要, 底部小结)。

    行里那个键叫 `dictation` 不叫 `copy`：Jinja 的 `a.b` 先找属性，`r.copy`
    会拿到 dict 自带的 `copy` 方法（`lib/tmpl.py` 的第三条）。
    """
    rows, summaries, tails = [], [], []

    for b in sp.blocks:
        if b.name == SUMMARY:
            for line in b.lines:
                head, _, detail = line.strip().partition("|")
                if head.strip():
                    summaries.append({"head": head.strip(), "detail": detail.strip()})
            continue
        if b.name == TAIL:
            tails += [line.strip() for line in b.lines if line.strip()]
            continue

        skim = b.name.endswith("*")                  # 略读课文
        rows.append({
            "no": b.name,
            "name": b.head,
            "read": b.attr("read", ""),
            "recite": _mark(b.attr("recite", "")),
            "dictation": _mark(b.attr("copy", "")),
            "write": _write(b.attr("write", ""), skim=skim),
            # 「其他要求」列 = 缩进的说明行，照课后题原话
            "other": "；".join(b.notes()),
            "yuan": b.name.startswith("园地"),        # 语文园地行
        })

    if not rows:
        spec_lib.die(f"{sp.path.name} 里没有任何 [课号] 区块")
    return rows, summaries, tails


def _counts(rows: list[dict]) -> dict:
    """页头那四个数。日积月累和课文背诵分开数 —— 混着数看不出课文要背几处。"""
    backed = [r for r in rows if r["recite"]["dot"]]
    return {
        "lessons": sum(1 for r in rows if not r["yuan"]),
        "recite": sum(1 for r in backed if not r["yuan"]),
        "riji": sum(1 for r in backed if r["yuan"]),
        "dictation": sum(1 for r in rows if r["dictation"]["dot"]),
    }


def _render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, dict]:
    rows, summaries, tails = _rows(sp)
    n = _counts(rows)

    heading = sp.get("title", DEFAULTS["title"])
    sub = sp.get("range", "")
    desc = "；".join(f'{s["head"]}：{s["detail"]}' for s in summaries[:2]) or heading

    body = tmpl.body(
        "overview/sheet.html",
        heading=heading,
        sub=sub,
        n=n,
        note=sp.get("note", ""),
        summaries=summaries,
        rows=rows,
        tails=tails,
        tally=f"{sub}　共 {len(rows)} 行" if sub else f"共 {len(rows)} 行",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading}　{sub}".strip(),
            description=desc,
            body=body,
            emoji="🗒️",
            css=("print.css", "overview.css"),
            root="../..",
            noindex=True,          # 教材内容，不需要被搜索引擎收录
        ),
    )
    print(f"    → overview/{out.name}  （{len(rows)} 行 · 要背 {n['recite']} 处 · "
          f"默写 {n['dictation']} 首）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, n


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="教材总览 · 语文",
        description="一册一份的总表：每课一行，哪篇要背、哪首要默写一眼看到。要求照课后题原话。",
        emoji="🗒️",
        h1="教材总览",
        sub=f"哪篇要背、哪首要默写 · 共 {len(entries)} 册",
        sections=[(None, entries)],
        empty="还没有总表 —— 往 storage/spec/chinese/overview/ 放一份 spec",
        accent="chinese",
    )
    print(f"    → overview/index.html  （{len(entries)} 册）")


def build_overview(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "overview"
    specs = spec_lib.specs(SPECS)
    if not specs:
        print("    · 教材总览：storage/spec/chinese/overview/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, n = _render(sp, out_dir, pdf)
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("book", path.stem),
            # 日积月累和课文背诵分开数 —— 加在一起看不出课文要背几处
            "small": f"{n['lessons']} 课 · 课文要背 {n['recite']} 处 · "
                     f"日积月累 {n['riji']} 处 · 默写 {n['dictation']} 首",
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
