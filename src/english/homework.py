"""每日打卡 —— 群公告整理成一张 A4 打印单。

    storage/spec/english/homework/<YYYYMMDD>.txt   群公告整理出的 spec
    → dist/english/homework/<YYYYMMDD>.html + .pdf + index.html

从老站 ../english/homework/generate_checklist.py 搬来。spec 格式一条没改
（老站五份 spec 直接能跑），改的是三处工程上的东西：

  · 骨架交给 lib/spec.py 解析 —— 老站那份自己写了一遍 key: value 和 [标签] 的解析
  · 页面交给 lib/page.py + src/assets/{print,homework}.css —— 老站是 250 行内联 style
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
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib

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


def render_task(task: Task, no: int) -> str:
    title = inline(task.title)
    if task.tag:
        title += f' <span class="tag">{inline(task.tag)}</span>'

    body = [f'      <div class="title">{title}</div>']
    for text in task.notes:
        body.append(f'      <div class="sub">{inline(text)}</div>')
    if task.items:
        lis = "".join(f"<li>{inline(t)}</li>" for t in task.items)
        body.append(f'      <ul class="sub">{lis}</ul>')
    if task.words:
        # 两列，按列填：grid-auto-flow:column + 行数固定
        rows = math.ceil(len(task.words) / 2)
        cells = "".join(
            f'<div class="w"><i class="box"></i><b>{html.escape(w)}</b>'
            f"<s>{html.escape(m)}</s></div>"
            for w, m in task.words)
        body.append(f'      <div class="words" style="grid-template-rows:repeat({rows},auto)">'
                    f"{cells}</div>")

    return (f'  <div class="task" style="--c:var(--c-{task.color})">\n'
            f'    <div class="no">{no}</div>\n'
            f'    <div class="body">\n' + "\n".join(body) + "\n"
            f"    </div>\n"
            f'    <i class="box big"></i>\n'
            f"  </div>")


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int]:
    tasks = [Task(b, i) for i, b in enumerate(sp.blocks)]
    if not tasks:
        spec_lib.die(f"{sp.path.name} 里没有任何任务行")

    date = sp.get("date", "")
    title = sp.get("title", DEFAULTS["title"])
    memo_lines = sp.int_("memo", DEFAULTS["memo"])
    memo = ""
    if memo_lines:
        lns = "\n".join('      <div class="ln"></div>' for _ in range(memo_lines))
        memo = ('  <div class="memo">\n'
                '      <div class="lb">今日备注 · 想记下来的话</div>\n'
                f"{lns}\n"
                "  </div>\n")

    body = (
        f'<div class="sheet">\n'
        f'  <div class="head">\n'
        f'    <div class="t">\n'
        + (f'      <div class="date">{html.escape(date)}</div>\n' if date else "")
        + f"      <div>\n"
        f"        <h1>{html.escape(title)}</h1>\n"
        f'        <div class="en">{html.escape(sp.get("subtitle", DEFAULTS["subtitle"]))}</div>\n'
        f"      </div>\n"
        f"    </div>\n"
        f'    <div class="who">姓名 <i class="u"></i><span>家长签字 <i class="u"></i></span></div>\n'
        f"  </div>\n\n"
        f'  <div class="tip">\n'
        f'    <span>{inline(sp.get("tip-left", DEFAULTS["tip-left"]))}</span>\n'
        f'    <span>{inline(sp.get("tip-right", DEFAULTS["tip-right"]))}</span>\n'
        f"  </div>\n\n"
        + "\n".join(render_task(t, i + 1) for i, t in enumerate(tasks))
        + "\n\n"
        + memo
        + f'  <div class="foot">\n'
        f'    <div class="sign"><span>完成时间 <i class="u"></i></span>'
        f"<span>今日自评 ☆☆☆☆☆</span></div>\n"
        f'    <div class="cheer">{html.escape(sp.get("cheer", DEFAULTS["cheer"]))}</div>\n'
        f"  </div>\n"
        f"</div>"
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
    print(f"    → homework/{out.name}  （{len(tasks)} 项）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, len(tasks)


def build_index(out_dir: Path, entries: list[dict]) -> None:
    rows = "\n".join(
        f'      <li>\n'
        f'        <a class="main" href="{e["stem"]}.html">{html.escape(e["label"])}'
        f'<small>{e["count"]} 项 · {e["en"]}</small></a>\n'
        + (f'        <a class="pdf" href="{e["stem"]}.pdf">PDF</a>\n' if e["pdf"] else "")
        + f"      </li>"
        for e in entries
    ) or '      <li><span class="empty">还没有打卡单 —— 往 storage/spec/english/homework/ 放一份 spec</span></li>'

    body = f"""<main class="wrap">
  <header class="hero">
    <a class="back" href="../../">‹ 学习小站</a>
    <h1>每日打卡</h1>
    <p class="sub">群公告整理成一张 A4，打印出来打勾 · 共 {len(entries)} 份</p>
  </header>
  <ul class="list">
{rows}
  </ul>
</main>"""

    page.write(
        out_dir / "index.html",
        page.render(
            title="每日打卡 · 英语",
            description="每天的作业清单，整理成一张 A4 打印单，做完一项打一个勾。",
            body=body,
            emoji="✅",
            css=("site.css",),
            root="../..",
        ),
    )
    print(f"    → homework/index.html  （{len(entries)} 份）")


def build_homework(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "homework"
    specs = sorted(SPECS.glob("*.txt"), reverse=True) if SPECS.exists() else []
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
