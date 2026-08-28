"""语文 · 今日练习 —— 看拼音写汉字的 A4 打印单。

spec 在 storage/spec/chinese/practice/<YYYYMMDD>.txt，产物落在 dist/chinese/practice/：

    <日期>.html / .pdf              题面版（格子空着）
    <日期>-answers.html / .pdf      答案版（格子里印楷体字，给家长批改）
    index.html                      目录页（**答案版不列进去**）

拼音候选可以让喂数据台先给（`../../feeder/bin/feeder pinyin 潮 据 堤` 或者
直接喂生字表照片），它会把**多音字全标出来** —— 但按课文语境定音仍然是人的活。

这个栏目的核心职责是**标对拼音**，也是唯一容易出错的地方：
脚本只排版、不判断读音。多音字必须在 spec 里手写，按课文语境定音
（`单=dān` 不是 shàn、`悄悄=qiāo qiāo` 不是 qiǎo）。
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "practice")

# 排版旋钮的默认值。cell 和 copies 是「排满一页 A4」的两个主要旋钮：
# 装不满就加大，快溢出到第二页就调小。
DEFAULTS = {"title": "今日练习", "hint": "看拼音，在田字格里写汉字。",
            "copies": 1, "cell": 15, "gap": 4, "py": 11}

try:                                     # 可选增强：只用来补单音字
    from pypinyin import Style, pinyin
except ImportError:
    pinyin = None


def _syllables(word: str, raw: str, sp: spec_lib.Spec) -> list[str]:
    """取一个词的拼音音节，并校验音节数 == 字数。"""
    syl = raw.split()

    if not syl:
        if pinyin is None:
            spec_lib.die(
                f"{sp.path.name}：「{word}」没写拼音，而且没装 pypinyin。\n"
                f"   请在 spec 里写 {word}=" + " ".join(["?"] * len(word)) +
                "\n   （或 pip3 install pypinyin，但多音字仍须手写）")
        syl = [s[0] for s in pinyin(word, style=Style.TONE)]

    if len(syl) != len(word):
        spec_lib.die(
            f"{sp.path.name}：「{word}={raw}」音节数 {len(syl)} 与字数 {len(word)} 不符。\n"
            f"   应该写成 {word}=" + " ".join(["?"] * len(word)))
    return syl


def _render(sp: spec_lib.Spec, out_dir: Path, *, pdf: bool, answers: bool) -> bool:
    """渲染一份练习单。返回 PDF 是否真的生成出来了。"""
    copies_all = sp.int_("copies", DEFAULTS["copies"])
    cell = sp.int_("cell", DEFAULTS["cell"])
    gap = sp.int_("gap", DEFAULTS["gap"])
    py_size = sp.int_("py", DEFAULTS["py"])

    if not sp.blocks:
        spec_lib.die(f"{sp.path.name} 里没有任何 [区块]")

    blocks, total = [], 0
    for b in sp.blocks:
        items = b.items()
        if not items:
            continue
        n = int(b.attr("copies", copies_all))
        blocks.append({
            "label": " ".join(x for x in (b.name, b.head) if x),
            # 一项 = 拼音行 + n 行田字格。题面版格子里是空的，答案版印字
            "rows": [{"py": _syllables(w, raw, sp),
                      "copies": n,
                      "chars": list(w) if answers else [""] * len(w)}
                     for w, raw in items],
        })
        total += len(items)

    heading = sp.get("title", DEFAULTS["title"]) + ("（答案）" if answers else "")
    if sp.get("date"):
        heading += f'　{sp.get("date")}'

    hint_text = sp.get("hint", DEFAULTS["hint"])

    body = tmpl.body(
        "practice/sheet.html",
        cell=cell, gap=gap, py_size=py_size,
        heading=heading,
        info=page.sheet_info("得分", show=not answers),
        hint=hint_text if hint_text and not answers else "",
        blocks=blocks,
        total=total,
    )

    name = sp.path.stem + ("-answers" if answers else "")
    out = page.write(
        out_dir / f"{name}.html",
        page.render(
            title=heading,
            body=body,
            emoji="📖",
            css=("print.css", "grid.css", "practice.css"),
            root="../..",
            noindex=True,          # 练习单不需要被搜索引擎收录
        ),
    )
    print(f"    → {out.relative_to(out.parent.parent.parent)}  （{total} 项）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


def _index(out_dir: Path, entries: list[dict]) -> None:
    """目录页。GitHub Pages 不列目录，所以必须自己生成一份。"""
    page.listing(
        out_dir,
        title="今日练习 · 语文",
        description="看拼音写汉字的 A4 打印单，点进去直接打印。",
        emoji="📖",
        h1="今日练习",
        sub=f"看拼音写汉字 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有练习单 —— 往 storage/spec/chinese/practice/ 放一份 spec",
    )
    print(f"    → practice/index.html  （{len(entries)} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "practice"
    specs = sorted(SPECS.glob("*.txt"), reverse=True)   # 新的排前面

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok = _render(sp, out_dir, pdf=pdf, answers=False)
        _render(sp, out_dir, pdf=pdf, answers=True)

        counts = {}
        for b in sp.blocks:
            if b.items():
                counts[b.name] = counts.get(b.name, 0) + len(b.items())
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("title", DEFAULTS["title"]) + (f'　{sp.get("date")}' if sp.get("date") else ""),
            "small": " · ".join(f"{k} {v} 项" for k, v in counts.items()),
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
