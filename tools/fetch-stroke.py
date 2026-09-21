#!/usr/bin/env python3
"""补一个字的笔顺数据 → storage/data/chinese/stroke/<字>.json

    python3 tools/fetch-stroke.py 提 纲 生 锈
    python3 tools/fetch-stroke.py --from-spec storage/spec/chinese/writing/07y.txt

写字单（`src/generator/chinese/writing.py`）缺哪个字就会报错并让你跑这条命令。

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
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import paths, spec as spec_lib  # noqa: E402

OUT = paths.data("chinese", "stroke")
BASE = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/"


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


def fetch(ch: str) -> str:
    """取一个字。返回 'ok' / 'skip' / 'fail: 原因'。"""
    f = OUT / f"{ch}.json"
    if f.is_file():
        return "skip"

    url = BASE + urllib.parse.quote(ch) + ".json"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        # 404 就是上游没有这个字，不是网络问题 —— 说清楚，别让人以为是断网
        return f"fail: 上游没有这个字（HTTP {e.code}）" if e.code == 404 else f"fail: HTTP {e.code}"
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

    OUT.mkdir(parents=True, exist_ok=True)
    f.write_bytes(raw)
    return "ok"


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__.strip().split("\n\n")[1])
        return 2

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
        r = fetch(c)
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
