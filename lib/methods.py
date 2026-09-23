"""学习方法 —— `storage/spec/methods.txt` 的读取口径，三科共用。

一课提炼一个方法，名字借那一课（田忌法、庐山法……），语文园地也算一课。两个下游：

    src/generator/chinese/methods.py   语文 · 学习方法：一课一张卡，照课本顺序
    src/generator/english/review.py    打卡评价「下次读之前」：只写方法名，
                                       图标和问句由这儿补上

报告里用了一个查不到的方法名，当场报错 —— 印出来的就是一个没人跟她解释过的词。

想在别处（数学秘籍、语文抽查单）用同一套方法，从这儿取，别再解析一遍那份 spec。
"""

from __future__ import annotations

from typing import NamedTuple

from lib import paths, spec as spec_lib

METHODS = paths.spec("methods.txt")
UNIT = "单元"          # [单元] 第一单元 | 单元页那句话 —— 单元分隔，不是方法


class Method(NamedTuple):
    name: str       # 田忌法
    no: str         # 7；语文园地 / 交流平台是空串
    title: str      # 田忌赛马；语文园地二
    ask: str        # 换个顺序行不行？
    story: str      # 课：课文里那件事
    icon: str       # 🐎
    step: str       # 解决问题 —— 五步里用在哪一步
    use: str        # 作业里怎么用（给大人看的）
    idea: dict      # 理：{name, kind, parts} 右半张卡的常识，parts 见 _idea_parts
    tools: list     # 用：[{quote, who, how}] 课本里的一句（——朝代·人名）→ 遇到问题时怎么用

    @property
    def source(self) -> str:
        """卡片底下那行出处：「第 7 课《田忌赛马》」或「语文园地二」。"""
        return f"第 {self.no} 课《{self.title}》" if self.no else self.title


BOXES = {"例：": ("eg", "📖 例子"), "实验：": ("lab", "🔬 实验")}


def _idea_parts(text: str) -> list[dict]:
    """「理」那段话按 // 分块，一块一个作用（大段话孩子不看）：

        第一块          lead  这是什么
        「例：」开头     eg    课文里的例子，进小框
        「实验：」开头   lab   研究里的实验，进小框
        最后一块（非框） take  落点，前面带 →
        其余            p     普通一句
    """
    raw = [x.strip() for x in text.split("//") if x.strip()]
    out = []
    for i, seg in enumerate(raw):
        box = next((k for k in BOXES if seg.startswith(k)), None)
        if box:
            kind, label = BOXES[box]
            out.append({"kind": kind, "label": label, "text": seg[len(box):].strip()})
        elif i == 0:
            out.append({"kind": "lead", "label": "", "text": seg})
        elif i == len(raw) - 1:
            out.append({"kind": "take", "label": "", "text": seg})
        else:
            out.append({"kind": "p", "label": "", "text": seg})
    return out


def _method(b, steps: dict) -> Method:
    where = f"{METHODS.name} [{b.name}]"
    first, _, rest = b.head.partition(" ")
    no, title = (first, rest.strip()) if first.isdigit() else ("", b.head.strip())
    step = b.attr("step", "")
    if step not in steps:
        spec_lib.die(f"{where}：step={step!r} 不在 steps 里（{'、'.join(steps)}）")
    story, idea, tools = "", None, []
    for line in b.notes():
        key, _, text = line.partition(" ")
        text = text.strip()
        if key == "课":
            story = text
        elif key == "理":
            parts = [x.strip() for x in text.split("|")]
            if len(parts) != 3:
                spec_lib.die(f"{where}：「理」是「常识名 | 哪一类 | 讲给孩子的话」，读到 {text!r}")
            idea = {"name": parts[0], "kind": parts[1], "parts": _idea_parts(parts[2])}
        elif key == "用":
            quote, arrow, how = text.partition("→")
            if not arrow:
                spec_lib.die(f"{where}：「用」是「课本里的一句 → 怎么用」，读到 {text!r}")
            words, _, who = quote.partition("——")
            tools.append({"quote": words.strip(), "who": who.strip(), "how": how.strip()})
        else:
            spec_lib.die(f"{where}：缩进行以「课 / 理 / 用」起头，读到 {line!r}")
    if not story or not idea:
        spec_lib.die(f"{where}：「课」和「理」都得有")
    return Method(b.name, no, title, b.tag, story, b.attr("icon", ""), step,
                  b.attr("use", ""), idea, tools)


def _parse():
    sp = spec_lib.parse(METHODS)
    steps = {}
    for part in sp.get("steps", "").split(","):
        key, _, icon = part.strip().partition("=")
        if key:
            steps[key.strip()] = icon.strip()
    units: list[dict] = []
    for b in sp.blocks:
        if b.name == UNIT:
            units.append({"head": b.head, "motto": b.tag, "methods": []})
            continue
        if not units:
            spec_lib.die(f"{METHODS.name} [{b.name}]：第一个方法前面要先有一个 [单元]")
        units[-1]["methods"].append(_method(b, steps))
    ideas = [m.idea["name"] for u in units for m in u["methods"]]
    dup = sorted({x for x in ideas if ideas.count(x) > 1})
    if dup:
        spec_lib.die(f"{METHODS.name}：常识重复了（{'、'.join(dup)}）—— 一课一个，不重复")
    return steps, units


def load() -> dict[str, Method]:
    _, units = _parse()
    return {m.name: m for u in units for m in u["methods"]}


def book() -> dict:
    """整册，照课本顺序：{steps: {步: 图标}, units: [{head, motto, methods}]}。"""
    steps, units = _parse()
    return {"steps": steps, "units": units}


def get(name: str, where: str) -> Method:
    box = load()
    if name not in box:
        spec_lib.die(f"{where}：方法「{name}」不在 {METHODS.name} 里（有：{'、'.join(box)}）"
                     "—— 要加新方法先写进那份 spec")
    return box[name]
