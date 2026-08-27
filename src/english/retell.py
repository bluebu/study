"""复述故事 —— 老师白板上的 Story Map 变成一张 A4，孩子看着复述。

    src/english/retell/specs/<slug>.txt  →  dist/english/retell/<slug>.html + .pdf

老师在白板上把整个故事拆成十几段，每段是一串关键词，用箭头竖着串下来。
拍下来是十几张照片，翻着看没法复述 —— 挪到一张纸上，一段一行，
眼睛能一次扫完整个故事的走向。

**分组按 Plot Diagram 的五个阶段走**，美国四年级正在学的那套：
Exposition → Rising Action → Climax → Falling Action → Resolution。
阶段名挂在左边当路标，段落归到对应阶段下面。孩子讲的时候知道自己讲到哪一段了，
而 CLIMAX 通常只有一段 —— 一眼就看出整本书的转折在哪儿。

顶上曾经画过一座情节山（SVG 折线 + 五个节点），**去掉了**：一页纸上它吃掉
两成高度，而阶段名本身已经说清了先后，山只是把同一件事再画一遍。

两条界限，别越：

  · **关键词是老师给的，一个不删不加不改写**（`docter`、`wasn't die` 原样留着）
  · **归组是解读**，不是老师给的。改归组只动 spec 里的区块归属，别动关键词

**只出英文。** 配了中文，眼睛会先去看中文，复述就变成翻译了。
生词（shepherdess / caretaker / unrewarded）留给她在故事里猜 ——
这批词本来就是她这两周指读过的。中文只出现在阶段抬头上（"铺垫"、"越陷越深"），
那是路标，不是词义。
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path

from lib import page, sheet, spec as spec_lib

HERE = Path(__file__).parent
SPECS = HERE / "retell" / "specs"

@dataclass
class Stage:
    """情节的一个阶段。"""
    name: str                      # EXPOSITION / CLIMAX …
    short: str = ""                # 铺垫 / 转折点
    note: str = ""                 # 这一段在干什么
    segs: list[list[str]] = field(default_factory=list)   # 每段一串关键词

    @property
    def is_climax(self) -> bool:
        return "CLIMAX" in self.name.upper()


def stages(sp: spec_lib.Spec) -> list[Stage]:
    """每个 [区块] 是一个阶段，区块内一行一段。

    一行一段，节点之间用逗号分隔；节点内部并列的词用 · 连着写
    （`safe · hurt` 是一个节点，不是两个）。
    """
    out = []
    for block in sp.blocks:
        stage = Stage(name=block.name, short=block.head, note=block.tag)
        for line in block.lines:
            text = line.strip()
            if not text:
                continue
            nodes = [n.strip() for n in text.split(",") if n.strip()]
            if nodes:
                stage.segs.append(nodes)
        if stage.segs:
            out.append(stage)
    if not out:
        spec_lib.die(f"{sp.path.name}：一个阶段区块都没有")
    return out


def chain(nodes: list[str]) -> str:
    """一串关键词 → 带箭头的 HTML。

    「词 + 它后面的箭头」绑成一个不换行的 unit —— 不这么做，折行时箭头会落到
    下一行的行首（「→ kinder people」），读着像这一行是从箭头开始的。
    """
    return "".join(
        f'<span class="unit"><span class="kw">{html.escape(n)}</span>'
        + ('<b class="arw">→</b>' if i < len(nodes) - 1 else "")
        + "</span>"
        for i, n in enumerate(nodes))


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int, int]:
    items = stages(sp)
    total_segs = sum(len(s.segs) for s in items)
    total_nodes = sum(len(seg) for s in items for seg in s.segs)

    acts, no = [], 0
    for stage in items:
        rows = []
        for nodes in stage.segs:
            no += 1
            rows.append(f'        <span class="seg"><i>{no}</i>'
                        f'<span class="chain">{chain(nodes)}</span></span>')
        tag = (f'<span class="tag">{html.escape(stage.name)}'
               + (f'<small>{html.escape(stage.short)} · {len(stage.segs)} 段</small>'
                  if stage.short else f'<small>{len(stage.segs)} 段</small>')
               + '</span>')
        acts.append(f'      <div class="act{" climax" if stage.is_climax else ""}">\n'
                    f'        {tag}\n'
                    f'        <span class="segs">\n' + "\n".join(rows) + "\n"
                    f'        </span>\n'
                    f'      </div>')

    heading = sp.title or "复述地图"
    meta = " · ".join(x for x in (sp.get("book"),
                                 f'第 {sp.get("pages")} 页' if sp.get("pages") else "",
                                 f"{total_segs} 段") if x)
    task = sp.get("task", "")

    body = (
        f'<div class="sheet">\n'
        f'  <div class="head">\n'
        f'    <div><h1>{html.escape(heading)}</h1>\n'
        f'      <p class="meta">{html.escape(meta)}</p></div>\n'
        f'    <div class="who">姓名 <i class="u"></i><span>日期 <i class="u"></i></span></div>\n'
        f'  </div>\n'
        + (f'  <p class="task">{html.escape(task)}</p>\n' if task else "")
        + f'  <div class="acts">\n' + "\n".join(acts) + f'\n  </div>\n'
        f'  <p class="foot">看着关键词讲，讲不出来的地方圈一下 · '
        f'CLIMAX 只有一段，那是整本书的转折</p>\n'
        f'</div>'
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} 复述地图",
            description=f"{heading} 的复述关键词地图，按情节的五个阶段分组，"
                        f"{total_segs} 段 {total_nodes} 个词，A4 打印。",
            body=body,
            emoji="🗺️",
            css=("print.css", "retell.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → retell/{out.name}  （{len(items)} 阶段 · {total_segs} 段 · {total_nodes} 个词）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, total_segs, total_nodes


def build_index(out_dir: Path, entries: list[dict]) -> None:
    rows = "\n".join(
        f'      <li>\n'
        f'        <a class="main" href="{e["stem"]}.html">{html.escape(e["title"])}'
        f'<small>{e["segs"]} 段 · {e["nodes"]} 个词'
        + (f' · {html.escape(e["book"])}' if e["book"] else "")
        + '</small></a>\n'
        + (f'        <a class="pdf" href="{e["stem"]}.pdf">PDF</a>\n' if e["pdf"] else "")
        + f'      </li>'
        for e in entries
    ) or '      <li><span class="empty">还没有复述地图 —— 往 src/english/retell/specs/ 放一份 spec</span></li>'

    body = f"""<main class="wrap">
  <header class="hero">
    <a class="back" href="../../">‹ 学习小站</a>
    <h1>复述故事</h1>
    <p class="sub">整个故事拆成几段关键词，按情节的五个阶段排好，看着讲一遍 · 共 {len(entries)} 份</p>
  </header>
  <ul class="list">
{rows}
  </ul>
</main>"""

    page.write(
        out_dir / "index.html",
        page.render(
            title="复述故事 · 英语",
            description="把故事拆成几段关键词，按情节的五个阶段排好，看着关键词把整个故事讲出来。A4 打印。",
            body=body,
            emoji="🗺️",
            css=("site.css",),
            root="../..",
        ),
    )
    print(f"    → retell/index.html  （{len(entries)} 份）")


def build_retell(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "retell"
    specs = sorted(SPECS.glob("*.txt")) if SPECS.exists() else []
    if not specs:
        print("    · 复述故事：specs/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, segs, nodes = render(sp, out_dir, pdf)
        entries.append({"stem": path.stem, "title": sp.title or path.stem,
                        "segs": segs, "nodes": nodes, "book": sp.get("book", ""),
                        "pdf": pdf_ok})

    build_index(out_dir, entries)
