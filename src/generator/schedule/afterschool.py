"""放学检查 —— 放学回来照着过一遍：作业抄没抄下来，三科逐项核。

    storage/spec/schedule/afterschool/<YYYYMMDD>.txt
    → dist/schedule/afterschool/<YYYYMMDD>.html + .pdf + index.html

**一天一份（一张纸），打印一叠放书桌上。** 名字按学期起那天命名（和一周课表一样）——
作业类型一个学期不怎么变，变了改 spec 重出一叠。

顺序就是检查顺序，纸上第一栏上底色：

1. **作业抄下来了吗** —— 放学前要把老师留的作业抄在作业本上带回家。
   这一栏只做入口检查、**不编号也不再抄一遍**：作业本就是原始记录，
   照着它去填下面各科的横线。没抄下来，后面全是空的
2. **三科逐项过** —— 每一项两个格子：**校内完成** ｜ **家中完成**
   （`boxes=` 能改成一格，下半区的「补充」栏就只有一个格子「完成」）。
   作业是这些项目的组合（语文那天可能是「小卷 + 生字本 + 背诵」），
   所以**每一项都要过一遍**：留了的画对勾（在哪儿做完的勾哪一格），
   **没留的画叉** —— 空着分不出「没留」和「没检查」。
   这两个动作印在页底，红色的对勾和叉**直接画出来当示范**，比写字直白
   **项的顺序就是做的顺序**，纸上自动编号（预习、复习排在末尾）。
   项按 **5 个一组、2 列**排（`GROUP` / `GRID`）：语文 8 项排成 5+3，
   数学 3 项、英语 2 项**整组留在左列不换列** —— 列宽按 2 列固定，
   所以三科的格子落在同两条竖线上。**右列没排满的那几格补成空格子**
   （一条横线 + 两个格子，没序号没项目名）：老师临时加的作业写这儿
3. **收拾书包** —— 照明天的课表装，家长签字
4. **补充**（同一张纸，下半区）—— 上面是学校留的作业（照作业本核），
   下面是家里加的，中间一条分界线**一眼看出是两码事**。这一区**不按
   「家庭作业 / 生活习惯」分栏，统一一栏叫「补充」**：编号位固定
   （`slots=10`，5 个一组两列 → 左 5 右 5），写了名字的照抄，剩下的留白手填。
   按类目预先分栏的话，每天加什么不一定，总是一边空着一边不够写

spec 的形状：**一个区块 = 纸上一栏**，区块里两种行混着写都行 ——
缩进行是说明（每条前面一个格子），项行是作业类型（`,` `，` `、` 分隔）。
想加一栏（比如「明天要带的东西」）直接在 spec 里加区块，代码一行不用改。
区块属性：

    lines=N   这一栏留 N 行横线（抄作业用）
    cols=N    排几列，默认 2；`cols=1` 排一列（横线长，够写具体内容）
    boxes=N   每项几个格子，默认 2（校内完成 ｜ 家中完成）。**补充那栏
              `boxes=1`** —— 家里加的作业没有「校内完成」这回事，
              那一个格子就叫**「完成」**（`SOLO_LABEL`）。位置照旧从右往左取，
              所以一格的栏和两格的栏最右那格对在同一条竖线上
    slots=N   **这一栏固定 N 个编号位**：写了名字的照抄，剩下的只出序号和
              横线、留着手填。补充区就靠它 —— 每天加什么不一定，位子先留好
    [分区]    **不是一栏，也不是分页**：纸上隔一条点线，下面是另一个区域，
              **一天还是一张纸**。不带抬头 —— 区域的名字就是它下面那几栏
              的名字。属性 `cols=N`：**本区的栏并排排 N 列**
              （`[分区] cols=2` → 第一栏在左半边、第二栏在右半边）。
              下半区现在只有「补充」一栏，不写这个属性，默认一列。
              「校内完成 / 家中完成」那行小字**每个区域各出一遍**；
              并排的区里每栏各出一遍 —— 左右是两列，各认自己那个格子
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("schedule", "afterschool")

DEFAULTS = {"title": "放学检查"}

# 项怎么排：**5 个一组、排 2 列，按列填**（左列 1~5、右列 6~10）。
# 不足 5 个的栏（数学 3 项、英语 2 项）**整组留在左列、不换列** ——
# 所以不能用 CSS 多列：那东西会自动平衡，3 项会被劈成 2+1。
# 走 grid（固定行数 + auto-flow column），列宽按列数固定，
# 项少的时候右列空着但仍占位 —— 三科的名字、横线、格子这才落在同两条竖线上。
# 这两个数注入到每个 .rows 的 --rows / --gcols，CSS 只读变量，**一处定义**
GROUP = 5
GRID = 2

# 每项后面那几个格子的名字，**从右往左取**：`boxes=1` 取最右那个（家中完成）。
# 右对齐是关键 —— 一格的栏和两格的栏，最右那一格落在同一条竖线上
BOX_LABELS = ("校内完成", "家中完成")
# 只有一个格子的栏（`boxes=1`，补充区）用这个名字：只有一格时「在哪儿完成的」
# 没得选，名字里再带「家中」是白占字。**位置照旧从右往左取**，
# 格子仍和上半区各栏最右那列对在同一条竖线上
SOLO_LABEL = "完成"
ZONE = "分区"      # 这个名字的区块不是一栏，是纸上的一条区域分界线


def _num(sp: spec_lib.Spec, b, key: str, default: str) -> int:
    v = b.attr(key, default)
    if not str(v).isdigit():
        spec_lib.die(f"{sp.path.name}：[{b.name}] 的 {key}= 要写数字，现在是 {v!r}")
    return int(v)


def _columns(sp: spec_lib.Spec) -> list[dict]:
    """区块 → 纸上一栏。说明行、项行、横线三样都是可选的。

    `[分区]` 不是一栏 —— 它在返回的列表里留一个 `{"zone": 抬头}`，
    切区域交给 `_zones()`，这儿只管把顺序保住。
    """
    out = []
    for b in sp.blocks:
        if b.name == ZONE:
            if b.head:
                spec_lib.die(f"{sp.path.name}：[{ZONE}] 不带抬头（现在写着"
                             f" {b.head!r}）—— 区域的名字就是它下面那几栏的名字")
            out.append({"zone": True, "zcols": max(1, _num(sp, b, "cols", "1"))})
            continue

        # 项行的左边就是项目名（`小卷, 书后习题, 背`），没有 `=` 右边
        items = [left for left, _ in b.items() if left]
        lines = _num(sp, b, "lines", "0")
        ncols = max(1, _num(sp, b, "cols", str(GRID)))
        boxes = _num(sp, b, "boxes", str(len(BOX_LABELS)))
        if not 1 <= boxes <= len(BOX_LABELS):
            spec_lib.die(f"{sp.path.name}：[{b.name}] 的 boxes= 只能是 "
                         f"1~{len(BOX_LABELS)}，现在是 {boxes}")
        # slots=N：**位子先留好**，写了名字的照抄，剩下的补成空串 ——
        # 模板见到空串就只出序号和横线（补充区每天加什么不一定）
        slots = _num(sp, b, "slots", "0")
        if slots > len(items):
            items = items + [""] * (slots - len(items))
        # 键叫 `rows` 不叫 `items` —— Jinja 的 `a.b` 先找属性，`col.items`
        # 会拿到 dict 自带的那个方法，渲染时当场 TypeError（`lib/tmpl.py`
        # 的第三条，这儿是第三次踩）
        # grid 的行数**按本栏的项数定，不是固定 GROUP**：数学 3 项要的是
        # 「3 行 × 2 列」，给 5 行的话补出来的空格子会流回左列第 4、5 行去。
        # 补几个 = 把这个矩形填满（语文 5×2 补 2、数学 3×2 补 3、英语 2×2 补 2）,
        # 所以补空格子**一行纸都不多占**。排一列的栏（cols=1）不分组、也不用补
        nrows = min(len(items), GROUP) if ncols > 1 else len(items)
        col = {"name": b.name, "head": b.head, "notes": b.notes(),
               "rows": items, "lines": lines, "ncols": ncols,
               "boxes": boxes,
               "labels": [SOLO_LABEL] if boxes == 1 else list(BOX_LABELS[-boxes:]),
               "nrows": nrows, "blanks": max(0, nrows * ncols - len(items))}
        if col["notes"] or col["rows"] or col["lines"]:
            out.append(col)

    cols = [c for c in out if "zone" not in c]
    if not cols:
        spec_lib.die(f"{sp.path.name} 里没有任何区块")

    # **第一栏不编号**：它是入口检查（作业抄没抄下来），不是清单里的一项 ——
    # 编号从三科那栏起，数出来的是「要逐项过的有几栏」。
    # 编号**跨页接着数**：翻到第二页还是同一天的同一套流程
    for col in cols:
        col["no"] = None
    for i, col in enumerate(cols[1:], 1):
        col["no"] = i
    return out


def _zones(rows: list[dict]) -> list[dict]:
    """按 `[分区]` 切区域。**区域是纸上隔一条点线，不是分页** —— 一天一张。

    `zcols` 是这一区的栏并排几列（`[分区] cols=2` → 左右各一栏）。

    「校内完成 / 家中完成」那行小字**每个区域各出一遍**：下半区离上面那行
    小字隔了半张纸，不重出就认不出哪列是哪列。**并排的区里每栏各出一遍**
    —— 左右两栏是两列格子，各认自己头上那个名字。
    """
    zones, cur = [], {"zcols": 1, "parts": []}
    for row in rows:
        if "zone" in row:
            if cur["parts"]:
                zones.append(cur)
            cur = {"zcols": row["zcols"], "parts": []}
            continue
        cur["parts"].append(row)
    if cur["parts"]:
        zones.append(cur)

    for z in zones:
        withrows = [c for c in z["parts"] if c["rows"]]
        for col in z["parts"]:
            col["show_cols"] = False
        for col in (withrows if z["zcols"] > 1 else withrows[:1]):
            col["show_cols"] = True
    return zones


def _render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, dict]:
    heading = sp.get("title", DEFAULTS["title"])
    rows = _columns(sp)
    zones = _zones(rows)
    cols = [c for c in rows if "zone" not in c]
    # **数的是写了名字的项**：slots= 留出来的空位子是给手填的，不算今天的活
    total = sum(1 for c in cols for it in c["rows"] if it)

    body = tmpl.body(
        "afterschool/sheet.html",
        heading=heading,
        zones=zones,
        total=total,
        tally=f"{len(cols)} 栏 / {total} 项",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} · {sp.get('term', '')}".rstrip(" ·"),
            description="放学回来照着过一遍：作业抄没抄下来，三科逐项核 ——"
                        "每项两个格子，校内完成 ｜ 家中完成。A4 打印。",
            body=body,
            emoji="🎒",
            css=("print.css", "afterschool.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → afterschool/{out.name}  "
          f"（{len(zones)} 区 / {len(cols)} 栏 / {total} 项）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, {"cols": len(cols), "items": total}


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="放学检查 · 课程表",
        description="放学回来照着过一遍：作业抄没抄下来，三科逐项核。每项两个格子，校内完成 ｜ 家中完成。",
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
