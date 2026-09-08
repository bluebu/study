"""语文 · 教材总览 —— 一册一份的宏观总表：每课一行，**哪篇要背、哪首要默写一眼看到**。

spec 在 storage/spec/chinese/overview/<册>.txt，产物落在 dist/chinese/overview/：

    <册>.html / .pdf     A4 打印单，一张连着排的长表，夹在语文书里；
                         屏幕上（尤其手机）同一份就是速查页，表格自己横滚
    index.html           目录页

**一册一份，所以 spec 按册命名**（`g4a` = 四年级上册），不按日期 —— 练习单、
抽查单是一天/一课一份，这个栏目一整册只有一份。

四种区块（`lib/spec.py` 只解析骨架，这四种的语义是这个栏目自己的）：

    [摘要]      顶部摘要框，一行一条 `标题 | 详情`
    [<课号>]    一课一行：read= 朗读、recite= 背诵、copy= 默写、write= 写字数，
                缩进行 = 「其他要求」列。课号带 `*` 是略读课文（只认字、不写字），
                `[园地N]` 和 `[读书吧]` 不是课文（课号和课文名换灰、底色略淡）
    [分组]      表内的单元分组行，head 是组名（`[分组] 第五~第八单元`）
    [小结]      底部小结，一行一条

**不强制换页：一册就是一张连着排的长表**，换页交给打印机在行边界断
（`tr{break-inside:avoid}` + `thead` 每页重复表头）。原先 `[分页]` 是人定的
硬换页点，按单元边界断成三页 13 / 12 / 10 行 —— 一页装得下约 20 行，
于是第二页表格只排到 2/3 处、下面空掉小半页。单元边界该留的是**分组行**，
不是换页点。

⚠️ 所以这一份的打印边距**走 `@page`，不是 `.sheet` 的 padding**
（`overview.css` 末尾那段 `@media print` 覆盖了 print.css 的通用锁）：
padding 只在盒子的头尾生效，跨页之后中间几页会顶到纸边上。

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
GROUP = "分组"            # 表内的单元分组行，head 是组名
TODO = "待补"             # 课本还没到手的单元：印灰字，不算进「要背」

# 不是课文的行：语文园地、快乐读书吧。转灰 + 淡底，和课文行分得开
ASIDE = ("园地", "读书吧")


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
    """区块 → (行, 顶部摘要, 底部小结)。全册一张连续的表，`[分组]` 是表内的分组行。

    分组行也走这一串（带 `group` 键），模板里一个 `{% if r.group %}` 分岔 ——
    单元边界得跟着行一起流到它该在的位置上，不能另起一层结构。

    课文行里那个键叫 `dictation` 不叫 `copy`：Jinja 的 `a.b` 先找属性，`r.copy`
    会拿到 dict 自带的 `copy` 方法（`lib/tmpl.py` 的第三条）。
    """
    rows: list[dict] = []
    summaries, tails = [], []

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
        if b.name == GROUP:
            rows.append({"group": b.head})
            continue

        skim = b.name.endswith("*")                  # 略读课文
        rows.append({
            "group": "",
            "no": b.name,
            "name": b.head,
            "read": b.attr("read", ""),
            "recite": _mark(b.attr("recite", "")),
            "dictation": _mark(b.attr("copy", "")),
            "write": _write(b.attr("write", ""), skim=skim),
            # 「其他要求」列 = 缩进的说明行，照课后题原话
            "other": "；".join(b.notes()),
            "aside": b.name.startswith(ASIDE),       # 语文园地 / 快乐读书吧
        })

    if not any(not r["group"] for r in rows):
        spec_lib.die(f"{sp.path.name} 里没有任何 [课号] 区块")
    return rows, summaries, tails


def _counts(rows: list[dict]) -> dict:
    """页头那四个数。日积月累和课文背诵分开数 —— 混着数看不出课文要背几处。"""
    rows = [r for r in rows if not r["group"]]       # 分组行不是课文，不进统计
    backed = [r for r in rows if r["recite"]["dot"]]
    return {
        "lessons": sum(1 for r in rows if not r["aside"]),
        "recite": sum(1 for r in backed if not r["aside"]),
        "riji": sum(1 for r in backed if r["aside"]),
        # 「N 处」不是「N 首」：27 课一行要默写《出塞》《夏日绝句》两首
        "dictation": sum(1 for r in rows if r["dictation"]["dot"]),
    }


def _render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, dict]:
    rows, summaries, tails = _rows(sp)
    n = _counts(rows)
    lines = sum(1 for r in rows if not r["group"])

    heading = sp.get("title", DEFAULTS["title"])
    desc = "；".join(f'{s["head"]}：{s["detail"]}' for s in summaries[:2]) or heading

    body = tmpl.body(
        "overview/sheet.html",
        heading=heading,
        sub=sp.get("range", ""),
        n=n,
        note=sp.get("note", ""),
        summaries=summaries,
        rows=rows,
        tails=tails,
        tally=f"共 {lines} 行",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f'{heading}　{sp.get("range", "")}'.strip(),
            description=desc,
            body=body,
            emoji="🗒️",
            css=("print.css", "overview.css"),
            root="../..",
            noindex=True,          # 教材内容，不需要被搜索引擎收录
        ),
    )
    print(f"    → overview/{out.name}  （{lines} 行 · "
          f"要背 {n['recite']} 处 · 默写 {n['dictation']} 处）")
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
                     f"日积月累 {n['riji']} 处 · 默写 {n['dictation']} 处",
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
