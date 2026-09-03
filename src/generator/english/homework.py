"""每日打卡 —— 群公告整理成一张 A4 打印单。

    storage/spec/english/homework/<YYYYMMDD>.txt   群公告整理出的 spec
    → dist/english/homework/<YYYYMMDD>.html + .pdf + index.html

从老站 ../english/homework/generate_checklist.py 搬来。spec 格式一条没改
（老站五份 spec 直接能跑），改的是三处工程上的东西：

  · 骨架交给 lib/spec.py 解析 —— 老站那份自己写了一遍 key: value 和 [标签] 的解析
  · 版式交给 src/templates/homework/sheet.html + src/assets/{print,homework}.css
    —— 老站是 250 行内联 style
  · PDF 交给 lib/sheet.py（Chrome 路径自动探测，CI 里也能出）

spec 长这样：

    date: 8月27日

    [听] 听外教音频 | 120 分钟
        今天实际听了 __ 分钟          ← 普通说明行
    [点读] 点读 · 超8 Lesson 3
        * 第 61–62 页 单词部分         ← 圆点列表
    [练] 单词抄写 | 每天 2 个
        + close to = 几乎，接近        ← 单词表，带勾选框

行内两个记号：`__` 出一条填空横线（越长线越长），`<<3>>` 出 3 个小方格。
"""

from __future__ import annotations

import html
import math
import re
import sys
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("english", "homework")

MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 类别关键字 → 色板变量名。标签里含哪个关键字就用哪个色。
# 和打卡评价共用同一套五色（palette.css 是单一真源），分类色里没有红 —— 红专属分数。
CATEGORY = [
    ("听", "listen"), ("指", "listen"),
    ("读", "read"),   ("点", "read"),
    ("词", "word"),   ("写", "word"),
    ("练", "drill"),  ("AI", "drill"),
    ("语", "gram"),   ("法", "gram"),
]
CYCLE = ["listen", "read", "word", "drill", "gram"]   # 没写标签时按这个循环

# ── 一页装得下吗 ────────────────────────────────────────────────
# A4 一张纸的高度是死的，卡片却是按内容长的：8 项时还空着 90px、9 项只剩 24px，
# 第 10 项一来就多出 42px —— 被 Chrome 二次分页，打出来是两张纸，第二张上只有
# 页脚那一条。所以卡间距和卡内 padding 做成 CSS 变量（homework.css 的
# --gap / --pad），一页装不下就换下一档更紧的。办法和 ket.py 答案版的按估算高度
# 切页是同一套：**估算只用来挑档，真正的间距值只写在 CSS 里**。
#
# 下面每个数都是在**打印媒体**下量出来的（Chromium，210mm 宽），不是拍的。
# 改了 homework.css 的字号 / 行高 / 边框 / 边距就得重量一遍 ——
# 量法：emulateMedia('print') 之后取各元素的 getBoundingClientRect().height。
PAGE_H = 1112          # A4 是 1123px（297mm @96dpi），留 11px 给估算自身的误差
                       # （量下来偏高 1~2px）。真正的余量在下面每一档里：挑中的那档
                       # 离 A4 还剩 ~24px，够线上 Noto 比本地 PingFang 多折一行（≈19px）
SHEET_PAD = 76         # .sheet 上下 padding 各 10mm
HEAD_H, HEAD_GAP = 56, 9      # 页头；那道间距是它的 margin-bottom:4 和 .tip 的 9 折叠后的值
TIP_H, TIP_GAP = 17, 12       # 提示行
CARD_MIN, CARD_BORDER = 32, 2     # 卡内容最矮就是大勾选框（28 + 2×2 边框）；卡上下边框各 1.5px，
                                  # 但 1x 下按设备像素各落成 1px —— 写 3 的话估算会按卡数系统性偏高
