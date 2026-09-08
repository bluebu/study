"""语文 —— 把各栏目串起来。

    practice/   今日练习：看拼音写汉字 → A4 田字格练习单（附答案版）
    check/      抽查单：学完一课，家长照着问一遍 → 题面版 + 家长版
    overview/   教材总览：一册一份的总表，哪篇要背、哪首要默写一眼看到

一个栏目一个模块，各管各的产物目录，这里只按顺序调。

**每个栏目单独 try**：一个栏目的 spec 写错，不该把另外两个也带下水
（英语那边踩过 —— review 和 ket 挤在一个函数里，review 提前 return
就把后面的栏目静默跳过了）。

科目准则和各栏目口径见同目录的 CLAUDE.md。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from check import build_check          # noqa: E402
from overview import build_overview    # noqa: E402
from practice import build_practice    # noqa: E402

SECTIONS = [
    ("今日练习", build_practice),
    ("抽查单", build_check),
    ("教材总览", build_overview),
]


def build(dist: Path, pdf: bool = False) -> None:
    for name, fn in SECTIONS:
        try:
            fn(dist, pdf=pdf)
        except SystemExit:
            raise                     # spec 写错要立刻停，别把坏数据发上线
        except Exception:
            print(f"    ✗ {name}：{traceback.format_exc().splitlines()[-1]}")
            raise
