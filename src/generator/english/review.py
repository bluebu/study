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
  · **换书就换了一把尺子** —— 分数是给「这个孩子 + 这本书」的，不是给孩子的
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

        # ── 其余全部算出来
        self.duration = float(self.acoustics["duration"])
        self.pause_count = int(self.acoustics["pause_count"])
        self.pause_ratio = float(self.acoustics["pause_ratio"])
        self.correct = self.words - self.errors
        self.accuracy = round(self.correct / self.words * 100, 1)
        self.wcpm = round(self.correct / self.duration * 60) if self.duration else 0
        # 几个词一停：全段词数 ÷ 停顿次数。老站三份报告都是这么算的
        self.per_group = round(self.words / self.pause_count, 1) if self.pause_count else 0

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

        # 想过再加一条「[比对] 的条数 == errors」，**撤了**：这两个数本来就不相等，
        # 口径允许两个方向都差（一条含两处错 → errors 多；回读或课本印错写「实读」
        # 但不计错 → errors 少）。实测 7 份 spec 里 5 份都会响 —— 在多数情况下都响的
        # 检查没有信号，只是噪音。报告里编号是顺着「实读」排的，编号最大值不等于
        # errors 属正常，这条写进了 skill 的自检清单。

        # ③ [卡壳] / [句末] 抬头行的每一段，起止都要能转成浮点
        for blk, how in (("卡壳", "起-止 = 标签"), ("句末", "时刻")):
            if blk not in self.blocks:
                continue
            for item, label in spec_lib.Block(name="", lines=[self.blocks[blk].head]).items():
                bad = [x for x in (item.split("-") if blk == "卡壳" else [item])
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
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out


def marked(text: str, tag: str) -> str:
    """把 *xxx* 换成 <mark>/<ins>。"""
    return re.sub(r"\*(.+?)\*", rf"<{tag}>\1</{tag}>", rich(text))


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

    同一本书里上一次的分附在后面 —— 分数持平而准确率在涨的时候（p70-72 → p73-74
    正是这样），这一行就是唯一能解释「为什么涨了分却没动」的地方。
    """
    book = r.spec.get("book", "")
    if not book:
        return ""
    parts = []
    if first:                       # 一天读了三次就出现三遍，那句话只在头一节说
        parts.append(f"这个分是给《{book}》这本书的 —— 换一本书就换了一把尺子，"
                     f"只在同一本书里跨天比才作数")
    prev = others.get(r.prevs[-1]) if r.prevs else None
    if prev is not None and prev.score and prev.spec.get("book", "") == book:
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

    svg, counts = figures.timeline_svg(r.acoustics, bounds, stalls)
    note = joined(r.blocks["卡壳"].notes()) if "卡壳" in r.blocks else ""
    return {"seconds": round(r.duration), "svg": svg, "counts": counts,
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
    whole = DATA / f"{slug}.ref.txt"
    if whole.exists():
        return whole.read_text(encoding="utf-8")
    last = slug.rsplit("/", 1)[-1]
    m = re.fullmatch(r"[pP](\d+)(?:-(\d+))?", last)
    if not m:
        return ""
    lo, hi = int(m[1]), int(m[2] or m[1])
    folder = DATA / slug.rsplit("/", 1)[0] if "/" in slug else DATA
    pages = [folder / f"p{n}.ref.txt" for n in range(lo, hi + 1)]
    return "\n\n".join(p.read_text(encoding="utf-8") for p in pages if p.exists())


def auto_bounds(r: Report) -> list[float]:
    """从原文的句末标点推句末时刻。spec 没写 [句末] 时的兜底。"""
    text = ref_text(r.slug)
    if not (r.reading and text):
        return []
    times = r.reading.get("alignment", {}).get("refTimes") or []
    words = re.findall(r"[A-Za-z0-9''\-]+[^\sA-Za-z0-9]*", text)
    return [times[i] for i, w in enumerate(words)
            if i < len(times) and times[i] is not None and re.search(r"[.!?][\"']?$", w)]


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

    out = []
    n = 0
    for it in items:
        doubt = it["lbl"] == "识别成"
        if doubt:
            num = "?"
        else:
            n += 1
            num = str(n)
        why = joined(it["why"])
        out.append({"num": num, "doubt": doubt, "lbl": it["lbl"],
                    "ref": marked(it["ref"], "mark"),
                    "read": marked(it["read"], "ins"),
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

    body = tmpl.body(
        "review/day.html",
        day={"label": pretty_date(date),
             "sub": dot_join(pieces),
             "sum": summary},
        reports=[card_ctx(r, others, lesson=len(lessons) > 1, book=len(books) > 1,
                          first=(i == 0))
                 for i, r in enumerate(rows)],
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
            css=("review.css", "daysum.css"),
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


def read_result() -> list[dict]:
    """读回 result 表。缺文件当空 —— 和 data 那几个可选文件一个口径。"""
    if not RESULT.exists():
        return []
    with RESULT.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


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

    **跨本不给涨跌。** 「换书就换了一把尺子」是这个栏目的铁律：分数是给
    「这个孩子 + 这本书」的。当天读了两本书、或者和上一天读的不是同一本，
    合计只当个流水，不标 +N / −N —— 标了就是在拿两把尺子量出来的数相减。
    """
    words = sum(r.words for r in rows)
    correct = sum(r.correct for r in rows)
    dur = sum(r.duration for r in rows)
    books = {r.spec.get("book", "") for r in rows}

    out = {
        "times": len(rows),
        "pages": sum(r.page_count for r in rows),
        "words": words,
        "accuracy": round(correct / words * 100, 1) if words else 0,
        "wcpm": round(correct / dur * 60) if dur else 0,
        "minutes": round(dur / 60),
        "mixed": len(books) > 1,
        "deltas": [],
    }

    # 涨跌只在「两天都只读了同一本书」时给
    if not prev or len(books) != 1:
        return out
    pb = {r.spec.get("book", "") for r in prev}
    if pb != books:
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
