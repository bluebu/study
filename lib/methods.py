"""学习方法 —— `storage/spec/methods.txt` 的读取口径，三科共用。

一课提炼一个方法，名字借那一课（田忌法、庐山法……）。两个下游：

    src/generator/chinese/methods.py   语文 · 学习方法：整册的方法卡片，照课本顺序
    src/generator/english/review.py    打卡评价「下次读之前」：只写方法名，
                                       图标和问句由这儿补上

报告里用了一个查不到、或者还没学到的方法，当场报错 —— 印出来的就是一个
没人跟她解释过的词，那又变回大人在讲道理。

想在别处（数学秘籍、语文抽查单）用同一套方法，从这儿取，别再解析一遍那份 spec。
"""

from __future__ import annotations

from typing import NamedTuple

from lib import paths, spec as spec_lib

METHODS = paths.spec("methods.txt")
UNIT = "单元"          # [单元] 第一单元 —— 单元分隔，不是方法


class Method(NamedTuple):
    name: str       # 田忌法
    no: str         # 7（语文课号）
    title: str      # 田忌赛马
    ask: str        # 换个顺序行不行？
    story: str      # 课文里那件事
    icon: str       # 🐎
    step: str       # 想 —— 遇到难题时用在哪一步
    use: str        # 作业里怎么用（给大人看的）
    learned: bool   # 学过没有（课号 <= spec 头的 learned）


def _parse():
    sp = spec_lib.parse(METHODS)
    learned = sp.int_("learned", 0)
    steps = {}
    for part in sp.get("steps", "").split(","):
        key, _, icon = part.strip().partition("=")
        if key:
            steps[key.strip()] = icon.strip()
    units: list[dict] = []
    for b in sp.blocks:
        if b.name == UNIT:
            units.append({"head": b.head, "methods": []})
            continue
        no, _, title = b.head.partition(" ")
        step = b.attr("step", "")
        if step not in steps:
            spec_lib.die(f"{METHODS.name} [{b.name}]：step={step!r} 不在 steps 里（{'、'.join(steps)}）")
        if not units:
            spec_lib.die(f"{METHODS.name} [{b.name}]：第一个方法前面要先有一个 [单元]")
        m = Method(b.name, no, title.strip(), b.tag, " ".join(b.notes()), b.attr("icon", ""),
                   step, b.attr("use", ""), int(no) <= learned)
        units[-1]["methods"].append(m)
    return learned, steps, units


def load() -> dict[str, Method]:
    _, _, units = _parse()
    return {m.name: m for u in units for m in u["methods"]}


def book() -> dict:
    """整册，照课本顺序：{learned, steps: {步: 图标}, units: [{head, methods}]}。"""
    learned, steps, units = _parse()
    return {"learned": learned, "steps": steps, "units": units}


def get(name: str, where: str) -> Method:
    box = load()
    if name not in box:
        spec_lib.die(f"{where}：方法「{name}」不在 {METHODS.name} 里（有：{'、'.join(box)}）"
                     "—— 要加新方法先写进那份 spec")
    m = box[name]
    if not m.learned:
        spec_lib.die(f"{where}：「{name}」出自第 {m.no} 课《{m.title}》，她还没学到"
                     f"（{METHODS.name} 的 learned 写的是学到哪一课）—— 换一个学过的方法")
    return m
