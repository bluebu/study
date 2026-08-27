"""复述故事 —— 老师白板上的 Story Map 变成一张 A4，孩子看着复述。

    src/english/retell/specs/<slug>.txt  →  dist/english/retell/<slug>.html + .pdf

老师在白板上把整个故事拆成十几段，每段是一串关键词，用箭头竖着串下来。
拍下来是十几张照片，翻着看没法复述 —— 挪到一张纸上，一段一行，
眼睛能一次扫完整个故事的走向。

**只出英文。** 配了中文，眼睛会先去看中文，复述就变成翻译了。
生词（shepherdess / caretaker / unrewarded）留给她在故事里猜——
这批词本来就是她这两周指读过的。
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from lib import page, sheet, spec as spec_lib

HERE = Path(__file__).parent
SPECS = HERE / "retell" / "specs"


def segments(sp: spec_lib.Spec) -> list[list[str]]:
    """[地图] 区块 → 每段一串关键词。

    一行一段，节点之间用逗号分隔；节点内部并列的词用 · 连着写
    （`safe · hurt` 是一个节点，不是两个）。
    """
    block = next((b for b in sp.blocks if b.name == "地图"), None)
    if block is None:
        spec_lib.die(f"{sp.path.name}：缺 [地图] 区块")

    out = []
    for line in block.lines:
        text = line.strip()
        if not text:
            continue
        nodes = [n.strip() for n in text.split(",") if n.strip()]
        if nodes:
            out.append(nodes)
    if not out:
        spec_lib.die(f"{sp.path.name}：[地图] 里一段都没有")
    return out


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int, int]:
    segs = segments(sp)
    total_nodes = sum(len(s) for s in segs)

    rows = []
    for i, nodes in enumerate(segs, 1):
        # 「词 + 它后面的箭头」绑成一个不换行的单元 —— 不这么做，
        # 折行时箭头会落到下一行的行首（「→ kinder people」），
        # 读着像这一行是从箭头开始的。箭头留在行尾才是「还没完」。
        chain = "".join(
            f'<span class="unit"><span class="kw">{html.escape(n)}</span>'
            + ('<b class="arw">→</b>' if i < len(nodes) - 1 else "")
            + '</span>'
            for i, n in enumerate(nodes))
        rows.append(f'    <li><i class="no">{i}</i><span class="chain">{chain}</span></li>')

    heading = sp.title or "复述地图"
    meta = " · ".join(x for x in (sp.get("book"), f'第 {sp.get("pages")} 页' if sp.get("pages") else "",
                                 f"{len(segs)} 段") if x)
    task = sp.get("task", "")

    body = (
        f'<div class="sheet">\n'
        f'  <div class="head">\n'
        f'    <div><h1>{html.escape(heading)}</h1>\n'
        f'      <p class="meta">{html.escape(meta)}</p></div>\n'
        f'    <div class="who">姓名 <i class="u"></i><span>日期 <i class="u"></i></span></div>\n'
        f'  </div>\n'
        + (f'  <p class="task">{html.escape(task)}</p>\n' if task else "")
        + f'  <ol class="map">\n' + "\n".join(rows) + f'\n  </ol>\n'
        f'  <p class="foot">看着关键词讲，讲不出来的地方圈一下，回去再听一遍音频</p>\n'
        f'</div>'
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} 复述地图",
            description=f"{heading} 的复述关键词地图，{len(segs)} 段 {total_nodes} 个词，A4 打印。",
            body=body,
            emoji="🗺️",
            css=("print.css", "retell.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → retell/{out.name}  （{len(segs)} 段 · {total_nodes} 个词）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, len(segs), total_nodes


def build_index(out_dir: Path, entries: list[dict]) -> None:
    rows = "\n".join(
        f'      <li>\n'
        f'        <a class="main" href="{e["stem"]}.html">{html.escape(e["title"])}'
        f'<small>{e["segs"]} 段 · {e["nodes"]} 个词{f" · {e['book']}" if e["book"] else ""}</small></a>\n'
        + (f'        <a class="pdf" href="{e["stem"]}.pdf">PDF</a>\n' if e["pdf"] else "")
        + f'      </li>'
        for e in entries
    ) or '      <li><span class="empty">还没有复述地图 —— 往 src/english/retell/specs/ 放一份 spec</span></li>'

    body = f"""<main class="wrap">
  <header class="hero">
    <a class="back" href="../../">‹ 学习小站</a>
    <h1>复述故事</h1>
    <p class="sub">整个故事拆成几段关键词，看着讲一遍 · 共 {len(entries)} 份</p>
  </header>
  <ul class="list">
{rows}
  </ul>
</main>"""

    page.write(
        out_dir / "index.html",
        page.render(
            title="复述故事 · 英语",
            description="把故事拆成几段关键词，看着关键词把整个故事讲出来。A4 打印。",
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