TITLE_H = 22.5                    # 标题一行
NOTE_H = 21.75                    # 一行说明（18.75 + margin-top 3）。**假定不折行**
BULLET_H, BULLET_GAP, BULLET_PAD = 18.75, 2, 15.5   # 一条 * 列表项 / 项间 / ul 自己的上下留白
WORD_TOP, WORD_ROW_H, WORD_GAP = 8, 19.5, 7         # + 单词表：上间距 / 一行 / 行距
MEMO_LB, MEMO_LINE, MEMO_BOX, MEMO_GAP = 17.25, 20, 20, 12   # 备注：抬头 / 一条横线 / padding+边框 / 上间距
FOOT_H, FOOT_GAP = 37, 14     # 页脚

# (卡间距, 卡内上下 padding)，从松到紧。**第一档就是原来的版式** ——
# 装得下的日子生成器不注入任何 style，HTML 和以前逐字节一样。
DENSITY = [(10, 11), (7, 9), (5, 8), (4, 6)]

DEFAULTS = {
    "title": "每日打卡作业",
    "subtitle": "Daily Checklist",
    "cheer": "加油，每天一小步 👣 成就未来一大步",
    "memo": 2,
    "tip-left": "做完一项，就在右边的方框里打一个 ✓",
    "tip-right": "全部完成后，按模板在群里打卡",
}


class Task:
    """一项作业。"""

    def __init__(self, block: spec_lib.Block, index: int):
        self.color = color_for(block.name, CYCLE[index % len(CYCLE)])
        self.title = block.head
        self.tag = block.tag
        self.notes: list[str] = []      # 普通说明行
        self.items: list[str] = []      # * 圆点列表
        self.words: list[tuple[str, str]] = []   # + 单词表

        for raw in block.lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("+"):
                word, _, mean = line[1:].strip().partition("=")
                self.words.append((word.strip(), mean.strip()))
            elif line.startswith("*"):
                self.items.append(line[1:].strip())
            else:
                self.notes.append(line)


def color_for(label: str, fallback: str) -> str:
    for key, name in CATEGORY:
        if key in label:
            return name
    return fallback


def inline(text: str) -> str:
    """转义之后还原两个记号：`__` → 填空横线，`<<n>>` → n 个小方格。

    横线宽度跟着下划线个数走 —— 要写「120」的空比要打勾的空长，
    spec 里多敲几个下划线就行，不用去改 CSS。
    """
    out = html.escape(text)
    out = re.sub(r"_{2,}",
                 lambda m: f'<i class="fill" style="width:{max(40, len(m.group()) * 11)}px"></i>',
                 out)
    out = re.sub(r"&lt;&lt;(\d+)&gt;&gt;",
                 lambda m: '<span class="mini">' + "<i></i>" * int(m.group(1)) + "</span>",
                 out)
    return out


def task_ctx(task: Task) -> dict:
    """一项作业交给模板的形状 —— 标记全在模板里，这儿只做 inline 和分列算行数。"""
    return {
        "color": task.color,
        "title": inline(task.title),
        "tag": inline(task.tag) if task.tag else "",
        "notes": [inline(t) for t in task.notes],
        # 键不能叫 items —— Jinja 的 `t.items` 会取到 dict 自带的方法（见 lib/tmpl.py）
        "bullets": [inline(t) for t in task.items],
        "words": [{"word": w, "mean": m} for w, m in task.words],
        # 两列，按列填：grid-auto-flow:column，所以要先算出行数
        "word_rows": math.ceil(len(task.words) / 2) if task.words else 0,
    }


def sheet_height(tasks: list[Task], memo_lines: int, gap: float, pad: float) -> float:
    """这一张打印单在纸上有多高（px）—— 估算，只用来挑间距档。"""
    total = SHEET_PAD + HEAD_H + HEAD_GAP + TIP_H + TIP_GAP
    for t in tasks:
        body = TITLE_H + len(t.notes) * NOTE_H
        if t.items:
            body += BULLET_PAD + len(t.items) * BULLET_H + (len(t.items) - 1) * BULLET_GAP
        if t.words:
            rows = math.ceil(len(t.words) / 2)
            body += WORD_TOP + rows * WORD_ROW_H + (rows - 1) * WORD_GAP
        total += max(CARD_MIN, body) + 2 * pad + CARD_BORDER
    total += (len(tasks) - 1) * gap
    # 末张卡的 margin-bottom 和下一块的 margin-top 折叠成大的那个
    if memo_lines:
        total += max(gap, MEMO_GAP) + MEMO_LB + memo_lines * MEMO_LINE + MEMO_BOX + FOOT_GAP
    else:
        total += max(gap, FOOT_GAP)
    return total + FOOT_H


