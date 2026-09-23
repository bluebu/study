"""方法工具箱 —— `storage/spec/methods.txt` 的读取口径，三科共用。

每个方法借语文课本里的一课起名字（田忌法、庐山法……），报告里只写方法名，
出自哪课、问自己的那一句、课文里那件事，都从这份 spec 取。名字写错当场报错 ——
一个查不到的方法名印出来，孩子看到的就是一个没人解释过的词。

想在别处（数学秘籍、语文抽查单）用同一套方法，从这儿取，别再解析一遍那份 spec。
"""

from __future__ import annotations

from typing import NamedTuple

from lib import paths, spec as spec_lib

METHODS = paths.spec("methods.txt")


class Method(NamedTuple):
    name: str       # 田忌法
    no: str         # 7（语文课号）
    title: str      # 田忌赛马
    ask: str        # 换个顺序行不行？
    story: str      # 同样三匹马，换个出场顺序……


def load() -> dict[str, Method]:
    box = {}
    for b in spec_lib.parse(METHODS).blocks:
        no, _, title = b.head.partition(" ")
        box[b.name] = Method(b.name, no, title.strip(), b.tag, " ".join(b.notes()))
    return box


def get(name: str, where: str) -> Method:
    box = load()
    if name not in box:
        spec_lib.die(f"{where}：方法「{name}」不在工具箱里（{METHODS.name} 里有："
                     f"{'、'.join(box)}）—— 要加新方法先写进那份 spec")
    return box[name]
