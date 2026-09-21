"""语文 · 写字 —— 一字一行的笔顺单。

spec 在 storage/spec/chinese/writing/<课号>.txt，产物落在 dist/chinese/writing/：

    <课号>.html / .pdf      笔顺单
    index.html              目录页

**这个栏目练的是「一笔一笔怎么写下来」**，不是认字也不是默写：一个字一行，
左边一个大田字格印整字，右边把笔画逐笔累加铺开 —— 第 N 格画前 N 笔，
第 N 笔红色、之前的灰黑，起笔处点一个绿点。孩子照着号码跟着写。

## 字形不走字体，走 SVG

田字格里的范字**不是用 --font-kai 渲染的**，是 storage/data/chinese/stroke/
里逐笔的 SVG path 画出来的。这么做有两个好处，第二个是这个栏目的硬需求：

1. **本地和线上字形一致**。别的栏目的范字本地 mac 落在 Kaiti、线上 ubuntu
   落在 AR PL UKai，字形有差（CLAUDE.md 的「字体」那节）。这儿两边都是同一份
   path 数据，家长点「打印单」拿到的和本地看到的一模一样
2. **字体给不了笔顺**。一个字在字体里是一个整体字形，切不出「第 3 笔是哪一段」

笔顺数据的来源、许可、怎么补字，见 DATA.md 的「笔顺字形」那一档。
缺字**当场报错**并给出补数据的命令 —— 静默少印一个字，孩子那一行就白练了。

## 坐标系

数据是 1024×1024 的字身框，**Y 轴朝上**（字体的坐标习惯），所以模板里统一套
`translate(0,900) scale(1,-1)` 翻过来。900 不是 1024 —— 字身框的基线在 y=900 上下，
这个数字是 Make Me a Hanzi 定的，别改成 1024（整字会往上跑出格子）。
"""

from __future__ import annotations

import json
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "writing")
STROKES = paths.data("chinese", "stroke")

DEFAULTS = {
    "title": "写字 · 笔顺",
    "hint": "红色是这一笔新写的，绿点是起笔的地方。照着号码一笔一笔跟着写。",
    "big": 24,      # 左边大田字格的边长（mm）
    "step": 13,     # 右边逐笔小格的边长（mm）。12 画的字一行正好排满 186mm 版心
}

# 一行最多排几个小格。版心 186mm - 大格 24 - 间距 3 = 159mm，13mm 一格排得下 12 个。
# 这批字最多 12 画（提、锈），正好不折行；真遇到 13 画以上的字 CSS 会自动折到下一行，
# 版式不会坏，只是那一行高一点。
STEPS_PER_ROW = 12


def _load(ch: str) -> dict:
    """取一个字的笔顺数据。缺了就报错 —— 不静默跳过。"""
    f = STROKES / f"{ch}.json"
    if not f.is_file():
        spec_lib.die(
            f"没有「{ch}」的笔顺数据：{f.relative_to(paths.ROOT)}\n"
            f"   补一个：python3 tools/fetch-stroke.py {ch}")
    d = json.loads(f.read_text(encoding="utf-8"))
    if not d.get("strokes"):
        spec_lib.die(f"「{ch}」的笔顺数据是空的：{f.relative_to(paths.ROOT)}")
    return d


def _char(ch: str, py: str) -> dict:
    """一个字的上下文：整字 + 逐笔累加的每一格。

    模板只管摆 <path>，画哪几条、哪条是新的、绿点点在哪，全在这儿算完。
    """
    d = _load(ch)
    strokes, medians = d["strokes"], d["medians"]

    steps = []
    for i in range(len(strokes)):
        sx, sy = medians[i][0]          # 新笔画中线的第一个点 = 起笔处
        steps.append({
            "n": i + 1,
            # cls 在这儿选好，模板里不写 {% if %} —— 模板不做计算
            "paths": [{"d": p, "cls": "new" if j == i else "old"}
                      for j, p in enumerate(strokes[:i + 1])],
            "dot": {"x": sx, "y": sy},
        })

    return {
        "char": ch,
        "py": py,
        "total": len(strokes),
        "paths": [{"d": p, "cls": "old"} for p in strokes],   # 大格里的整字
        "steps": steps,
        # 笔画多到一行排不下时，让这一行的小格换行（类名给模板，别在模板里比大小）
        "wrap": "wrap" if len(strokes) > STEPS_PER_ROW else "",
    }