def squeeze_for(tasks: list[Task], memo_lines: int) -> str:
    """挑一档装得下一页的间距，返回要注入 .sheet 的 style（第一档返回空串）。"""
    for i, (gap, pad) in enumerate(DENSITY):
        if sheet_height(tasks, memo_lines, gap, pad) <= PAGE_H:
            return "" if i == 0 else f"--gap:{gap}px;--pad:{pad}px"

    gap, pad = DENSITY[-1]
    over = sheet_height(tasks, memo_lines, gap, pad) - PAGE_H
    print(f"    ⚠️  {len(tasks)} 项一张 A4 装不下：最紧一档还超 {over:.0f}px，"
          f"PDF 会多出一页（可在 spec 里写 memo: 0 少两行备注）", file=sys.stderr)
    return f"--gap:{gap}px;--pad:{pad}px"


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int]:
    tasks = [Task(b, i) for i, b in enumerate(sp.blocks)]
    if not tasks:
        spec_lib.die(f"{sp.path.name} 里没有任何任务行")

    date = sp.get("date", "")
    title = sp.get("title", DEFAULTS["title"])
    memo_lines = sp.int_("memo", DEFAULTS["memo"])
    squeeze = squeeze_for(tasks, memo_lines)

    body = tmpl.body(
        "homework/sheet.html",
        squeeze=squeeze,
        date=date,
        title=title,
        subtitle=sp.get("subtitle", DEFAULTS["subtitle"]),
        tip_left=inline(sp.get("tip-left", DEFAULTS["tip-left"])),
        tip_right=inline(sp.get("tip-right", DEFAULTS["tip-right"])),
        tasks=[task_ctx(t) for t in tasks],
        memo_lines=memo_lines,
        cheer=sp.get("cheer", DEFAULTS["cheer"]),
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=" ".join(x for x in (date, title) if x),
            description=f"{date}的英语打卡作业清单，共 {len(tasks)} 项，A4 打印。",
            body=body,
            emoji="✅",
            css=("print.css", "homework.css"),
            root="../..",
            noindex=True,        # 打印单不需要被搜索引擎收录
        ),
    )
    print(f"    → homework/{out.name}  （{len(tasks)} 项{' · 紧排' if squeeze else ''}）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, len(tasks)


def build_index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="每日打卡 · 英语",
        description="每天的作业清单，整理成一张 A4 打印单，做完一项打一个勾。",
        emoji="✅",
        h1="每日打卡",
        sub=f"群公告整理成一张 A4，打印出来打勾 · 共 {len(entries)} 份",
        sections=[(None, [{"href": f'{e["stem"]}.html',
                           "label": e["label"],
                           "small": f'{e["count"]} 项 · {e["en"]}',
                           "pdf": f'{e["stem"]}.pdf' if e["pdf"] else None}
                          for e in entries])],
        empty="还没有打卡单 —— 往 storage/spec/english/homework/ 放一份 spec",
        pdf_label="PDF",
    )
    print(f"    → homework/index.html  （{len(entries)} 份）")


def build_homework(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "homework"
    specs = spec_lib.specs(SPECS, reverse=True)
    if not specs:
        print("    · 每日打卡：specs/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, count = render(sp, out_dir, pdf)
        ymd = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", path.stem)
        en = (f"{MONTHS_EN[int(ymd.group(2)) - 1]} {int(ymd.group(3))} · Daily checklist"
              if ymd else "Daily checklist")
        entries.append({"stem": path.stem, "label": sp.get("date") or path.stem,
                        "count": count, "en": en, "pdf": pdf_ok})

    build_index(out_dir, entries)
