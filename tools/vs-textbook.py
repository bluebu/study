#!/usr/bin/env python3
"""拿教材 PDF 核一遍语文的 spec —— 版本对不上就会印错内容给孩子。

    python3 tools/vs-textbook.py ~/workspace/personal/教材/义务教育教科书_语文_四年级上册_人教版.pdf

**为什么有这个脚本**：这批抽查单最早是照 2019 版编的 —— 第 6 课写成
《呼风唤雨的世纪》（2024 版是《方帽子店》）、听写块的字全是旧写字表、
语文园地三的日积月累印着《别董大》（2024 版在园地八）。光看 spec 看不出来，
得拿书对。对过一遍就该固化成脚本，而不是下次再人肉对一遍。

三件事，只报不改 —— **改哪个字是判断，不是脚本的事**：

1. 抽查单「读准」「词语」块里的每个词，必须在它那几页课文里出现
   （spec 文件头的 `pages:` 是课文书页，如 `pages: 23-27`）
2. 教材总览的 `write=` 逐课相加，必须等于书末写字表标的「共 N 个字」
3. 书页 → PDF 页的偏移自己探（找「写 字 表」那页），不写死

⚠️ pdftotext 把行上方的注音混进正文里（「一溜liū烟」），所以比对前
   **必须先去掉所有拉丁字母**，否则「一溜烟」这种词一律报找不到 —— 假警报
   比不报更费时间。

教材 PDF 是版权内容，**不进仓库**（本机 ~/workspace/personal/教材/ 下）。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib import paths, spec as spec_lib  # noqa: E402

ITEM_KEYS = ("note:", "ask:", "lines:", "answer:")   # 区块内的 key 行，不是词
# 要核的区块：这两个区块的项是「课文里的词」，其余区块是问答，不适合机械比对
CHECK_BLOCKS = ("读准", "词语")


def pdf_pages(pdf: Path) -> list[str]:
    """PDF → 一页一段文本（去掉拉丁字母：注音混在正文里）。"""
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"✗ pdftotext 跑不动：{r.stderr.strip()[:200]}")
    return r.stdout.split("\f")


def find_offset(pages: list[str]) -> int:
    """书页 → PDF 页的偏移。靠「写 字 表」那页自己认，不写死。"""
    for i, p in enumerate(pages, 1):
        if "写 字 表" in p or "写字表" in p.replace(" ", ""):
            m = re.search(r"^\s*(\d{2,3})\s*$", p, re.M)
            if m:
                return i - int(m.group(1))
    sys.exit("✗ 认不出「写字表」那一页，没法算书页偏移")


def plain(pages: list[str], offset: int, a: int, b: int) -> str:
    """书页 a~b 的正文：去掉空白和拉丁字母（注音）才是能比对的原文。"""
    raw = "".join(pages[p + offset - 1] for p in range(a, b + 1)
                  if 0 < p + offset - 1 < len(pages))
    return re.sub(r"[A-Za-z\s]+", "", raw)


def loose(word: str, text: str) -> bool:
    """宽松匹配：旁批和正文在 pdftotext 里是交错的，词会被插断 ——
    《方帽子店》的「一溜烟」中间就插了一整条旁批（「一子”？溜烟似的跑了」）。
    每个字之间允许插一小段，能按顺序连起来就当「疑似被旁批打断」，不算硬错。
    """
    return re.search(".{0,24}?".join(map(re.escape, word)), text) is not None


def check_sheets(pages: list[str], offset: int) -> int:
    """抽查单：读准 / 词语两个区块里的词，必须在它那几页课文里。"""
    bad = 0
    for path in spec_lib.specs(paths.spec("chinese", "check")):
        sp = spec_lib.parse(path)
        rng = sp.get("pages")
        if not rng:
            print(f"  ? {path.name}：文件头没写 pages:，跳过")
            continue
        a, _, b = rng.partition("-")
        text = plain(pages, offset, int(a), int(b or a))

        miss, cut = [], []
        for block in sp.blocks:
            if block.name not in CHECK_BLOCKS:
                continue
            for line in block.lines:
                if line.strip().startswith(ITEM_KEYS):
                    continue
                for chunk in re.split(f"[{re.escape(spec_lib.ITEM_SEPS)}]", line):
                    word = chunk.split("=")[0].strip()
                    if not word or word in text:
                        continue
                    (cut if loose(word, text) else miss).append(
                        f"{block.name}「{word}」")
        if miss:
            bad += 1
            print(f"  ✗ {path.name}（书页 {rng}）课文里找不到：{'、'.join(miss)}")
        elif cut:
            print(f"  ? {path.name}（书页 {rng}）疑似被旁批打断，看一眼："
                  f"{'、'.join(cut)}")
        else:
            print(f"  ✓ {path.name}")
    return bad


def check_overview(pages: list[str], offset: int) -> int:
    """教材总览：write= 逐课相加 == 书末写字表标的总数。"""
    table = plain(pages, offset, 125, 126)
    m = re.search(r"共(\d+)个字", table)
    if not m:
        print("  ? 写字表那页读不出「共 N 个字」，跳过校验和")
        return 0
    want = int(m.group(1))

    bad = 0
    for path in spec_lib.specs(paths.spec("chinese", "overview")):
        sp = spec_lib.parse(path)
        got = sum(int(b.attr("write")) for b in sp.blocks
                  if (b.attr("write") or "").isdigit())
        ok = got == want
        bad += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {path.name}：write= 相加 {got} 字"
              f"　书末写字表 {want} 字{'' if ok else '  ← 对不上'}")
    return bad


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    pdf = Path(sys.argv[1]).expanduser()
    if not pdf.exists():
        sys.exit(f"✗ 找不到教材 PDF：{pdf}")

    pages = pdf_pages(pdf)
    offset = find_offset(pages)
    print(f"\n教材 {pdf.name}：{len(pages)} 页，书页 + {offset} = PDF 页\n")

    print("抽查单（读准 / 词语两个区块的词是不是课文里的）")
    bad = check_sheets(pages, offset)
    print("\n教材总览（写字数的校验和）")
    bad += check_overview(pages, offset)

    print(f"\n{'全部对上 ✓' if not bad else f'✗ {bad} 处对不上 —— 改哪个字是判断，脚本只报'}\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
