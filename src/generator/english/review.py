"""打卡评价 —— 每天的朗读作业，一份能和下次比的成绩单。

    storage/data/english/review/<slug>.read.json
                              喂数据台（../feeder）产出：声学 + 转写 + 逐字对齐
    storage/data/english/review/<slug>.json
                              同上，停顿声学单独一份（和老站 data/ 字段逐个对齐）
    storage/data/english/review/<slug>.ref.txt
                              红线划中的课文原文 —— 比对基准
    storage/spec/english/review/<slug>.txt
                              人的判断：哪几处算读错、四维分数、点评
    storage/result/english/review.csv
                              算出来的指标，每次构建全量重算覆盖（趋势页读它）

`<slug>` 是「书 / 课 / 第几页」，**斜杠就是目录**：`super8/L3/p68` 落成
`storage/data/english/review/super8/L3/p68.ref.txt`。一次录音读了几页就写区间
（`p68-69`）—— 颗粒度是**一次录音**，不是一页。
喂数据台一次扫一叠截图时就是这么落的（页码它自己认页角那枚绿圆盘）。

spec 里**没有任何字段指向数据文件** —— 全靠这个名字拼路径，spec 叫什么，
data 就得叫什么。要不要 push 哪些文件见根目录 DATA.md。

产物落在 dist/english/review/：**一天一份报告** + 一个目录页 + 一张趋势页。

    <YYYY-MM-DD>.html   当天的成绩单：页眉是日期 + 当天汇总，
                        当天每次录音是页内的一节（锚点 `#<slug 里的斜杠换成->`）
    index.html          按日期倒序，每天一条汇总 + 当天每次录音一行
    trend.html          全部放在一条线上（从 result/english/review.csv 读回来）

并进日页之前是「一次录音一个页面」。改掉是因为平时看的就是「今天整体怎么样」——
为一次 90 秒的朗读单开一个 URL，每天要点开三次才看得全。

**数字一个都不从 spec 抄**：准确率、WCPM、几个词一停、停顿占比全部由这里算，
spec 只写 words（核对过的原文词数）和 errors（认定的计错数）。老站那 7 份报告是
手写 HTML，同一个数字在标题、四个数字、三把尺子、「分数是怎么来的」里各写一遍，
改一处就得改四处。

口径见 ../english/review/README.md，动之前先读那份：
  · 准确率 =（原文词数 − 计错数）÷ 原文词数。替换、漏读、读错音计错；
    插入词和回读只算不流利、不计错
  · WCPM = 读对词数 ÷ 总时长 × 60
  · 分档 Fountas & Pinnell BAS 1 p.40，常模 Hasbrouck & Tindal 2017 Table 4
  · **不计进统计的段落**（念生词表、读划线外的段落）写进 spec 的 `[跳过]`，
    duration / pause_count / pause_ratio 三个都扣掉它再算
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import figures  # noqa: E402

SPECS = paths.spec("english", "review")
DATA = paths.data("english", "review")
RESULT = paths.result("english", "review.csv")
ERRORS_RESULT = paths.result("english", "review-errors.csv")

# 内容分类 → 色板变量名。顺序就是目录页的分组顺序。
# 和老站 CAT_ORDER / CAT_COLOR 一致，但那边在两个脚本里各存了一份、
# README 还得写「要改一起改」—— 这里只有这一处。
CATS = {
    "单词": "word",
    "超8": "read",
    "G3": "listen",
    "语法": "gram",
}
CAT_FALLBACK = "drill"          # 没列到的新分类先用紫

# 四个维度的满分。总分 100 = 30 + 30 + 25 + 15
DIMENSIONS = [("准确度", 30), ("流利度", 30), ("断句语调", 25), ("发音", 15)]

# 错误的八类 + 每类对应的练法。**分类是给「怎么练」用的，不是给归档用的** ——
# 每一类都要能落到一句具体的练习话上，落不到的就不该单独成一类。
# 这八类是从头 159 处错的定性文字里归纳出来的，不是先拍脑袋定表再往里塞。
ERROR_KINDS: dict[str, str] = {
    "元音":  "把这几个词摆成最小对立对，挨着念听中间那个音",
    "辅音":  "对着镜子看口型，th / v / w 各念十遍",
    "词尾":  "每句最后一个词多含半拍再往下读",
    "小词":  "a / the / to 这类词慢下来看清再读",
    "词形":  "开读之前先用眼睛把整句扫一遍",
    "生词":  "开读之前先把长词拆成音节念两遍",
    "专名":  "人名地名单独拎出来念熟，再放回句子里",
    "漏读":  "手指指着词读，读到哪儿指到哪儿",
}


# ══════════════════════════════════════════════════════════════
# 读一份 spec + 它的数据
# ══════════════════════════════════════════════════════════════

class Report:
    """一份报告的全部内容：spec 里的判断 + data 里的测量 + 算出来的数字。"""

    def __init__(self, sp: spec_lib.Spec):
        self.spec = sp
        # 名字可以带目录（specs/super8/L3/p68.txt → super8/L3/p68）
        try:
            self.slug = sp.path.resolve().relative_to(SPECS.resolve()).with_suffix("").as_posix()
        except ValueError:
            self.slug = sp.path.stem
        self.blocks = {b.name: b for b in sp.blocks}

        acoustics = DATA / f"{self.slug}.json"
        if not acoustics.exists():
            spec_lib.die(f"{self.slug}：缺 data/{self.slug}.json —— "
                         f"先用喂数据台跑一遍录音（feeder read）")
        self.acoustics = json.loads(acoustics.read_text(encoding="utf-8"))

        reading = DATA / f"{self.slug}.read.json"
        self.reading = json.loads(reading.read_text(encoding="utf-8")) if reading.exists() else None

        # ── 人给的两个数
        self.words = sp.int_("words", 0)
        self.errors = sp.int_("errors", 0)
        if not self.words:
            spec_lib.die(f"{self.slug}：要写 words（核对过的原文词数）")

        # ── [跳过]：录音里不属于这次朗读的那几段（念生词表、读划线外的段落）
        #
        # 这几段**时长里有、词数里没有**，留着就是把分母撑大 —— 9/1 那次录音
        # 前 90 秒念的是生词表，报告头上的 WCPM 因此印成 35，只算课文那段是 57。
        # 从前是在每份 spec 的 [怎么来的] 里人工补一句「只算课文那一段是 XX」，
        # 一份一算、口径散在散文里，趋势页和 csv 拿到的还是被撑大的那个数。
        # 现在统一在这儿扣掉：**duration / pause_count / pause_ratio 三个都按扣完的算**，
        # WCPM 和「几个词一停」跟着就对了。
        #
        # 为什么是人写在 spec 里、不是机器自动认：feeder 的 draft 会把候选打出来
        # （「读了原文以外的 113.2 秒」），但边界机器切不干净 —— 对齐会把生词表
        # 末几个词拉去顶课文结尾的词（p70-72 的 only/in、p12-15 的 problems），
        # 照 refTimes 首尾切会把整段生词表算进课文。所以机器给候选、人定边界。
        self.skips: list[tuple[float, float, str]] = []
        if "跳过" in self.blocks:
            for span, label in spec_lib.Block(
                    name="", lines=[self.blocks["跳过"].head]).items():
                a, _, b = span.partition("-")
                self.skips.append((float(a), float(b), label or "不计"))

        # ── 其余全部算出来
        self.raw_duration = float(self.acoustics["duration"])   # 录音本身多长（图上画的是它）
        _pauses = self.acoustics.get("pauses") or []
        if self.skips and _pauses:
            _kept = [q for q in _pauses
                     if not any(a <= q["start"] < b for a, b, _ in self.skips)]
            self.duration = round(self.raw_duration
                                  - sum(b - a for a, b, _ in self.skips), 2)
            self.pause_count = len(_kept)
            self.pause_ratio = (round(sum(q["dur"] for q in _kept) / self.duration, 3)
                                if self.duration else 0.0)
        else:
            self.duration = self.raw_duration
            self.pause_count = int(self.acoustics["pause_count"])
            self.pause_ratio = float(self.acoustics["pause_ratio"])
        self.correct = self.words - self.errors
        self.accuracy = round(self.correct / self.words * 100, 1)
        self.wcpm = round(self.correct / self.duration * 60) if self.duration else 0
        # 几个词一停：全段词数 ÷ 停顿次数。老站三份报告都是这么算的
        self.per_group = round(self.words / self.pause_count, 1) if self.pause_count else 0

        # ── [比对] 每条计错条目开头的类型标签：[元音] / [词尾] / [专名×2] / [－]
        #
        # 用〔〕不用 []：`lib/spec.py` 的区块头正则是 `\s*\[([^\]]+)\]`，**允许前导空白**，
        # 缩进行写成 `    [元音] …` 会被当成一个新区块、整个 [比对] 从那儿断掉
        # （踩过：p65 的 lines 只剩 2 行）。标签**不印进正文** —— 它是字段不是话。
        # 八类是从头 159 条定性文字里归纳出来的，每一类对应一个明确的练法
        # （元音→最小对立对、词尾→句尾多含半拍、词形→开读前扫一遍……）。
        # 分类只有人做得了：「hut 读成 heart」是元音、「visit 读成 wait」是看岔词形，
        # 机器的 category 分不出这一层（它只到「实词/小词/词尾」）。
        # `[－]` = 这条列出来但不计错（读多了自己退回去重来那种）。
        self.errors_by_kind: dict[str, int] = {}
        self.error_words: list[tuple[str, str]] = []      # (原文词, 类型)
        if "比对" in self.blocks:
            ref_word = None
            for line in self.blocks["比对"].lines:
                if line.startswith("原文 "):
                    m = re.search(r"\*(.+?)\*", line)
                    ref_word = m.group(1) if m else None
                elif line.startswith(("实读 ", "识别成 ")):
                    pass
                elif line.startswith("    "):
                    for tag in re.findall(r"〔([^〔〕]+?)〕", line.strip()[:40]):
                        if tag == "－":
                            continue
                        name, _, mult = tag.partition("×")
                        if name not in ERROR_KINDS:
                            continue
                        n = int(mult) if mult.isdigit() else 1
                        self.errors_by_kind[name] = self.errors_by_kind.get(name, 0) + n
                        for _ in range(n):
                            self.error_words.append(((ref_word or "?").strip("\"'“”.,!?;:"), name))
                    ref_word = None
            # 剥掉标签，报告正文只出「hut 读成 heart」，不出「〔元音〕」
            self.blocks["比对"].lines = [
                re.sub(r"^(\s+)(?:〔[^〔〕]+〕)+\s*", r"\1", ln)
                for ln in self.blocks["比对"].lines]

        self.score = sp.int_("score", 0)
        self.naep = sp.int_("naep", 2)
        self.cat = sp.get("cat", "超8")
        self.date = sp.get("date", "")
        self.order = sp.int_("order", 0)
        # prev 写全名（super8/L3/p67）或只写页（p67，当成同一课里的上一页）
        folder = self.slug.rsplit("/", 1)[0] + "/" if "/" in self.slug else ""
        self.prevs = [s if "/" in s or not folder else folder + s
                      for s in (x.strip() for x in (sp.get("prev") or "").split(",")) if s]

        self._check()

    def _check(self) -> None:
        """spec 自身的一致性。**以前一条都没有，全靠人肉加一遍。**

        这三条各自都踩过：四维之和和 score 对不上（分数条和大数字互相打架）、
        `[比对]` 里标了不计错却写成「实读」（编号顺延，多出来的编号看着像还有一处错）、
        `[卡壳]` 的标签里混进中文逗号（`could not convert string to float`，
        报错里看不出是哪一条）。都是**静默**或**看不出位置**的错，所以在这儿拦住。
        """
        name = self.spec.path.name

        # ① 四维之和 == score
        got = dict(parse_pairs(self.blocks["评分"].head)) if "评分" in self.blocks else {}
        if got:
            total = 0
            for dim, full in DIMENSIONS:
                raw = got.get(dim)
                if raw is None:
                    spec_lib.die(f"{name}: [评分] 少了「{dim}」—— 维度名写错会静默丢掉那一条，"
                                 f"四个都要有：" + " ".join(f"{d}=?/{f}" for d, f in DIMENSIONS))
                total += int(str(raw).split("/")[0])
            if total != self.score:
                spec_lib.die(f"{name}: [评分] 四维之和是 {total}，score 写的是 {self.score} —— "
                             f"对不上。报告上大数字印 score、分数条印四维，两处会互相打架")

        # ② 类型标签之和 == errors
        # [比对] 的**条数**不等于 errors 是正常的（见下面那段），但**标签数**必须相等：
        # 一条含两处错就写 [专名×2]，不计错的写 [－]。对不上就是漏标或标重了 ——
        # 趋势页的分类统计和 Top3 全靠这些标签，漏一个就少算一处。
        tagged = sum(self.errors_by_kind.values())
        if "比对" in self.blocks and tagged != self.errors:
            spec_lib.die(
                f"{name}: [比对] 的类型标签加起来 {tagged} 处，errors 写的是 {self.errors} —— "
                f"对不上。每条计错的说明行开头要有〔类型〕（八类：{'/'.join(ERROR_KINDS)}），"
                f"一条含两处写〔类型×2〕，列出来但不计错的写〔－〕。"
                f"**用〔〕不用 []** —— 方括号会被当成新区块，整个 [比对] 从那儿断掉")

        # 想过再加一条「[比对] 的条数 == errors」，**撤了**：这两个数本来就不相等，
        # 口径允许两个方向都差（一条含两处错 → errors 多；回读或课本印错写「实读」
        # 但不计错 → errors 少）。实测 7 份 spec 里 5 份都会响 —— 在多数情况下都响的
        # 检查没有信号，只是噪音。报告里编号是顺着「实读」排的，编号最大值不等于
        # errors 属正常，这条写进了 skill 的自检清单。

        # ③ [卡壳] / [句末] 抬头行的每一段，起止都要能转成浮点
        for blk, how in (("卡壳", "起-止 = 标签"), ("跳过", "起-止 = 标签"), ("句末", "时刻")):
            if blk not in self.blocks:
                continue
            for item, label in spec_lib.Block(name="", lines=[self.blocks[blk].head]).items():
                bad = [x for x in (item.split("-") if blk in ("卡壳", "跳过") else [item])
                       if not _is_number(x)]
                if bad:
                    spec_lib.die(
                        f"{name}: [{blk}] 这一条读不成数字：{item!r}"
                        + (f"（标签「{label}」）" if label else "")
                        + f" —— 格式是「{how}」，而且**标签里不能有 , ， 、**："
                        + "那三个都是条目分隔符，后半截会被当成新的一条")

    # ── 供目录页和当日小结用的元信息
    @property
    def title(self) -> str:
        page_no = self.spec.get("page")
        return f"{self.spec.title} · 第 {page_no} 页" if page_no else self.spec.title

    @property
    def sub(self) -> str:
        book = self.spec.get("book", "")
        return f"{book} · {self.words} words" if book else f"{self.words} words"

    @property
    def page_count(self) -> int:
        """这次录音读了几页。没有 [分页] 就是一页。

        颗粒度是**一次录音**，页只是标注 —— 所以这个数只用来在当天的汇总里
        报「今天读了几页」，不影响任何指标的算法。
        """
        b = self.blocks.get("分页")
        n = len([ln for ln in b.lines if ln.strip() and not ln[:1].isspace()]) if b else 0
        return n or 1

    @property
    def color_var(self) -> str:
        return CATS.get(self.cat, CAT_FALLBACK)


# ══════════════════════════════════════════════════════════════
# 行内标记
# ══════════════════════════════════════════════════════════════

def rich(text: str) -> str:
    """spec 里的行内标记 → HTML。转义在前，标记在后，顺序不能反。

        **粗**      → <b>
        *词*        → <ins>（实读那侧）或 <mark>（原文那侧，见 diff_line）
        /           → 意群斜线（只在「斜线版」里）
    """
    out = html.escape(text)
    # 破折号两侧留空格 —— 全站中文一个写法（「基本持平 —— 8 月 30 日起」）。
    # 收在这一处：spec 里一行内手写的「改口——说明」，和续行拼接时空格丢在
    # 换行处的「基本持平—— 8 月」，都归这条管，不必两边各写一套规则
    out = re.sub(r"\s*(—+)\s*", r" \1 ", out).strip()
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out


# rich() 先 escape 再插标签，所以到 marked() 手上的高亮词已经是实体形式了
# （`Heidi's` → `Heidi&#x27;s`）。判断「这是不是一个能念的英文词」得先还原回去。
_ENTITIES = {"&#x27;": "'", "&amp;": "&", "&quot;": '"', "&lt;": "<", "&gt;": ">"}
_SAYABLE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _plain(s: str) -> str:
    for k, v in _ENTITIES.items():
        s = s.replace(k, v)
    return s


def picked(text: str) -> str:
    """取出 `*xxx*` 里高亮的那个词（没有就空串）。作用在**原始 spec 文本**上。"""
    m = re.search(r"\*(.+?)\*", text)
    return m.group(1) if m else ""


def marked(text: str, tag: str, *, say: bool = False,
           clip: tuple[float, float] | None = None,
           std: tuple[float, float] | None = None) -> str:
    """把 *xxx* 换成 <mark>/<ins>。

    `say=True` 时，高亮的那个词只要是个能念的英文词，就带上 `data-say` ——
    点一下让浏览器念出来（`review-play.js`）。**看字是听不出元音差别的**：
    seat / set、niece / nice 写在纸上一目了然，差在哪儿只有耳朵知道。

    再给一段 `clip` 起止秒数，点的时候优先播**她自己**读的那一段（红词）；
    `std` 是同一处在**官方朗读**里的起止（绿词），点了听录音棚里念的那一句。
    本地没有对应的音频就退回去念这个词 —— 线上两种音频都没有
    （录音和版权音频都不进仓库），所以线上点词听到的是合成音，一样能分元音。

    中文占位（`（没读出来）`）匹配不上 `_SAYABLE`，自然就不带属性 —— 优雅降级，
    不需要在调用处特判。
    """
    def one(m: re.Match[str]) -> str:
        w = m.group(1)
        attrs = ""
        if say and _SAYABLE.fullmatch(_plain(w)):
            attrs = f' class="say" data-say="{w}"'
            if clip:
                attrs += f' data-clip="{clip[0]:.2f},{clip[1]:.2f}"'
            if std:
                attrs += f' data-std="{std[0]:.2f},{std[1]:.2f}"'
        return f"<{tag}{attrs}>{w}</{tag}>"

    return re.sub(r"\*(.+?)\*", one, rich(text))


def grouped(lines: list[str]) -> list[str]:
    """按缩进把行分成段：缩进最浅的开一段，更深的接到上一段末尾。

    一句话写不下要换行，续行就多缩进一层：

        [尺子]
            96.4% 落在「要带一带」这一档的中间——
                不过比上一页往右挪了一点。          ← 接上一句，不是新的一句
            74 个正确词/分钟……                     ← 新的一句

    没有这一层，三把尺子的三句话会按行数错位一格 ——
    WCPM 那张图底下印出准确率的话，看不出是 bug，只觉得读着别扭。
    """
    out: list[str] = []
    base: int | None = None
    for ln in lines:
        if not ln.strip():
            continue
        indent = len(ln) - len(ln.rstrip("\n").lstrip())
        if base is None or indent <= base:
            base = indent if base is None else min(base, indent)
            out.append(ln.strip())
        elif out:
            out[-1] = _join(out[-1], ln.strip())
        else:
            out.append(ln.strip())
    return out


def joined(lines: list[str]) -> str:
    """把几行说明拼成一段。和 grouped 用同一套拼接规则。"""
    out = ""
    for ln in lines:
        out = _join(out, ln.strip()) if out else ln.strip()
    return out


def _join(a: str, b: str) -> str:
    """接上一行。中文之间不塞空格，英文之间塞。

    换行本来只是排版，不该在正文里留下痕迹 —— 中文续行硬加一个空格，
    印出来就是「高半级； 不过比上一页」，多一个空隙。
    """
    if not a or not b:
        return a + b
    # 破折号两侧的空格不在这儿管 —— 换行处和一行内手写的要一个口径，收在 rich()
    return a + " " + b if a[-1].isascii() and b[0].isascii() else a + b


# ══════════════════════════════════════════════════════════════
# 各区块
# ══════════════════════════════════════════════════════════════

# 成对的标点自己就占半个字的空，间隔号贴着它写才不显得散开。
# 收尾的（右半）在左边不留空格，起头的（左半）在右边不留空格。
_TAIL_TIGHT = "》」』”"
_HEAD_TIGHT = "《「『“"


def dot_join(pieces) -> str:
    """用「·」把几段拼成一行，**书名号 / 引号那一侧不留空格**。

        超8 · Lesson 3 ·《Prince Darling》· 2 次朗读

    而不是 `Lesson 3 · 《Prince Darling》 · 2 次朗读` —— 左右书名号本身
    已经各占半个字，再加空格就散了。页眉和每节的副标题都要这条规则，收在一处。
    """
    out = ""
    for piece in pieces:
        if not piece:
            continue
        if out:
            left = "" if out[-1] in _TAIL_TIGHT else " "
            right = "" if piece[0] in _HEAD_TIGHT else " "
            out += f"{left}·{right}"
        out += piece
    return out


def hero(r: Report, *, lesson: bool = False, book: bool = False) -> dict:
    """日页里**一节**的标题。

    页面的 h1 已经是日期、页眉已经写了卷名和书名，所以这儿一概不重复 ——
    节标题就是「第 69 页」。只有当天跨了课（`lesson`）或跨了本（`book`）时，
    才把那一样补回到副标题里，否则每节都在重复同一行字。

    并进日页之前这儿是整页的 h1，带着卷名 + 页码 + 书名 + 日期一长串。
    """
    head = f'第 {r.spec.get("page")} 页' if r.spec.get("page") else r.spec.title
    # 页码里的数字描成这一节的主色（「第 69 页」的 69）
    title = re.sub(r"(\d+)(?!.*\d)", r"<b>\1</b>", html.escape(head), count=1)

    pieces = []
    if lesson:
        pieces.append(r.spec.title)
    if book and r.spec.get("book"):
        pieces.append(f'《{r.spec.get("book")}》')
    # 「划线三段 110 词」是一节，不要在中间再断开
    pieces.append(" ".join(x for x in (r.spec.get("part"), f"{r.words} 词") if x))

    return {"title": title, "sub": dot_join(pieces)}


def pretty_date(iso: str) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日" if m else (iso or "")


def score_box(r: Report, others: dict[str, Report], *, first: bool = True) -> dict:
    b = r.blocks.get("总评")
    lead = b.head if b else ""
    tip = joined(b.notes()) if b else ""

    bars = []
    got = dict(parse_pairs(r.blocks["评分"].head)) if "评分" in r.blocks else {}
    for name, full in DIMENSIONS:
        raw = got.get(name)
        if not raw:
            continue
        n = int(raw.split("/")[0])
        bars.append({"name": name, "pct": round(n / full * 100), "val": f"{n}/{full}"})

    return {"num": r.score, "lead": lead, "tip": rich(tip) if tip else "",
            "bars": bars, "ruler": score_ruler(r, others, first)}


def score_ruler(r: Report, others: dict[str, Report], first: bool) -> str:
    """分数底下那行小字 —— **给这个分一把尺子**。

    「换书就换了一把尺子，分数是给『这个孩子 + 这本书』的，不是给孩子的」是
    英语科准则的第一条不可违反项，原话就写着「报告里要把这句话写出来」。
    以前只写在准则里、报告上一个字没有：页面最大的那个数字孤零零摆着，
    没有任何限定语，家长和孩子只能把它读成「这次考了 52 分」。

    上一次的分附在后面 —— 分数持平而准确率在涨的时候（p70-72 → p73-74
    正是这样），这一行就是唯一能解释「为什么涨了分却没动」的地方。

    **不写「换书就换了一把尺子」。** 超8 是第 8 级、里面 5 本书，难易在整套书里
    是分散的、不按册次递进 —— 拿「换了本书」去解释分数变化就是替数字找理由。
    难就是难、简单就是简单，按实测说；持平就是持平。
    """
    parts = []
    if first:                       # 一天读了三次就出现三遍，那句话只在头一节说
        parts.append("四项加起来 100 分：准确度 30 · 流利度 30 · 断句语调 25 · 发音 15")
    prev = others.get(r.prevs[-1]) if r.prevs else None
    if prev is not None and prev.score:
        parts.append(f"上一次 {prev.score} 分")
    return "。".join(parts) + "。" if parts else ""


def _is_number(text: str) -> bool:
    try:
        float(text.strip())
        return True
    except ValueError:
        return False


def parse_pairs(text: str) -> list[tuple[str, str]]:
    """「准确度=24/30 流利度=15/30」→ [(准确度, 24/30), …]

    lib/spec.py 的属性解析只认 ASCII 的 key=，中文 key 会整串留在 head 里 ——
    这是它有意为之（只解析骨架），各科自己解释。
    """
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"([^\s=]+)\s*=\s*([^\s]+)", text or "")]


def stats(r: Report) -> list[dict]:
    """四个数字。"""
    return [
        {"cls": "s1", "value": f"{r.accuracy}%", "unit": "", "label": f"读对 {r.correct}/{r.words} 词"},
        {"cls": "s2", "value": r.wcpm, "unit": "", "label": "每分钟正确词数"},
        # 「秒」小一号，跟在数字后面 —— 单位单独给，模板里套 <small>
        {"cls": "s3", "value": round(r.duration), "unit": "秒", "label": "读完全段"},
        {"cls": "s4", "value": r.pause_count, "unit": "", "label": "次停顿"},
    ]


def compare(r: Report, others: dict[str, Report]) -> dict | None:
    """和上一页比 / 三页放在一起看。

    四行数值全部算出来，spec 里只给趋势词（不给就用 +N / −N）。
    """
    b = r.blocks.get("对比")
    if not b or not r.prevs:
        return None
    chain = [others[s] for s in r.prevs if s in others] + [r]
    if len(chain) < 2:
        return None

    words = dict(parse_pairs("\n".join(
        ln.strip() for ln in b.lines if ln.strip() and not ln[:1].isspace())))

    rows = [
        ("准确率", [f"{x.accuracy}%" for x in chain], chain[-1].accuracy - chain[-2].accuracy, 1),
        ("正确词/分", [str(x.wcpm) for x in chain], chain[-1].wcpm - chain[-2].wcpm, 0),
        ("几个词一停", [str(x.per_group) for x in chain[:-1]] + [f"{chain[-1].per_group} 词"],
         chain[-1].per_group - chain[-2].per_group, 1),
        ("停顿占时长", [f"{round(x.pause_ratio * 100)}%" for x in chain],
         round(chain[-1].pause_ratio * 100) - round(chain[-2].pause_ratio * 100), 0),
    ]

    out = []
    for name, values, delta, digits in rows:
        # 停顿占比是「越小越好」，涨了要标红
        good = delta < 0 if name == "停顿占时长" else delta > 0
        cls = "flat" if abs(delta) < 10 ** -digits / 2 else ("up" if good else "down")
        tag = words.get(name) or (f"{'+' if delta > 0 else '−'}{abs(round(delta, digits) if digits else abs(int(delta)))}")
        # 前几次划掉、最后一次不划：「95.2% → 96.4% → 94.7%」。箭头由模板插
        out.append({"k": name, "was": values[:-1], "now": values[-1],
                    "cls": cls, "tag": str(tag)})

    note = joined(b.notes())
    icon, heading = ("📈", b.head) if len(chain) > 2 else ("↗️", b.head or "和上一页比")
    return {"icon": icon, "heading": heading, "rows": out,
            "note": rich(note) if note else ""}


def timeline(r: Report) -> dict:
    """停顿地图。

    bounds（原文真正的句末时刻）优先用 spec 里 [句末] 写的；没写就从原文的句号
    自动推 —— 自动那份认不出段落切换和引号内的分句，句末停顿会少数几次，
    所以印出去的报告还是人核一遍稳。
    """
    bounds = [float(x) for x, _ in spec_lib.Block(
        name="", lines=[r.blocks["句末"].head]).items()] if "句末" in r.blocks else auto_bounds(r)

    stalls = []
    if "卡壳" in r.blocks:
        for span, label in spec_lib.Block(name="", lines=[r.blocks["卡壳"].head]).items():
            a, _, bnd = span.partition("-")
            stalls.append((float(a), float(bnd), label))

    svg, counts = figures.timeline_svg(r.acoustics, bounds, stalls, r.skips)
    note = joined(r.blocks["卡壳"].notes()) if "卡壳" in r.blocks else ""
    # 图画的是**整段录音**（raw_duration），[跳过] 那几段涂灰；
    # 上面「四个数字」里的秒数和 WCPM 用的是扣完的 r.duration。两个数不一样是对的。
    return {"seconds": round(r.raw_duration), "svg": svg, "counts": counts,
            "note": rich(note) if note else ""}


def ref_text(slug: str) -> str:
    """这次朗读的比对基准 —— 原文按**朗读顺序**拼起来。

    两种落法都认，和喂数据台的 `Output/Reference.swift` 同一套口径：

        <slug>.ref.txt              一段朗读跨两页、当初两张图合成一份扫的
        <书>/<课>/pNN.ref.txt       一叠截图一次扫的（一页一份），按名字里的页码拼

    **后一种是常态** —— 教材截图一次扫十几页、录音当天晚上才录，
    所以 `p73-74` 这个名字下根本没有 `p73-74.ref.txt`，只有 `p73.ref.txt`
    和 `p74.ref.txt`。只认合起来那一份的话，`auto_bounds()` 会静默返回空，
    报告里「句末停顿」就成了 0 次（踩过：8/29 那份第一次构建就是 0）。
    """
    return "\n\n".join(p.read_text(encoding="utf-8") for p in ref_parts(slug))


def ref_parts(slug: str) -> list[Path]:
    """拼这次原文用到的那几个文件，**按朗读顺序**。

    `ref_text()` 拼文本、`std_times()` 拼时刻，两边都走这一份 —— 各拼一套
    的话，「原文第 i 个词」在文本和时刻里就不是同一个词了。
    """
    whole = DATA / f"{slug}.ref.txt"
    if whole.exists():
        return [whole]
    last = slug.rsplit("/", 1)[-1]
    m = re.fullmatch(r"[pP](\d+)(?:-(\d+))?", last)
    if not m:
        return []
    lo, hi = int(m[1]), int(m[2] or m[1])
    folder = DATA / slug.rsplit("/", 1)[0] if "/" in slug else DATA
    return [f for n in range(lo, hi + 1)
            if (f := folder / f"p{n}.ref.txt").exists()]


# 原文分词。词的边界和喂数据台的 `Aligner.words` 是同一套（撇号、连字符留在
# 词里），但**尾随标点保留** —— 句末那个点是划句子的唯一依据。
# `refTimes` / `pNN.ref.json` 的时刻都按这个词序排，所以这个正则改一个字符，
# 两份数据的下标就全错位了
_WORDS = re.compile(r"[A-Za-z0-9''\-]+[^\sA-Za-z0-9]*")
_SENT_END = re.compile(r"[.!?][\"']?$")


def auto_bounds(r: Report) -> list[float]:
    """从原文的句末标点推句末时刻。spec 没写 [句末] 时的兜底。"""
    text = ref_text(r.slug)
    if not (r.reading and text):
        return []
    times = r.reading.get("alignment", {}).get("refTimes") or []
    words = _WORDS.findall(text)
    return [times[i] for i, w in enumerate(words)
            if i < len(times) and times[i] is not None and _SENT_END.search(w)]


# 点一次最多听这么久。她读得慢、卡壳多，一句能拖到 39 秒（p6-8 那句 32 个词），
# 整句照播就成了「点一下等半分钟」。超过就以那个词为中心裁一段，两头不超出句子。
LISTEN_MAX = 12.0


def sentence_spans(text: str, times: list, ends: list | None = None
                   ) -> list[tuple[float, float] | None] | None:
    """原文每个词 → **它所在那一句**在音频里的起止秒数。

    点词听的是**那一句**，不是那一个词 —— 半秒钟的一个音节听不出所以然
    （`nice` 才 0.54 秒），得有上下文才判断得了读成了什么样。

    句子边界从原文的句末标点推。两种音源都走这一份：
    孩子的录音只记了一列 `refTimes`（每个原文词读到的时刻）；官方朗读记了
    起止两列（`pNN.ref.json`），`ends` 给了就用它收尾，不给按「末词 + 1.5 秒」凑。

    词数和时刻数对不齐就返回 None，让调用方退回「只播那个词」—— **别猜**。
    """
    words = _WORDS.findall(text) if text else []
    if not words or len(words) != len(times):
        return None

    def at(lo: int, hi: int, step: int = 1) -> float | None:
        return next((times[k] for k in range(lo, hi, step) if times[k] is not None), None)

    out: list[tuple[float, float] | None] = [None] * len(words)
    head = 0
    for i, w in enumerate(words):
        if not (_SENT_END.search(w) or i == len(words) - 1):
            continue
        a, b = at(head, i + 1), at(i, head - 1 if head else -1, -1)
        if a is not None and b is not None:
            # 末词的收尾：官方朗读那份直接有；孩子那份没记，用下一个词的开始，
            # 但别跨太远 —— 句子之间常有好几秒的停顿，整段拖进来就成了听静音
            tail = ends[i] if ends and i < len(ends) and ends[i] is not None else None
            nxt = at(i + 1, len(times))
            end = tail if tail is not None else (min(nxt, b + 1.5) if nxt is not None else b + 1.5)
            for k in range(head, i + 1):
                out[k] = (a, end)
        head = i + 1
    return out


def clip_index(r: Report) -> dict[str, list[tuple[float, float]]]:
    """原文词 → 点它该播录音的哪一段，按录音顺序排。

    默认给**整句**（见 sentence_spans）；句子对不齐或者太长，就退回以那个词
    为中心的一段。`read.json` 的每条差异本来就带 `start` / `end` 和 `refIndex`，
    这儿只是按词归个类。漏读那条没有时刻 —— **跳过去的词本来就没有声音**。

    spec 的 `[比对]` 是人从草稿里挑剩下的（撤掉了不计错的那些），但**顺序没变**，
    所以同一个词出现多次按顺序配就对得上。配不上就不给点 —— 优雅降级，
    宁可少一个按钮，也不要退回去解析说明文字里的「17.0 秒」：
    那种匹配一旦写错是**静默**失败，点开听到的是别处的声音，比没有更糟。
    """
    spans = sentence_spans(ref_text(r.slug),
                           ((r.reading or {}).get("alignment") or {}).get("refTimes") or [])
    out: dict[str, list[tuple[float, float]]] = {}
    for d in ((r.reading or {}).get("alignment") or {}).get("diffs", []):
        w, a, b = (d.get("ref") or "").lower(), d.get("start"), d.get("end")
        if not w or a is None or b is None:
            continue
        i = d.get("refIndex")
        span = spans[i] if spans and isinstance(i, int) and 0 <= i < len(spans) else None
        if span:
            lo, hi = span
            if hi - lo > LISTEN_MAX:        # 长句：以这个词为中心裁，不超出句界
                lo, hi = max(lo, a - LISTEN_MAX / 2), min(hi, a + LISTEN_MAX / 2)
        else:
            lo, hi = float(a), float(b)     # 没有句子信息，退回只播这个词
        out.setdefault(w, []).append((lo, hi))
    return out


def std_times(slug: str) -> tuple[str, list, list] | None:
    """原文每个词在**官方朗读**里的起止时刻 —— 绿词播的就是这一段。

    数据是 `feeder ref` 落的 `pNN.ref.json`（原文的两条来路里，从配套朗读音频
    转写那一条）。教材截图那条（`scan`）没有这份东西 → 返回 None，
    绿词照旧退回浏览器念 —— **超8 现在走的就是那条**，所以这不是缺陷。

    **逐页校验词数。** `.ref.txt` 是人核过的（转写把 Leimert 听成 Le Mert，
    人改回来那一页就少两个词），词数一对不上就把那一页的时刻整页丢掉 ——
    错一位在页面上只表现成「点绿词听到别处的声音」，比没有更糟。
    实测 wonders3/u1w3 的十四页里 p16 正是这一种。
    """
    src = ""
    starts: list[float | None] = []
    ends: list[float | None] = []
    got = False
    for txt in ref_parts(slug):
        n = len(_WORDS.findall(txt.read_text(encoding="utf-8")))
        jf = txt.with_name(txt.name.removesuffix(".txt") + ".json")
        words = None
        if jf.exists():
            d = json.loads(jf.read_text(encoding="utf-8"))
            ws = d.get("words") or []
            name = d.get("source") or ""
            if len(ws) != n:
                print(f"    · {jf.name}：{len(ws)} 个时刻对不上原文 {n} 个词"
                      " —— 这一页的绿词退回浏览器念")
            elif src and name != src:
                # 一次朗读的几页来自不同音频。页面上只有一条 <audio class=std>，
                # 混着放会拿这本书的时刻去另一本上找
                print(f"    · {jf.name}：音源不是上一页那个文件 —— 这一页的绿词退回念")
            elif not name:
                pass                         # 老数据没记音源，找不到音频
            else:
                src, words = name, ws
        if words:
            starts += [w.get("start") for w in words]
            ends += [w.get("end") for w in words]
            got = True
        else:
            starts += [None] * n
            ends += [None] * n
    return (src, starts, ends) if got else None


def std_src(r: Report) -> str | None:
    """官方朗读的音频文件名 —— 本机素材堆里有才返回，没有给 None。

    和孩子的录音同一条路（见 `audio_src`）：素材永不进仓库，CI 上 `inbox/`
    不存在 → None → 页面里不出 `<audio class="std">`，点绿词退回浏览器念。
    版权音频和孩子的声音一样，只在本机听得到。
    """
    got = std_times(r.slug)
    return got[0] if got and got[0] and paths.material(got[0]) else None


def _bare(w: str) -> str:
    """一个词剥到只剩字母数字，小写 —— 比原文行和原文词流用这一把尺子。"""
    return re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9']+$", "", w).lower()


def std_spots(r: Report, items: list[dict]) -> list[tuple[float, float] | None]:
    """`[比对]` 每一条 → 点它的绿词该播官方朗读的哪一段。和条目一一对应。

    **按原文那一行整段定位，不按「这个词第几次出现」配。** spec 里的「原文」
    一行就是原文的一小段（草稿从 `diff.context` 起草，高亮词前后各三个词），
    拿它当 n-gram 在原文词流里找，位置唯一就锚死了。

    为什么不能像红词那样按词配（那份的时刻只存在于差异条目里，只能按词配）：
    **spec 的条目和 `read.json` 的差异不是一一对应的** —— p68 那处机器判成
    `insert(syria)` + `omit(celia)` 两条，人合写成一条「Celia 读成 Syria」。
    按条目顺序或按词次序配都会错位，而错位在页面上只表现成
    「点绿词听到别处的声音」，比不给点更糟。

    同一行在 spec 里重复出现（同一句读错两次）就按出现次序取第几处匹配；
    找不到、或匹配处数不够，就不给点 —— 优雅降级。
    """
    blank: list[tuple[float, float] | None] = [None] * len(items)
    got = std_times(r.slug)
    if not got:
        return blank
    _, starts, ends = got
    text = ref_text(r.slug)
    spans = sentence_spans(text, starts, ends)
    flow = [_bare(w) for w in _WORDS.findall(text)]
    if not flow:
        return blank

    out: list[tuple[float, float] | None] = []
    seen: dict[str, int] = {}
    for it in items:
        raw = it["ref"]
        # `*Celia*` 那个**收尾**的星号会被 _WORDS 吸进词里（开头那个不会）——
        # 拿它认出高亮词是这一行的第几个。多词高亮认到末词，反正同一句
        toks = _WORDS.findall(raw)
        hl = next((k for k, w in enumerate(toks) if "*" in w), None)
        bare = [_bare(w) for w in toks]
        n = len(bare)
        if hl is None or not n:
            out.append(None)
            continue
        hits = [k for k in range(len(flow) - n + 1) if flow[k:k + n] == bare]
        seq = seen.get(raw, 0)
        seen[raw] = seq + 1
        if seq >= len(hits):
            out.append(None)
            continue
        i = hits[seq] + hl
        span = spans[i] if spans and 0 <= i < len(spans) else None
        a = starts[i] if 0 <= i < len(starts) else None
        if span is None and a is not None:
            # 句子划不出来（时刻缺了几个）：退回只播这一个词
            span = (a, ends[i] if ends[i] is not None else a + 1.2)
        if span and a is not None and span[1] - span[0] > LISTEN_MAX:
            # 长句：以这个词为中心裁，不超出句界。念得比她快，超长的少见
            span = (max(span[0], a - LISTEN_MAX / 2), min(span[1], a + LISTEN_MAX / 2))
        out.append(span)
    return out


def audio_src(r: Report) -> str | None:
    """这次录音的原始文件名 —— 本机素材堆里有才返回，没有给 None。

    **录音永不进仓库**（DATA.md 的「素材」那一档）。所以这条链路天生只在本地成立：
    CI 上 `inbox/` 不存在 → 这儿返回 None → 页面里一个 `<audio>` 都不出。
    不需要额外的开关，也就没有「忘了关」把孩子的声音带上公网的可能。
    """
    name = (r.acoustics or {}).get("source") or ""
    return name if paths.material(name) else None


def diffs(r: Report) -> dict | None:
    """逐字比对。

    条目按「原文 / 实读」成对出现，缩进行是说明。用「识别成」代替「实读」
    表示这处转写不可信 —— 编号出 `?`，别让它长得像已经定案的。
    """
    b = r.blocks.get("比对")
    if not b:
        return None

    items, cur = [], None
    for line in b.lines:
        stripped = line.strip()
        if not stripped:
            continue
        if line[:1].isspace():
            if cur:
                cur["why"].append(stripped)
            continue
        head, _, rest = stripped.partition(" ")
        if head == "原文":
            cur = {"ref": rest, "read": "", "lbl": "实读", "why": []}
            items.append(cur)
        elif head in ("实读", "识别成") and cur:
            cur["read"], cur["lbl"] = rest, head
        elif cur:                       # 没有前缀的行：当成上一条的续行
            cur["why"].append(stripped)

    spots, taken = clip_index(r), {}
    stds = std_spots(r, items)          # 绿词：和 items 一一对应
    out = []
    n = 0
    for idx, it in enumerate(items):
        doubt = it["lbl"] == "识别成"
        if doubt:
            num = "?"
        else:
            n += 1
            num = str(n)
        why = joined(it["why"])
        # 同一个词在一次录音里可能错好几回（`Alp` 在 p6-8 里两处），按出现顺序配
        word = _plain(picked(it["ref"])).lower()
        here = spots.get(word) or []
        k = taken.get(word, 0)
        clip = here[k] if k < len(here) else None
        if clip:
            taken[word] = k + 1
        out.append({"num": num, "doubt": doubt, "lbl": it["lbl"],
                    "ref": marked(it["ref"], "mark", say=True, std=stds[idx]),
                    "read": marked(it["read"], "ins", say=True, clip=clip),
                    "why": rich(why) if why else ""})
    # 抬头不写就自己数。存疑那条也算一处 —— 它同样是对不上的地方，
    # 只是判不准该算谁的，所以编号出 ? 而不是从计数里拿掉
    return {"heading": b.head or f"逐字比对 · {len(items)} 处", "rows": out}


def lines_block(r: Report, name: str, icon: str, default_head: str, cls: str = "text") -> dict | None:
    """磕巴 / 亮点这类「几行内容 + 一段小字注」的区块。模板里的 `texts` 一节。"""
    b = r.blocks.get(name)
    if not b:
        return None
    note = joined(b.notes())
    return {
        "icon": icon,
        "heading": b.head or default_head,
        "cls": cls,
        "gap": 8,
        "paras": [marked(ln.strip(), "ins")
                  for ln in b.lines if ln.strip() and not ln[:1].isspace()],
        "note": rich(note) if note else "",
    }


def highlight(r: Report) -> dict | None:
    """读得好的地方：主段是正文，缩进行是小字注。也走模板的 `texts` 一节。"""
    b = r.blocks.get("亮点")
    if not b:
        return None
    note = joined(b.notes())
    return {
        "icon": "🌟",
        "heading": "读得好的地方",
        "cls": "",          # 这一节的段落不加 .text（字号跟正文走）
        "gap": 6,
        "paras": [rich(m) for m in
                  grouped([ln for ln in b.lines if ln.strip() and not ln[:1].isspace()])],
        "note": rich(note) if note else "",
    }


def todos(r: Report) -> list[dict]:
    """下次试试这三件事。每条：一个 emoji 起头的标题行 + 缩进的说明行。"""
    b = r.blocks.get("三件事")
    if not b:
        return []
    items, cur = [], None
    for line in b.lines:
        if not line.strip():
            continue
        if line[:1].isspace():
            if cur:
                cur["desc"].append(line.strip())
            continue
        icon, _, title = line.strip().partition(" ")
        cur = {"icon": icon, "title": title, "desc": []}
        items.append(cur)

    return [{"icon": it["icon"], "title": rich(it["title"]),
             "desc": rich(joined(it["desc"]))} for it in items]


def pages(r: Report) -> dict | None:
    """一次录音跨几页时的小结（`[分页]`）。

    **只是标注。** 颗粒度是一次录音 —— 一份数据、一份 spec、一份报告；
    这张表里的数是喂数据台从**同一份对齐**里派生的，不是分开测的。
    一页的录音不写这个区块，也就不出这张表。

    一行一页，`第 68 页 = 2.9-138.5 秒 · 128 词 · 候选错 9 处`，
    缩进行是整段的小字注。右边原样印，人怎么改都行。
    """
    b = r.blocks.get("分页")
    if not b:
        return None
    rows = []
    for ln in b.lines:
        if not ln.strip() or ln[:1].isspace():
            continue
        k, _, v = ln.strip().partition("=")
        rows.append({"k": rich(k.strip()), "v": rich(v.strip())})
    if not rows:
        return None
    note = joined(b.notes())
    return {"heading": b.head or f"这次读了 {len(rows)} 页",
            "rows": rows, "note": rich(note) if note else ""}


def slashes(r: Report) -> list[str]:
    """画好斜线的版本 —— 按意群断句，一条斜线一口气。斜线由模板插。"""
    b = r.blocks.get("斜线")
    if not b:
        return []
    return [ln.strip() for ln in b.lines if ln.strip() and not ln[:1].isspace()]


def scales(r: Report) -> str:
    """三把尺子。三句 note 顺序固定：准确率 / WCPM / 断句语调。"""
    notes = grouped(r.blocks["尺子"].lines) if "尺子" in r.blocks else []
    while len(notes) < 3:
        notes.append("")
    prev_acc = None
    if r.prevs:
        prev_acc = getattr(r, "_prev_acc", None)
    return figures.block(r.accuracy, r.wcpm, r.naep, tuple(rich(n) for n in notes[:3]), prev_acc)


def how(r: Report) -> list[str]:
    b = r.blocks.get("怎么来的")
    if not b:
        return []
    return [rich(para) for para in grouped(b.lines)]


# ══════════════════════════════════════════════════════════════
# 组装
# ══════════════════════════════════════════════════════════════

def anchor(slug: str) -> str:
    """slug → 日页里的锚点 id：`super8/L3/p68-69` → `super8-L3-p68-69`。"""
    return slug.replace("/", "-")


def card_ctx(r: Report, others: dict[str, Report], *,
             lesson: bool = False, book: bool = False, first: bool = True) -> dict:
    """日页里**一次录音**那一节的上下文。版式在 review/one.html 的 card 宏。

    两套色（分类色 / 分数色）作为 fg / bg / cat 传出去，由模板注在这一节的
    行内 style 上 —— 一页有好几次录音、分数各不同，注在 :root 上会互相盖掉。
    """
    fg, bg = figures.score_color(r.score)
    return {
        "anchor": anchor(r.slug),
        "cat": r.color_var, "fg": fg, "bg": bg,
        # 本机有原始录音才出 <audio>（线上永远没有，见 audio_src）
        "audio": audio_src(r),
        # 官方朗读那份（绿词的音源）。同样只在本机有，见 std_src
        "std": std_src(r),
        "hero": hero(r, lesson=lesson, book=book),
        "score": score_box(r, others, first=first),
        "stats": stats(r),
        "compare": compare(r, others),
        "timeline": timeline(r),
        "pages": pages(r),
        "diffs": diffs(r),
        # 「亮点」和「磕巴」版式相同（几行内容 + 一段小字注），共用模板里的 textblk 宏，
        # 但**位置各排各的**：正面的那块跟在「和上一次比」后面，磕巴排到逐字比对之后。
        # 原先两块挤在一个 texts 列表里连着出，读得好的地方只能跟在磕巴屁股后面
        "good": highlight(r),
        "stumbles": lines_block(r, "磕巴", "🌀", "读了两遍才接上的地方"),
        "todos": todos(r),
        "slashes": slashes(r),
        "scales": scales(r),
        "how": how(r),
    }


def render_day(date: str, rows: list[Report], others: dict[str, Report],
               summary: dict, out_dir: Path, pdf: bool) -> bool:
    """**一天一个页面**：dist/english/review/<YYYY-MM-DD>.html。

    以前是一次录音一个页面，目录页列着当天的三条各自点进去。并成一页是因为
    平时看的就是「今天整体怎么样」—— 为一次 90 秒的朗读单开一个 URL，
    每天要点三次才看得全。目录页仍然列出每一次，只是链到这一页的锚点。
    """
    # 当天只读了一课 / 一本，卷名和书名就归页眉，每节不再重复；跨了才下放到节里
    lessons = {r.spec.title for r in rows}
    books = {r.spec.get("book", "") for r in rows if r.spec.get("book")}
    pieces = []
    if len(lessons) == 1:
        pieces.append(next(iter(lessons)))
    if len(books) == 1:
        pieces.append(f"《{next(iter(books))}》")
    pieces.append(f"{len(rows)} 次朗读")

    cards = [card_ctx(r, others, lesson=len(lessons) > 1, book=len(books) > 1,
                      first=(i == 0))
             for i, r in enumerate(rows)]

    # 本机有原始录音的，软链一条进 dist/ —— **软链不是拷贝**：源文件动辄几十兆，
    # 拷一遍既慢又占地方，而 `make up` 起的 http.server 跟随软链毫无问题。
    # dist/ 整个不进 git，所以这条链和它指向的录音都到不了线上。
    for c in cards:
        # 两种音源同一条路：她自己那段录音，和这本书的官方朗读
        for name in (c["audio"], c["std"]):
            if not name or not (src := paths.material(name)):
                continue
            link = out_dir / name
            link.parent.mkdir(parents=True, exist_ok=True)
            link.unlink(missing_ok=True)
            link.symlink_to(src)

    body = tmpl.body(
        "review/day.html",
        day={"label": pretty_date(date),
             "sub": dot_join(pieces),
             "sum": summary},
        reports=cards,
    )

    total = summary["words"]
    desc = (f"{pretty_date(date)}：{summary['times']} 次朗读共 {total} 个词，"
            f"合计读对 {summary['accuracy']}%，每分钟 {summary['wcpm']} 个正确词。")

    out = page.write(
        out_dir / f"{date}.html",
        page.render(
            title=f"{pretty_date(date)} · 打卡评价",
            description=desc,
            body=body,
            emoji="🎤",
            css=("review.css", "daysum.css", "review-play.css"),
            js=("review-play.js",),
            root="../..",           # dist/english/review/<date>.html，日页是平的
            noindex=True,           # 孩子的成绩单，不进搜索引擎
        ),
    )
    names = "、".join(r.title for r in rows)
    print(f"    → review/{date}.html  （{names}）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


# ══════════════════════════════════════════════════════════════
# result 层：算出来的指标落成一张表
# ══════════════════════════════════════════════════════════════

RESULT_FIELDS = ["slug", "date", "order", "cat", "book", "page",
                 "words", "errors", "correct", "accuracy", "wcpm",
                 "duration", "pause_count", "pause_ratio", "per_group",
                 "score", "naep"]


def write_result(reports: list[Report]) -> None:
    """把每份报告算出来的指标落成 storage/result/english/review.csv。

    **全量重算覆盖，不追加。** 追加不幂等，而且没必要 —— 全部 spec 和测量数据都在
    git 里，历史随时能重算一遍。push 这张表是为了 `git diff` 能看出「改了算法，
    哪些指标动了」，不是为了记住历史。

    **只放纯数据，一个 HTML 标签都不许进来。** 这张表要能直接喂给别的工具
    （趋势页、notebook、Excel），混进 `<a>` 就得先清洗才能用。
    """
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    with RESULT.open("w", newline="", encoding="utf-8") as f:
        # lineterminator 必须显式给 —— csv 默认写 \r\n，git 会当 CRLF 反复归一化，
        # 「git diff 看指标变化」这条用途就被换行噪音盖掉了
        w = csv.writer(f, lineterminator="\n")
        w.writerow(RESULT_FIELDS)
        for r in sorted(reports, key=lambda x: (x.date, x.order)):
            w.writerow([r.slug, r.date, r.order, r.cat,
                        r.spec.get("book", ""), r.spec.get("page", ""),
                        r.words, r.errors, r.correct, r.accuracy, r.wcpm,
                        r.duration, r.pause_count, r.pause_ratio, r.per_group,
                        r.score, r.naep])
    print(f"    → result/english/review.csv  （{len(reports)} 行）")

    # 错误明细：一行一处错。趋势页的分类统计和 Top3 从这儿读回来。
    #
    # **为什么另出一张表、不在 review.csv 上加八列**：Top3 要按「哪个词反复栽」排，
    # 那是词级的，八个计数列装不下。一行一处错既能按类型汇总、也能按词汇总，
    # 而且它和 review.csv 一样是**可再生**的 —— 全量重算覆盖。
    ERRORS_RESULT.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with ERRORS_RESULT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["slug", "date", "book", "word", "kind"])
        for r in sorted(reports, key=lambda x: (x.date, x.order)):
            for word, kind in r.error_words:
                w.writerow([r.slug, r.date, r.spec.get("book", ""), word, kind])
                rows += 1
    print(f"    → result/english/review-errors.csv  （{rows} 处错）")


def read_result() -> list[dict]:
    """读回 result 表。缺文件当空 —— 和 data 那几个可选文件一个口径。"""
    if not RESULT.exists():
        return []
    with RESULT.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def error_stats(limit_recent: int = 3) -> dict | None:
    """错误按类型汇总 + Top3「练哪个最划算」。数据从 review-errors.csv 读回来。

    **Top3 按「最近几次」排，不按全期。** 要治的是她现在还在犯的毛病 ——
    专名那一类全期 8 处（4.8%），但最近三次只剩 1 处：Alp 早就读对了，
    再把它排进 Top3 就是让人去练一个已经解决的问题。
    近期和全期各自的占比都印出来，涨还是收敛一眼能看见。

    每条 Top 还点名这一类里**反复栽的那几个词** —— 「元音 18 处」是问题的大小，
    「hut 四次全读成 heart」才是下手的地方。
    """
    if not ERRORS_RESULT.exists():
        return None
    rows = list(csv.DictReader(ERRORS_RESULT.open(encoding="utf-8")))
    if not rows:
        return None

    dates = sorted({r["date"] for r in rows})
    recent = set(dates[-limit_recent:])
    rec_rows = [r for r in rows if r["date"] in recent]

    def tally(src: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in src:
            out[r["kind"]] = out.get(r["kind"], 0) + 1
        return out

    all_n, rec_n = tally(rows), tally(rec_rows)
    total, rtotal = len(rows), max(len(rec_rows), 1)

    kinds = []
    for kind in sorted(all_n, key=lambda k: -all_n[k]):
        share, rshare = all_n[kind] / total * 100, rec_n.get(kind, 0) / rtotal * 100
        kinds.append({
            "kind": kind, "n": all_n[kind], "share": round(share, 1),
            "rn": rec_n.get(kind, 0), "rshare": round(rshare, 1),
            # ±3 个百分点以内算持平：11 次朗读、166 处错，比这更小的差是噪音
            "trend": "up" if rshare > share + 3 else "down" if rshare < share - 3 else "flat",
            "pct": round(all_n[kind] / max(all_n.values()) * 100),
        })

    top = []
    for k in sorted(kinds, key=lambda x: (-x["rn"], -x["n"]))[:3]:
        # 这一类里反复栽的词：同一个词栽两次以上，那是最省力的下手处
        words: dict[str, int] = {}
        for r in rows:
            if r["kind"] == k["kind"]:
                w = r["word"].lower().rstrip(".,!?\"'")
                words[w] = words.get(w, 0) + 1
        repeat = sorted((w for w in words.items() if w[1] >= 2), key=lambda x: -x[1])[:4]
        top.append({**k, "how": ERROR_KINDS.get(k["kind"], ""),
                    "repeat": [{"w": w, "n": n} for w, n in repeat]})

    return {"total": total, "rtotal": len(rec_rows), "days": len(recent),
            "kinds": kinds, "top": top,
            "covered": sum(x["rn"] for x in top),
            "covered_pct": round(sum(x["rn"] for x in top) / rtotal * 100)}


def build_trend(out_dir: Path) -> bool:
    """趋势页：两条曲线 + 一张全量数据表。

    **故意从 CSV 读，不用内存里的 reports。** 这样 result 表就必须是能被别处消费的
    纯数据，而不是构建内部的一个临时变量 —— 别的工具从同一个文件取数，看到的和
    这一页完全一样。少于两次朗读画不出趋势，直接不出这一页。
    """
    rows = read_result()
    if len(rows) < 2:
        print("    · 趋势：不足两次朗读，跳过")
        return False

    # x 轴标签只写页码，不写「第 … 页」—— 一次录音跨几页时标签是「70–72」这种区间，
    # 两个区间标签挨在一起就重叠了（7 个点、390px 宽，实测叠了 7.8px）。
    # 哪一轴是什么，图的标题和轴末的单位已经说清楚了。
    label = lambda r: str(r["page"] or r["order"])
    acc = [(label(r), float(r["accuracy"])) for r in rows]
    wcpm = [(label(r), int(r["wcpm"])) for r in rows]

    def short_date(iso: str) -> str:
        """趋势表里日期只留月/日 —— 390px 宽放不下「2026 年 8 月 25 日」。"""
        parts = iso.split("-")
        return f"{int(parts[1])}/{int(parts[2])}" if len(parts) == 3 else iso

    body = tmpl.body(
        "review/trend.html",
        n=len(rows),
        accuracy_svg=figures.trend_svg(acc, 86, 100, (90, 95, 98), "准确率 %"),
        wcpm_svg=figures.trend_svg(wcpm, 0, 100, (0, 50, 100), "WCPM", "var(--c-listen)"),
        errs=error_stats(),
        rows=[{**r,
               "date": short_date(r["date"]),
               # 表里只留「课/页」，全 slug 在 390px 上放不下
               "slug": "/".join(r["slug"].split("/")[-2:]),
               "fg": figures.score_color(int(r["score"]))[0]}
              for r in rows],
    )

    page.write(
        out_dir / "trend.html",
        page.render(
            title="朗读趋势 · 打卡评价",
            description="把每次朗读的准确率和每分钟正确词数放在一条线上看。",
            body=body,
            emoji="📈",
            css=("site.css", "trend.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → review/trend.html  （{len(rows)} 次）")
    return True


def day_summary(rows: list[Report], prev: list[Report] | None) -> dict:
    """一天的整体汇总 —— 目录页每个日期分组头上那一条。

    **合计不是平均。** 准确率按「当天读对的总词数 ÷ 当天总词数」算，不是把几份
    报告的准确率取平均 —— 读了 30 个词的一次和读了 130 个词的一次，权重本来
    就不该一样。WCPM 同理，除的是当天的总时长。

    **涨跌照给，不看是不是同一本书。** 超8 是第 8 级、5 本书，难易分散不递进，
    「换本书就不能比」这个前提本身不成立。数字就是数字：涨了标涨、跌了标跌、
    持平就是持平，别替它找理由。文本这次难还是简单，按实测写进报告正文。
    """
    words = sum(r.words for r in rows)
    correct = sum(r.correct for r in rows)
    dur = sum(r.duration for r in rows)
    books = {r.spec.get("book", "") for r in rows}

    out = {  # noqa: E126
        "times": len(rows),
        "pages": sum(r.page_count for r in rows),
        "words": words,
        "accuracy": round(correct / words * 100, 1) if words else 0,
        "wcpm": round(correct / dur * 60) if dur else 0,
        "minutes": round(dur / 60),
        "mixed": len(books) > 1,
        "deltas": [],
    }

    if not prev:
        return out
    pw = sum(r.words for r in prev)
    pc = sum(r.correct for r in prev)
    pd = sum(r.duration for r in prev)
    if not (pw and pd):
        return out
    for key, now, was, digits in (
        ("accuracy", out["accuracy"], round(pc / pw * 100, 1), 1),
        ("wcpm", out["wcpm"], round(pc / pd * 60), 0),
    ):
        d = round(now - was, digits)
        out["deltas"].append({"k": key, "up": d > 0,
                              "flat": abs(d) < 10 ** -digits / 2,
                              "tag": f"{'+' if d > 0 else '−'}{abs(d)}"})
    return out


def build_index(out_dir: Path, by_date: dict[str, list[Report]], order: list[str],
                sums: dict[str, dict], pdfs: dict[str, bool],
                trend: bool, total: int) -> None:
    """目录页：按日期倒序，每天一条汇总 + 当天每次录音一行。

    行链的是**日页的锚点**（`2026-08-27.html#super8-L3-p68-69`）——
    报告已经并进日页了，一次录音不再单独占一个 URL。
    """
    days = []
    for date in order:
        items = []
        for r in by_date[date]:
            fg, bg = figures.score_color(r.score)
            items.append({
                "href": f"{date}.html#{anchor(r.slug)}",
                "title": r.title,
                "small": f"{r.sub} · {r.accuracy}% · 每分钟 {r.wcpm} 词",
                "cat": r.cat, "score": r.score,
                "fg": fg, "bg": bg, "color": r.color_var,
            })
        days.append({
            "label": pretty_date(date),
            "href": f"{date}.html",
            # 报告本身是网页（手机上看），PDF 只是想转发给别人时的附加件。
            # 现在一天一份，所以挂在日期那一行，不再一次录音一个
            "pdf": f"{date}.pdf" if pdfs.get(date) else None,
            "rows": items,
            "sum": sums[date],
        })

    body = tmpl.body("review/index.html", total=total, trend=trend, days=days)

    page.write(
        out_dir / "index.html",
        page.render(
            title="打卡评价 · 英语",
            description="每天的朗读作业，一份能和下次比的成绩单：逐字比对、停顿地图、三把尺子上的位置。",
            body=body,
            emoji="🎤",
            css=("site.css", "review-index.css", "daysum.css"),
            root="../..",
        ),
    )
    print(f"    → review/index.html  （{len(order)} 天 · {total} 次）")


def build_review(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "review"
    specs = spec_lib.specs(SPECS, deep=True)
    if not specs:
        print("    · 打卡评价：specs/ 里还没有 spec，跳过")
        return

    reports = [Report(spec_lib.parse(p)) for p in specs]
    others = {r.slug: r for r in reports}

    # prev 指向的 slug 必须真存在 —— 指错了是**静默**失败：分数底下的「上一次 N 分」
    # 和整个「和上一次比」区块直接不出，页面看着完好，只是少了一块。
    # 踩过：p6-8 写 `prev: p73-74`，同课补全成 `super8/L4/p73-74`，
    # 而它在 L3 —— **跨课的 prev 必须写全名**。
    for r in reports:
        for s in r.prevs:
            if s not in others:
                near = [k for k in others if k.rsplit("/", 1)[-1] == s.rsplit("/", 1)[-1]]
                spec_lib.die(
                    f"{r.slug}: prev 指向的 {s} 不存在 —— 只写页码会补成本课的，"
                    f"跨课要写全名"
                    + (f"（是不是想写 {near[0]}？）" if near else ""))

    # 三把尺子上要标出上一页的位置，得先把彼此认全
    for r in reports:
        if r.prevs and r.prevs[-1] in others:
            r._prev_acc = others[r.prevs[-1]].accuracy

    # 一天一个页面：先按日期分组，组内按分类顺序再按 order
    by_date: dict[str, list[Report]] = {}
    for r in reports:
        by_date.setdefault(r.date, []).append(r)
    cat_rank = {c: i for i, c in enumerate(CATS)}
    for rows in by_date.values():
        rows.sort(key=lambda x: (cat_rank.get(x.cat, 99), x.order))

    # 「和上一天比」要拿时间上更早的那一天 —— 目录页是倒序渲染的，先把顺序算好
    order = sorted(by_date, reverse=True)
    earlier = {d: order[i + 1] if i + 1 < len(order) else None for i, d in enumerate(order)}
    sums = {d: day_summary(by_date[d], by_date.get(earlier[d])) for d in order}

    pdfs = {d: render_day(d, by_date[d], others, sums[d], out_dir, pdf)
            for d in sorted(by_date)}

    # 先落 result 表，趋势页再从那张表读回来 —— 顺序不能反
    write_result(reports)
    trend = build_trend(out_dir)
    build_index(out_dir, by_date, order, sums, pdfs, trend, len(reports))
