"""复述故事 —— 老师白板上的 Story Map 变成一张 A4，孩子看着复述。

    storage/spec/english/retell/<slug>.txt  →  dist/english/retell/<slug>.html + .pdf

老师在白板上把整个故事拆成十几段，每段是一串关键词，用箭头竖着串下来。
拍下来是十几张照片，翻着看没法复述 —— 挪到一张纸上，一段一行，
眼睛能一次扫完整个故事的走向。

**老师给的东西有两种形状，纸上也就有两种。** 哪一种不用配置，看 spec 里
有没有 `?` 行就知道：

  · **一行一段**（白板 Story Map，L1《Prince Darling》）：每段一串关键词，
    逗号变箭头。分组是我们按 Plot Diagram 的五个阶段解读出来的，美国四年级
    正在学的那套：Exposition → Rising Action → Climax → Falling Action →
    Resolution。阶段名挂在左边当路标，而 CLIMAX 通常只有一段 —— 一眼就看出
    整本书的转折在哪儿。
  · **一章几问 + 一章一批词**（思维导图，L4《Heidi》）：`?` 行是老师编了号的
    问题，剩下的行是这一章的词。问题有先后（编号照老师的，每章从 1 起），
    **词没有先后** —— 所以问题走编号圆圈、词摊成一片用 `·` 隔开，不给箭头。
    箭头是「先这个再那个」的断言，老师没给顺序就不许编一个出来。
    分组也是老师给的（Chapter 1–3），不是解读，别改成五阶段。

两条界限，别越：

  · **关键词是老师给的，一个不删不加不改写**（`docter`、`wasn't die` 原样留着）
  · **归组是解读**，不是老师给的。改归组只动 spec 里的区块归属，别动关键词

**只出英文。** 配了中文，眼睛会先去看中文，复述就变成翻译了。
生词（shepherdess / caretaker / unrewarded）留给她在故事里猜 ——
这批词本来就是她这两周指读过的。中文只出现在阶段抬头上（"铺垫"、"越陷越深"），
那是路标，不是词义。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("english", "retell")

# `?` 开头的行 = 思维导图上的一个问题。问句里本来就有逗号，不能按节点拆，
# 所以要一个前缀把它和词行分开
ASK = "?"


def nodes(text: str) -> list[str]:
    """一行拆成节点：`,` `，` `、` 都算分隔，`词 = 中文` 只取词。

    **中文释义落在 spec 里、不上纸**（只出英文，见文件头第一条）。第 4 课老师
    是连着中文一起给的 —— 扔掉就得回群里翻，印上去复述就变成翻译，所以
    原样存进 spec、渲染时丢掉。哪天想要中文，改模板就够，不用重敲一遍词表。
    """
    out = []
    for chunk in re.split(f"[{re.escape(spec_lib.ITEM_SEPS)}]", text):
        word, _, _gloss = chunk.partition("=")
        if word.strip():
            out.append(word.strip())
    return out


@dataclass
class Stage:
    """情节的一个阶段。"""
    name: str                      # EXPOSITION / CLIMAX …
    short: str = ""                # 铺垫 / 转折点
    note: str = ""                 # 这一段在干什么
    segs: list[list[str]] = field(default_factory=list)   # 每段一串关键词（一行一段）
    asks: list[str] = field(default_factory=list)         # 思维导图上的问题
    pool: list[str] = field(default_factory=list)         # 这一章的词，无先后

    @property
    def is_climax(self) -> bool:
        return "CLIMAX" in self.name.upper()


def stages(sp: spec_lib.Spec) -> list[Stage]:
    """每个 [区块] 是一个阶段（或一章），区块内一行一段（或一行几个词）。

    行怎么拆都一样（见 `nodes()`）：节点之间用逗号分隔，节点内部并列的词用
    · 连着写（`safe · hurt` 是一个节点，不是两个）。**拆出来算什么，看这个
    区块有没有 `?` 行** —— 有问题就是思维导图那种，词行合成一片无序的词库；
    没有就是白板 Story Map，一行一段、渲染成箭头串。
    """
    out = []
    for block in sp.blocks:
        stage = Stage(name=block.name, short=block.head, note=block.tag)
        rows = []
        for line in block.lines:
            text = line.strip()
            if not text:
                continue
            if text.startswith(ASK):
                stage.asks.append(text[len(ASK):].strip())
            elif row := nodes(text):
                rows.append(row)
        if stage.asks:
            stage.pool = [n for row in rows for n in row]
        else:
            stage.segs = rows
        if stage.asks or stage.segs:
            out.append(stage)
    if not out:
        spec_lib.die(f"{sp.path.name}：一个阶段区块都没有")
    return out


def render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, str]:
    items = stages(sp)
    asked = any(st.asks for st in items)          # 思维导图那种形状
    n_asks = sum(len(s.asks) for s in items)
    n_pool = sum(len(s.pool) for s in items)
    total_segs = sum(len(s.segs) for s in items)
    total_nodes = sum(len(seg) for s in items for seg in s.segs)

    # 两种形状数的东西不一样：段 / 问。`tally` 上页头，`small` 上目录页
    tally = f"{n_asks} 问 · {n_pool} 词" if asked else f"{total_segs} 段"
    small = tally if asked else f"{total_segs} 段 · {total_nodes} 个词"
    what = (f"按老师给的章节分组，{n_asks} 个问题 {n_pool} 个词" if asked
            else f"按情节的五个阶段分组，{total_segs} 段 {total_nodes} 个词")

    # 段号跨阶段连续编，所以在这儿一次编完再交给模板。
    # 问题的号相反，**每章从 1 起** —— 那是老师在导图上编的号，模板里走 loop.index
    no = 0
    ctx = []
    for stage in items:
        segs = []
        for row in stage.segs:
            no += 1
            segs.append({"no": no, "nodes": row})
        ctx.append({"name": stage.name, "short": stage.short,
                    "is_climax": stage.is_climax, "segs": segs,
                    "asks": stage.asks, "pool": stage.pool})

    heading = sp.title or "复述地图"
    meta = " · ".join(x for x in (sp.get("book"),
                                 f'第 {sp.get("pages")} 页' if sp.get("pages") else "",
                                 tally) if x)

    body = tmpl.body(
        "retell/sheet.html",
        heading=heading,
        meta=meta,
        task=sp.get("task", ""),
        stages=ctx,
        asked=asked,
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading} 复述地图",
            description=f"{heading} 的复述关键词地图，{what}，A4 打印。",
            body=body,
            emoji="🗺️",
            css=("print.css", "retell.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → retell/{out.name}  （{len(items)} {'章' if asked else '阶段'} · {small}）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, small


def build_index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="复述故事 · 英语",
        description="把整个故事的关键词收到一张纸上 —— 一段一串，或者一章几问配一批词，看着讲一遍。A4 打印。",
        emoji="🗺️",
        h1="复述故事",
        sub=f"整个故事的关键词收到一张纸上，看着讲一遍 · 共 {len(entries)} 份",
        sections=[(None, [
            {"href": f'{e["stem"]}.html',
             "label": e["title"],
             "small": " · ".join(x for x in (e["small"], e["book"]) if x),
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
        pdf_ok, small = render(sp, out_dir, pdf)
        entries.append({"stem": path.stem, "title": sp.title or path.stem,
                        "small": small, "book": sp.get("book", ""),
                        "pdf": pdf_ok})

    build_index(out_dir, entries)
