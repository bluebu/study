"""语文 · 写字 —— 一字一行的笔顺单。

spec 在 storage/spec/chinese/writing/<课号>.txt，产物落在 dist/chinese/writing/：

    <课号>.html / .pdf      笔顺单
    index.html              目录页

**这个栏目练的是「一笔一笔怎么写下来」**，不是认字也不是默写：一个字一行，
左边一个大田字格印整字、底下标偏旁部首，右边把笔画逐笔累加铺开 ——
第 N 格画前 N 笔，第 N 笔红色、之前的浅灰，起笔处一个绿点，格子下面是
号码和**这一笔的中文名字**（横、竖、横折钩……）。

## 三个数据源，各管一段

    storage/data/chinese/stroke/<字>.json   字形：逐笔 SVG path + 中线（画出来的形）
    storage/data/chinese/stroke-order.json  笔画码：一个字一串字母，一笔一个（叫什么）
    storage/data/chinese/stroke-names.json  码 → 笔画名（原样存，含要人定的）

**两份字形数据必须笔画数一致**，否则第 5 笔的名字会标到第 6 笔上 ——
比不标更糟。所以每个字都当场比一次，不等就报错。

判断落在 spec 那一层（人写的）：

    storage/spec/chinese/radical.txt        逐字归部 + 部首叫什么
    storage/spec/chinese/stroke-name.txt    一码两名 / 内部代号，哪个才是纸上要印的

## 字形不走字体，走 SVG

田字格里的范字**不是用 --font-kai 渲染的**，是 stroke/ 里逐笔的 SVG path 画出来的。
两个好处，第二个是这个栏目的硬需求：

1. **本地和线上字形一致**。别的栏目的范字本地 mac 落在 Kaiti、线上 ubuntu
   落在 AR PL UKai，字形有差（CLAUDE.md 的「字体」那节）。这儿两边都是同一份
   path 数据，家长点「打印单」拿到的和本地看到的一模一样
2. **字体给不了笔顺**。一个字在字体里是一个整体字形，切不出「第 3 笔是哪一段」

## 坐标系

字形数据是 1024×1024 的字身框，**Y 轴朝上**（字体的坐标习惯），所以模板里统一套
`translate(0,900) scale(1,-1)` 翻过来。900 不是 1024 —— 字身框的基线在 y=900 上下，
这个数字是 Make Me a Hanzi 定的，别改成 1024（整字会往上跑出格子）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "writing")
STROKES = paths.data("chinese", "stroke")
ORDER = paths.data("chinese", "stroke-order.json")
NAMES = paths.data("chinese", "stroke-names.json")
RADICAL_SPEC = paths.spec("chinese", "radical.txt")
NAME_SPEC = paths.spec("chinese", "stroke-name.txt")

DEFAULTS = {
    "title": "写字 · 笔顺",
    "hint": "红色是这一笔新写的，绿点是起笔的地方。照着号码一笔一笔跟着写，念出笔画的名字。",
    "big": 26,      # 左边大田字格的边长（mm）
    "step": 16,     # 右边逐笔小格的边长（mm）
}

# 一行最多排几个小格。版心 186mm − 大格 26 − 间距 3 = 157mm，16mm 一格排得下 9 个。
# 超过就折行（CSS 管），版式不坏，只是那一行高一倍。
# **笔画名要印在格子底下**，所以格子不能再小了：「横折折折钩」五个字得塞进这个宽度。
STEPS_PER_ROW = 9


def _load_json(f: Path, what: str) -> dict:
    if not f.is_file():
        spec_lib.die(f"缺{what}：{f.relative_to(paths.ROOT)}")
    return json.loads(f.read_text(encoding="utf-8"))


def _radicals() -> tuple[dict[str, str], dict[str, str]]:
    """读人写的部首表 → ({部首: 名称}, {字: "部首|名称"})。"""
    sp = spec_lib.parse(RADICAL_SPEC)
    names, by_char = {}, {}
    for b in sp.blocks:
        target = names if b.name == "部首名" else by_char if b.name == "归部" else None
        if target is None:
            continue
        for k, v in b.items():
            target[k] = v
    return names, by_char


def _stroke_names() -> tuple[dict[str, str], dict[str, str]]:
    """读人写的笔画名判断 → ({码: 名}, {"字.笔序": 名})。"""
    sp = spec_lib.parse(NAME_SPEC)
    default, by_char = {}, {}
    for b in sp.blocks:
        target = default if b.name == "默认名" else by_char if b.name == "按字" else None
        if target is None:
            continue
        for k, v in b.items():
            target[k] = v
    return default, by_char


class Dict_:
    """三份表一起加载，供一次构建复用。"""

    def __init__(self) -> None:
        self.order = _load_json(ORDER, "笔画码表")
        self.names = _load_json(NAMES, "笔画名表")
        self.rad_names, self.rad_by_char = _radicals()
        self.nm_default, self.nm_by_char = _stroke_names()

    # ── 笔画名 ──────────────────────────────────────────────
    def stroke_name(self, ch: str, i: int, code: str) -> str:
        """第 i 笔（从 1 数）叫什么。取名次序：按字 → 默认名 → 数据里的 name。"""
        hit = self.nm_by_char.get(f"{ch}.{i}")
        if hit:
            return hit
        hit = self.nm_default.get(code)
        if hit:
            return hit

        raw = self.names.get(code, {}).get("name", "")
        # 一码两名（横撇|横钩）和内部代号（点2）都不能直接印 —— 印上去孩子会当成
        # 这一笔的正式名字记住。两处都没给就停下来问人。
        if not raw or "|" in raw or re.search(r"\d", raw):
            spec_lib.die(
                f"「{ch}」第 {i} 笔的笔画名要人定：码 {code} 在数据里叫「{raw or '(没有)'}」。\n"
                f"   在 {NAME_SPEC.relative_to(paths.ROOT)} 里补一条：\n"
                f"     [按字]  {ch}.{i}=<名字>      ← 只改这一个字\n"
                f"     [默认名] {code}=<名字>         ← 这个码一律这么叫")
        return raw

    # ── 部首 ────────────────────────────────────────────────
    def radical(self, ch: str) -> tuple[str, str]:
        """(部首, 这个位置叫什么)。"""
        raw = self.rad_by_char.get(ch)
        if not raw:
            spec_lib.die(
                f"「{ch}」还没归部。\n"
                f"   在 {RADICAL_SPEC.relative_to(paths.ROOT)} 的 [归部] 里补一条："
                f"{ch}=<部首>（或 {ch}=<部首>|<这个位置叫什么>）")
        rad, _, name = raw.partition("|")
        rad = rad.strip()
        name = name.strip() or self.rad_names.get(rad, "")
        if not name:
            spec_lib.die(
                f"部首「{rad}」（{ch} 用到）还没有名字。\n"
                f"   在 {RADICAL_SPEC.relative_to(paths.ROOT)} 的 [部首名] 里补一条：{rad}=<叫什么>")
        return rad, name


def _char(ch: str, py: str, d: Dict_) -> dict:
    """一个字的上下文：整字 + 部首 + 逐笔累加的每一格。

    模板只管摆 <path>，画哪几条、哪条是新的、绿点点在哪、这一笔叫什么，
    全在这儿算完。
    """
    f = STROKES / f"{ch}.json"
    if not f.is_file():
        spec_lib.die(
            f"没有「{ch}」的字形数据：{f.relative_to(paths.ROOT)}\n"
            f"   补一个：python3 tools/fetch-stroke.py {ch}")
    g = json.loads(f.read_text(encoding="utf-8"))
    strokes, medians = g["strokes"], g["medians"]

    codes = d.order.get(ch, "")
    if not codes:
        spec_lib.die(
            f"没有「{ch}」的笔画码（笔画叫什么全靠它）：{ORDER.relative_to(paths.ROOT)}\n"
            f"   补一个：python3 tools/fetch-stroke.py {ch}")
    # ⚠️ 两份数据源，笔画数必须对得上。差一笔，往后每一笔的名字都会错位 ——
    #    而纸上看不出来（名字都是真笔画名，只是标错了地方）。
    if len(codes) != len(strokes):
        spec_lib.die(
            f"「{ch}」两份数据笔画数对不上：字形 {len(strokes)} 笔、笔画码 {len(codes)} 笔。\n"
            f"   名字会整体错位，所以停在这儿。重取一次：\n"
            f"     python3 tools/fetch-stroke.py --refresh {ch}")

    steps = []
    for i in range(len(strokes)):
        sx, sy = medians[i][0]          # 新笔画中线的第一个点 = 起笔处
        steps.append({
            "n": i + 1,
            "name": d.stroke_name(ch, i + 1, codes[i]),
            # cls 在这儿选好，模板里不写 {% if %} —— 模板不做计算
            "paths": [{"d": p, "cls": "new" if j == i else "old"}
                      for j, p in enumerate(strokes[:i + 1])],
            "dot": {"x": sx, "y": sy},
        })

    rad, rad_name = d.radical(ch)
    return {
        "char": ch,
        "py": py,
        "total": len(strokes),
        "rad": rad,
        "rad_name": rad_name,
        "paths": [{"d": p, "cls": "old"} for p in strokes],   # 大格里的整字
        "steps": steps,
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


def _render(sp: spec_lib.Spec, out_dir: Path, d: Dict_, *, pdf: bool) -> tuple[bool, str]:
    """渲染一份笔顺单。返回 (PDF 出了没, 目录页上的小字)。"""
    if not sp.blocks:
        spec_lib.die(f"{sp.path.name} 里没有任何 [区块]")

    blocks, n_chars, n_strokes, counts = [], 0, 0, []
    for b in sp.blocks:
        items = b.items()
        if not items:
            continue
        words = []
        for w, raw in items:
            syl = _syllables(w, raw, sp)
            chars = [_char(c, s, d) for c, s in zip(w, syl)]
            words.append({
                "word": w,
                "py": " ".join(syl),
                "chars": chars,
                # 单字条目（写字表）不用再在上面重复一行词 —— 字就在大格里
                "show_word": len(w) > 1,
            })
            n_strokes += sum(c["total"] for c in chars)
            n_chars += len(w)
        blocks.append({
            "label": " ".join(x for x in (b.name, b.head) if x),
            # 「要求会默写」的徽章。开关在 spec 的区块属性上：copy=1
            "must_copy": bool(b.attr("copy", "")),
            "words": words,
        })
        counts.append(f"{b.name} {len(items)} 项")

    heading = sp.get("title", DEFAULTS["title"])

    body = tmpl.body(
        "writing/sheet.html",
        big=sp.int_("big", DEFAULTS["big"]),
        step=sp.int_("step", DEFAULTS["step"]),
        heading=heading,
        info=page.sheet_info("得分"),
        hint=sp.get("hint", DEFAULTS["hint"]),
        blocks=blocks,
        total=f"{n_chars} 个字 · {n_strokes} 笔",
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
          f"  （{' · '.join(counts)} · {n_chars} 字 · {n_strokes} 笔）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf")), " · ".join(counts)


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="写字 · 语文",
        description="一字一行的笔顺单：左边整字和部首，右边一笔一笔铺开，每笔标名字。",
        emoji="📖",
        h1="写字",
        sub=f"笔顺一笔一笔铺开 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有笔顺单 —— 往 storage/spec/chinese/writing/ 放一份 spec",
    )
    print(f"    → writing/index.html  （{len(entries)} 份）")


def build_writing(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "writing"
    specs = spec_lib.specs(SPECS)                # 按课号排，和抽查单一致
    if not specs:
        return

    d = Dict_()                                  # 三份表加载一次，所有 spec 共用
    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, small = _render(sp, out_dir, d, pdf=pdf)
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("title", DEFAULTS["title"]),
            "small": small,
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
