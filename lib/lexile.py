"""课文蓝思值（Lexile）的**估算** —— 一段英文 → 约多少 L。

**这不是官方值。** 蓝思是 MetaMetrics 的专有算法：结构公开，常数和词频库不公开。
这里照公开的结构算，常数拿几本公版书的官方值标出来。要官方值只能把原文贴进
hub.lexile.com 的分析器（免费，要注册）。

── 结构（Stenner《Measuring Reading Comprehension with the Lexile Framework》式 2、式 5）

    logit = 9.82247 × LMSL − 2.14634 × MLWF − C
    L     = (logit + 3.3) × 180 + 200

    LMSL = log10(平均句长)            句长按词数
    MLWF = mean(log10(词频))          词频 = 每 5,088,721 词里出现几次
                                        （原版用 Carroll 1971 那份 508 万词的学校语料）

论文只给了两个系数和换算式，**C 没公开，对数底也没写**。两件事都是标出来的：

    · 底取 10。取自然对数时 LMSL 的系数太大，句长从 9 到 22 就差出 1600L，
      四本书的残差上千 —— 明显不对
    · 分号、冒号也断句。19 世纪的书一句话用分号串三四个分句（黑骏马平均 22 词一句），
      不断的话黑骏马被估高 170L
    · C = 2.499，四本公版书（Project Gutenberg 全文）残差的均值：

          书                      官方值    估出来    来源
          The Wonderful Wizard of Oz   1000L    1051L   ReadingVine
          The Secret Garden             970L     919L   LightSail
          Black Beauty                 1020L    1032L   LightSail
          The Tale of Peter Rabbit      660L     649L   TeachingBooks

      **整本书上 ±50L。** 一段一两百词的课文误差会更大（MetaMetrics 自己说
      少于 125 词不给值）—— 页面上一律写「约」，看趋势、别看个位

── 词频表 `lib/lexile-freq.tsv`

Carroll 那份语料拿不到，用开源的 wordfreq 3.1.1（多语料混合）顶替：
`word_frequency(w, 'en') × 5,088,721` 取 log10，只存出现 ≥2 次的那 4.7 万词。
表外的词（人名 Glinda、生僻词）按出现 1 次算，log10 = 0 —— 名字多的段落因此估得偏难，
这和孩子的实际感受是一致的。**CI 不装 wordfreq**，表是生成好提交进来的；
要换词频源就重新生成这张表、重标 C，别在代码里另接一套。
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

FREQ = Path(__file__).with_name("lexile-freq.tsv")
C = 2.499

_WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_SENT = re.compile(r"[.!?;:]+[\"”’)]*\s")


@lru_cache(maxsize=1)
def _table() -> dict[str, float]:
    out = {}
    for line in FREQ.read_text(encoding="utf-8").splitlines():
        w, _, v = line.partition("\t")
        out[w] = float(v)
    return out


def estimate(text: str) -> int | None:
    """一段英文的估算 L 值，取整到 10。没有词就返回 None。"""
    t = re.sub(r"\n\s*\n", " . ", text.replace("\r", ""))   # 空行分段 = 句子边界
    t = re.sub(r"\s+", " ", t) + " "
    words = _WORD.findall(t)
    sents = [s for s in _SENT.split(t) if re.search(r"[A-Za-z]", s)]
    if not words or not sents:
        return None
    freq = _table()
    mlwf = sum(freq.get(w.lower().replace("’", "'"), 0.0) for w in words) / len(words)
    logit = 9.82247 * math.log10(len(words) / len(sents)) - 2.14634 * mlwf - C
    return round(((logit + 3.3) * 180 + 200) / 10) * 10
