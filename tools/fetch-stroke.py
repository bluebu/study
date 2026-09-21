#!/usr/bin/env python3
"""补一个字的笔顺数据 → storage/data/chinese/

    python3 tools/fetch-stroke.py 提 纲 生 锈
    python3 tools/fetch-stroke.py --from-spec storage/spec/chinese/writing/07y.txt
    python3 tools/fetch-stroke.py --refresh 提       # 已有也重取（两份数据打架时）

**一个字要两份数据**，缺一样都出不了这张纸，所以一条命令一起取：

    stroke/<字>.json     字形：逐笔 SVG path + 中线  → 画出来的形
    stroke-order.json    笔画码：一个字一串字母，一笔一个 → 这一笔叫什么

取完**当场比一次笔画数**：两边不等就不写盘。差一笔，往后每一笔的名字都会
标错位置，而纸上看不出来（名字都是真笔画名，只是安错了格子）。

写字单（`src/generator/chinese/writing.py`）缺哪样都会报错并让你跑这条命令。

## 为什么数据要进仓库

CI 那边**不该联网拉第三方**：字形是这张纸的内容，拉不到就静默少印一个字，
或者哪天上游改了字形、两次打印的范字不一样。所以一次取下来、提交进去，
以后构建只读本地文件 —— 和「本地能出就等于线上能出」是同一条道理。

体积不用担心：一个字 2~6 KB，一学期几百个字也就一两兆。

## 来源和许可

    hanzi-writer-data（MIT）→ Make Me a Hanzi（LGPL / Arphic Public License）
    → 字形出自 Arphic 文鼎楷体（AR PL UKai）

和 CI 里给田字格装的 `fonts-arphic-ukai` **是同一套字形**，所以这张纸上 SVG 画的
范字和别的单子上字体渲染的范字长得一样，不会一个楷体一个宋体。
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import paths, spec as spec_lib  # noqa: E402

OUT = paths.data("chinese", "stroke")
ORDER = paths.data("chinese", "stroke-order.json")
NAMES = paths.data("chinese", "stroke-names.json")

BASE = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/"
# 笔画码和笔画名。整包 6939 字、143 KB，**只从里面挑用到的字**落盘 ——
# 和 stroke/ 一个规矩：这层 data 跟着 spec 长，不整包搬进仓库
CNCHAR = "https://cdn.jsdelivr.net/npm/cnchar-order@3.2.6/cnchar.order.min.js"

_cn_cache: dict | None = None


def cnchar_tables() -> tuple[dict, dict]:
    """(字 → 笔画码, 码 → 笔画名)。一次进程只下载解析一遍。"""
    global _cn_cache
    if _cn_cache is None:
        with urllib.request.urlopen(CNCHAR, timeout=30) as r:
            js = r.read().decode("utf-8")
        orders, names = {}, {}
        for blob in re.findall(r"JSON\.parse\('(.*?)'\)", js, re.S):
            try:
                d = json.loads(blob.replace("\\'", "'"))
            except json.JSONDecodeError:
                continue
            first = next(iter(d), None)
            if first and isinstance(d[first], dict) and "name" in d[first]:
                names = d
            else:
                orders.update(d)
        if not orders or not names:
            raise RuntimeError("cnchar 的笔画表解析不出来，上游格式大概是变了")
        _cn_cache = (orders, names)
    return _cn_cache


def chars_of_spec(path: Path) -> list[str]:
    """把一份写字单 spec 里出现的汉字按顺序抖出来（去重）。"""
    sp = spec_lib.parse(path)
    out = []
    for b in sp.blocks:
        for word, _ in b.items():
            for c in word:
                if c not in out:
                    out.append(c)
    return out


def fetch(ch: str, *, refresh: bool = False) -> str:
    """取一个字的两份数据。返回 'ok' / 'skip' / 'fail: 原因'。

    **两份都齐、且笔画数对得上**才算成功，否则一个字节都不写盘。
    """
    f = OUT / f"{ch}.json"
    orders, _ = cnchar_tables()
    have_order = ch in json.loads(ORDER.read_text(encoding="utf-8")) if ORDER.is_file() else False
    if f.is_file() and have_order and not refresh:
        return "skip"

    # ── 1. 笔画码（决定每一笔叫什么）──
    codes = orders.get(ch)
    if not codes:
        return "fail: cnchar 没收这个字，出不了笔画名"

    # ── 2. 字形 ──
    if f.is_file() and not refresh:
        raw = f.read_bytes()
    else:
        url = BASE + urllib.parse.quote(ch) + ".json"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            # 404 就是上游没有这个字，不是网络问题 —— 说清楚，别让人以为是断网
            return f"fail: 上游没有这个字（HTTP {e.code})" if e.code == 404 else f"fail: HTTP {e.code}"
        except Exception as e:                       # noqa: BLE001
            return f"fail: {e}"

    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        return f"fail: 返回的不是 JSON（{e}）"

    # 宁可这儿炸，也别让一个空壳文件混进仓库 —— 生成器只检查文件在不在
    if not d.get("strokes") or not d.get("medians"):
        return "fail: 数据里没有 strokes/medians"
    if len(d["strokes"]) != len(d["medians"]):
        return f"fail: strokes {len(d['strokes'])} 条、medians {len(d['medians'])} 条，对不上"

    # ── 3. 两个数据源必须笔画数一致 ──
    # 差一笔，往后每一笔的名字都会标错格子，而纸上看不出来（名字都是真笔画名）。
    # 所以宁可这个字不进仓库，也不留一份会静默印错的数据。
    if len(codes) != len(d["strokes"]):
        return (f"fail: 两源打架 —— 字形 {len(d['strokes'])} 笔、笔画码 {len(codes)} 笔。"
                f"这个字先不收")

    OUT.mkdir(parents=True, exist_ok=True)
    f.write_bytes(raw)
    _merge_order(ch, codes)
    return "ok"


def _merge_order(ch: str, codes: str) -> None:
    """把一个字的笔画码并进 stroke-order.json（排好序，diff 才看得懂）。"""
    cur = json.loads(ORDER.read_text(encoding="utf-8")) if ORDER.is_file() else {}
    cur[ch] = codes
    ORDER.parent.mkdir(parents=True, exist_ok=True)
    ORDER.write_text(
        json.dumps(cur, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")


def _ensure_names() -> None:
    """笔画名表（码 → 名）落一次盘。原样存，判断在 spec。"""
    if NAMES.is_file():
        return
    _, names = cnchar_tables()
    NAMES.parent.mkdir(parents=True, exist_ok=True)
    NAMES.write_text(
        json.dumps(names, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  ✓ 笔画名表 → {NAMES.relative_to(paths.ROOT)}")


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__.strip().split("\n\n")[1])
        return 2

    refresh = "--refresh" in args
    args = [a for a in args if a != "--refresh"]
    if not args:
        print("  --refresh 后面还要给字（或 --from-spec <spec>）")
        return 2

    _ensure_names()

    if args[0] == "--from-spec":
        if len(args) < 2:
            print("  --from-spec 后面要给一份 spec 的路径")
            return 2
        chars = chars_of_spec(Path(args[1]))
        print(f"  {args[1]} 里有 {len(chars)} 个字")
    else:
        chars = [c for a in args for c in a]

    n_ok = n_skip = 0
    fails = []
    for c in chars:
        r = fetch(c, refresh=refresh)
        if r == "ok":
            n_ok += 1
            time.sleep(0.1)                      # 别把 CDN 打急了
        elif r == "skip":
            n_skip += 1
        else:
            fails.append((c, r))
            print(f"    ✗ {c}  {r}")

    print(f"  取到 {n_ok} 个，已有 {n_skip} 个"
          + (f"，失败 {len(fails)} 个" if fails else "")
          + f" → {OUT.relative_to(paths.ROOT)}/")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
