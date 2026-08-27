"""英语 —— 把各栏目串起来。

    ket/         词汇默写：KET 核心词 → 四线三格 A4 卷
    review/      打卡评价：朗读录音 + 教材原文 → 一份能和下次比的成绩单
    homework/    每日打卡：群公告 → A4 打印单

一个栏目一个模块，各管各的产物目录，这里只按顺序调。

**每个栏目单独 try**：一个栏目的 spec 写错，不该把另外两个也带下水。
（原先是 review 和 ket 挤在一个函数里，review 那段一旦提前 return，
后面的栏目就被静默跳过 —— 注释里当时写的是「ket 放前面」，绕过而不是解决。）

科目准则和各栏目口径见同目录的 CLAUDE.md。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ket           # noqa: E402
from homework import build_homework  # noqa: E402
from review import build_review      # noqa: E402

SECTIONS = [
    ("词汇默写", ket.build),
    ("打卡评价", build_review),
    ("每日打卡", build_homework),
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
