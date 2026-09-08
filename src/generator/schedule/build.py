"""课程表 —— 把各栏目串起来。

    week/         一周课表：一张 A4 横版，贴桌前，装书包照着带书
    afterschool/  放学检查：作业抄没抄下来，三科逐项过一遍

一个栏目一个模块，各管各的产物目录，这里只按顺序调。
**每个栏目单独 try** —— 一个栏目的 spec 写错，不该把另一个也带下水。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from afterschool import build_afterschool  # noqa: E402
from week import build_week                # noqa: E402

SECTIONS = [
    ("一周课表", build_week),
    ("放学检查", build_afterschool),
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