def _syllables(word: str, raw: str, sp: spec_lib.Spec) -> list[str]:
    """取一个词的拼音音节，并校验音节数 == 字数。

    **这个栏目不自动补拼音**：纸是照着写的，拼音错一个孩子就读错一个，
    多音字（俱乐部的「乐」= lè）只有人按词语语境定得了。所以 spec 里必须写。
    """
    syl = raw.split()
    if not syl:
        spec_lib.die(
            f"{sp.path.name}：「{word}」没写拼音。\n"
            f"   spec 里写成 {word}=" + " ".join(["?"] * len(word)))
    if len(syl) != len(word):
        spec_lib.die(
            f"{sp.path.name}：「{word}={raw}」音节数 {len(syl)} 与字数 {len(word)} 不符。\n"
            f"   应该写成 {word}=" + " ".join(["?"] * len(word)))
    return syl


def _render(sp: spec_lib.Spec, out_dir: Path, *, pdf: bool) -> tuple[bool, int, int]:
    """渲染一份笔顺单。返回 (PDF 出了没, 词数, 字数)。"""
    if not sp.blocks:
        spec_lib.die(f"{sp.path.name} 里没有任何 [区块]")

    blocks, n_words, n_chars, n_strokes = [], 0, 0, 0
    for b in sp.blocks:
        items = b.items()
        if not items:
            continue
        words = []
        for w, raw in items:
            syl = _syllables(w, raw, sp)
            chars = [_char(c, s) for c, s in zip(w, syl)]
            words.append({"word": w, "py": " ".join(syl), "chars": chars})
            n_strokes += sum(c["total"] for c in chars)
            n_chars += len(w)
        blocks.append({
            "label": " ".join(x for x in (b.name, b.head) if x),
            "words": words,
        })
        n_words += len(words)

    heading = sp.get("title", DEFAULTS["title"])

    body = tmpl.body(
        "writing/sheet.html",
        big=sp.int_("big", DEFAULTS["big"]),
        step=sp.int_("step", DEFAULTS["step"]),
        heading=heading,
        info=page.sheet_info("得分"),
        hint=sp.get("hint", DEFAULTS["hint"]),
        blocks=blocks,
        total=f"{n_words} 个词 · {n_chars} 个字 · {n_strokes} 笔",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=heading,
            body=body,
            emoji="📖",
            css=("print.css", "grid.css", "writing.css"),
            root="../..",
            noindex=True,          # 练习单不进搜索引擎，同今日练习
        ),
    )
    print(f"    → {out.relative_to(out.parent.parent.parent)}"
          f"  （{n_words} 词 · {n_chars} 字 · {n_strokes} 笔）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf")), n_words, n_chars


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="写字 · 语文",
        description="一字一行的笔顺单：左边整字，右边一笔一笔铺开，照着号码写。",
        emoji="📖",
        h1="写字",
        sub=f"笔顺一笔一笔铺开 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有笔顺单 —— 往 storage/spec/chinese/writing/ 放一份 spec",
    )
    print(f"    → writing/index.html  （{len(entries)} 份）")


def build_writing(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "writing"
    entries = []
    for path in spec_lib.specs(SPECS):          # 按课号排，和抽查单一致
        sp = spec_lib.parse(path)
        pdf_ok, n_words, n_chars = _render(sp, out_dir, pdf=pdf)
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("title", DEFAULTS["title"]),
            "small": f"{n_words} 个词 · {n_chars} 个字",
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
