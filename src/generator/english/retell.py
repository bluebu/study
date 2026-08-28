"""复述故事 —— 老师白板上的 Story Map 变成一张 A4，孩子看着复述。

    storage/spec/english/retell/<slug>.txt  →  dist/english/retell/<slug>.html + .pdf

老师在白板上把整个故事拆成十几段，每段是一串关键词，用箭头竖着串下来。
拍下来是十几张照片，翻着看没法复述 —— 挪到一张纸上，一段一行，
眼睛能一次扫完整个故事的走向。

**分组按 Plot Diagram 的五个阶段走**，美国四年级正在学的那套：
Exposition → Rising Action → Climax → Falling Action → Resolution。
阶段名挂在左边当路标，段落归到对应阶段下面。孩子讲的时候知道自己讲到哪一段了，
而 CLIMAX 通常只有一段 —— 一眼就看出整本书的转折在哪儿。

两条界限，别越：

  · **关键词是老师给的，一个不删不加不改写**（`docter`、`wasn't die` 原样留着）
  · **归组是解读**，不是老师给的。改归组只动 spec 里的区块归属，别动关键词

**只出英文。** 配了中文，眼睛会先去看中文，复述就变成翻译了。
生词（shepherdess / caretaker / unrewarded）留给她在故事里猜 ——
这批词本来就是她这两周指读过的。中文只出现在阶段抬头上（"铺垫"、"越陷越深"），
那是路标，不是词义。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("english", "retell")

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


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, int, int]:
    items = stages(sp)
    total_segs = sum(len(s.segs) for s in items)
    total_nodes = sum(len(seg) for s in items for seg in s.segs)

    # 段号跨阶段连续编，所以在这儿一次编完再交给模板
    no = 0
    ctx = []
    for stage in items:
        segs = []
        for nodes in stage.segs:
            no += 1
            segs.append({"no": no, "nodes": nodes})
        ctx.append({"name": stage.name, "short": stage.short,
                    "is_climax": stage.is_climax, "segs": segs})

    heading = sp.title or "复述地图"
    meta = " · ".join(x for x in (sp.get("book"),
                                 f'第 {sp.get("pages")} 页' if sp.get("pages") else "",
                                 f"{total_segs} 段") if x)

    body = tmpl.body(
        "retell/sheet.html",
        heading=heading,
        meta=meta,
        task=sp.get("task", ""),
        stages=ctx,
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
    page.listing(
        out_dir,
        title="复述故事 · 英语",
        description="把故事拆成几段关键词，按情节的五个阶段排好，看着关键词把整个故事讲出来。A4 打印。",
        emoji="🗺️",
        h1="复述故事",
        sub=f"整个故事拆成几段关键词，按情节的五个阶段排好，看着讲一遍 · 共 {len(entries)} 份",
        sections=[(None, [
            {"href": f'{e["stem"]}.html',
             "label": e["title"],
             "small": " · ".join(x for x in (f'{e["segs"]} 段', f'{e["nodes"]} 个词', e["book"]) if x),
             "pdf": f'{e["stem"]}.pdf' if e["pdf"] else None}
            for e in entries])],
        empty="还没有复述地图 —— 往 storage/spec/english/retell/ 放一份 spec",
        pdf_label="PDF",
    )
    print(f"    → retell/index.html  （{len(entries)} 份）")


def build_retell(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "retell"
    specs = spec_lib.specs(SPECS)
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
