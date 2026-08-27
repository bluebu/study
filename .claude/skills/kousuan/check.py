#!/usr/bin/env python3
"""口算卷逐题判对错 —— 会话不许心算，统计数字一律以这里的输出为准。

抄题的时候把「题=孩子写的」一行一条丢进来（一行一题，# 是注释）：

    140÷70=20
    256÷8=32
    7.6+2.4=10.0
    1-0.03=0.07

    python3 check.py 抄的.txt          # 逐题对错 + 统计
    python3 check.py 抄的.txt --wrong  # 只列错题，直接抄进 spec 的 [错题] 区

判定三档：

    ✓  对
    ~  值对、写法不规范（10.0 该写 10）—— 不算错，但值得提一句
    ✗  错，右边给出正确答案和「多/少一个 0」这类线索

只支持两个数一个运算符（口算卷就是这个形状），多运算符会明确报错，
不静默算错。用 Decimal 不用 float：1-0.03 必须等于 0.97。
"""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation

OPS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b,
       "×": lambda a, b: a * b, "÷": lambda a, b: a / b}
NORM = str.maketrans({"*": "×", "/": "÷", "−": "-", "＋": "+", "－": "-",
                      "＝": "=", "，": ",", "。": ".", "：": ":"})
NUM = re.compile(r"^\d+(\.\d+)?$")


def fmt(d: Decimal) -> str:
    """去掉多余的 0，又不让 Decimal 甩出 4E+1 这种科学计数。"""
    return format(d.normalize(), "f")


def _dec(s: str) -> Decimal | None:
    s = s.strip()
    if not NUM.match(s):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def solve(expr: str) -> Decimal:
    """算一道题。只认「数 运算符 数」，别的形状直接报错。"""
    for op, fn in OPS.items():
        if op in expr:
            left, _, right = expr.partition(op)
            a, b = _dec(left), _dec(right)
            if a is None or b is None:
                raise ValueError(f"「{expr}」两边不是数")
            if op == "÷" and b == 0:
                raise ValueError(f"「{expr}」除以 0")
            got = fn(a, b)
            return got.normalize() if op == "÷" else got
    raise ValueError(f"「{expr}」里没找到运算符")


def hint(written: Decimal, right: Decimal) -> str:
    """给一句错因线索。这类卷子九成错在 0 的个数，先认这个。"""
    w, r = written.normalize(), right.normalize()
    if w == r * 10:
        return "多写一个 0"
    if w * 10 == r:
        return "少写一个 0"
    if w == r * 100:
        return "多写两个 0"
    if w * 100 == r:
        return "少写两个 0"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", help="一行一题的「题=写的」文件")
    ap.add_argument("--wrong", action="store_true", help="只列错题")
    args = ap.parse_args()

    ok = loose = bad = 0
    lines = []
    for raw in open(args.file, encoding="utf-8"):
        line = raw.strip().translate(NORM)
        if not line or line.startswith("#"):
            continue
        expr, sep, written = line.partition("=")
        if not sep:
            print(f"✗ 这行没有等号，写成「题=孩子写的」：{raw.strip()!r}", file=sys.stderr)
            return 1

        expr, written = expr.strip(), written.strip()
        try:
            right = solve(expr)
        except ValueError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 1

        got = _dec(written)
        if got is None:
            mark, tail, bad = "✗", f"→ {fmt(right)}（没抄到答案）", bad + 1
        elif got == right:
            # 值对，但 10.0 / 4.0 这种末尾 0 在小数计算里该化掉
            if written != fmt(right) and "." in written:
                mark, tail, loose = "~", f"值对，写法该是 {fmt(right)}", loose + 1
            else:
                mark, tail, ok = "✓", "", ok + 1
        else:
            why = hint(got, right)
            mark, tail, bad = "✗", f"→ {fmt(right)}" + (f"（{why}）" if why else ""), bad + 1

        if mark != "✗" and args.wrong:
            continue
        lines.append(f"{mark} {expr} = {written:<8} {tail}".rstrip())

    print("\n".join(lines))
    total = ok + loose + bad
    if total:
        print(f"\n{total} 题　对 {ok + loose}　错 {bad}　正确率 "
              f"{round((ok + loose) / total * 100)}%"
              + (f"　（其中 {loose} 题值对写法不规范）" if loose else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
