"""英语 · 打卡评价 —— 每天的朗读作业，一份能和下次比的成绩单。

    src/english/review/
      data/<slug>.read.json   喂数据台（../feeder）产出：声学 + 转写 + 逐字对齐
      data/<slug>.json        同上，停顿声学单独一份（和老站 data/ 字段逐个对齐）
      data/<slug>.ref.txt     红线划中的课文原文 —— 比对基准
      specs/<slug>.txt        人的判断：哪几处算读错、四维分数、点评

产物落在 dist/english/review/：一页一份报告 + 一个目录页。

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

import html
import json
import re
import sys
from pathlib import Path

from lib import page, sheet, spec as spec_lib

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import figures  # noqa: E402
import ket      # noqa: E402  词汇默写栏目

REVIEW = HERE / "review"
SPECS = REVIEW / "specs"
DATA = REVIEW / "data"

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
        self.prevs = [s.strip() for s in (sp.get("prev") or "").split(",") if s.strip()]

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

def hero(r: Report) -> str:
    head = (f'第 {r.spec.get("page")} 页' if r.spec.get("page") else "")
    if r.spec.get("book"):
        head += f'《{r.spec.get("book")}》'
    # 「划线三段 110 词」是一节，不要在中间再断开
    part = " ".join(x for x in (r.spec.get("part"), f"{r.words} 词") if x)
    sub = ""
    for piece in (head, part, pretty_date(r.date)):
        if not piece:
            continue
        # 书名号 / 引号收尾后直接跟间隔号，中间不留空格
        sep = "" if not sub else ("· " if sub[-1] in "》」』”" else " · ")
        sub += sep + piece

    # 卷名里的最后一个数字描成主色（「超8 · Lesson 3」的 3）
    title = html.escape(r.spec.title)
    title = re.sub(r"(\d+)(?!.*\d)", r"<b>\1</b>", title, count=1)
    return (f'    <header class="hero">\n'
            f'      <span class="eyebrow">DAILY REVIEW · 打卡评价</span>\n'
            f'      <h1>{title}</h1>\n'
            f'      <p class="sub">{html.escape(sub)}</p>\n'
            f'    </header>\n')


def pretty_date(iso: str) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日" if m else (iso or "")


def score_box(r: Report) -> str:
    b = r.blocks.get("总评")
    lead = html.escape(b.head) if b else ""
    tip = joined(b.notes()) if b else ""

    bars = []
    got = dict(parse_pairs(r.blocks["评分"].head)) if "评分" in r.blocks else {}
    for name, full in DIMENSIONS:
        raw = got.get(name)
        if not raw:
            continue
        n = int(raw.split("/")[0])
        bars.append(
            f'        <div class="bar"><span class="nm">{name}</span>'
            f'<span class="track"><i class="fill" style="width:{round(n / full * 100)}%"></i></span>'
            f'<span class="val">{n}/{full}</span></div>'
        )

    return (f'    <section class="box score">\n'
            f'      <span class="num"><b>{r.score}</b><span>／100</span></span>\n'
            f'      <span class="say">\n'
            f'        <p class="lead">{lead}</p>\n'
            + (f'        <p class="tip">{rich(tip)}</p>\n' if tip else "")
            + f'      </span>\n'
            f'      <div class="bars" style="flex-basis:100%">\n'
            + "\n".join(bars) + "\n"
            f'      </div>\n'
            f'    </section>\n')


def parse_pairs(text: str) -> list[tuple[str, str]]:
    """「准确度=24/30 流利度=15/30」→ [(准确度, 24/30), …]

    lib/spec.py 的属性解析只认 ASCII 的 key=，中文 key 会整串留在 head 里 ——
    这是它有意为之（只解析骨架），各科自己解释。
    """
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"([^\s=]+)\s*=\s*([^\s]+)", text or "")]


def stats(r: Report) -> str:
    cells = [
        ("s1", f"{r.accuracy}%", f"读对 {r.correct}/{r.words} 词"),
        ("s2", str(r.wcpm), "每分钟正确词数"),
        ("s3", f"{round(r.duration)}<small>秒</small>", "读完全段"),
        ("s4", str(r.pause_count), "次停顿"),
    ]
    body = "\n".join(f'      <div class="stat {c}"><b>{v}</b><span>{html.escape(l)}</span></div>'
                     for c, v, l in cells)
    return ('    <h2 class="mini-h"><span>📊</span> 四个数字</h2>\n'
            f'    <div class="stats">\n{body}\n    </div>\n')


def compare(r: Report, others: dict[str, Report]) -> str:
    """和上一页比 / 三页放在一起看。

    四行数值全部算出来，spec 里只给趋势词（不给就用 +N / −N）。
    """
    b = r.blocks.get("对比")
    if not b or not r.prevs:
        return ""
    chain = [others[s] for s in r.prevs if s in others] + [r]
    if len(chain) < 2:
        return ""

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
        shown = " → ".join(f"<s>{v}</s>" for v in values[:-1]) + f" → {values[-1]}"
        out.append(f'      <div class="r"><span class="k">{name}</span>'
                   f'<span class="v">{shown}</span>'
                   f'<span class="d {cls}">{html.escape(str(tag))}</span></div>')

    note = joined(b.notes())
    icon, heading = ("📈", b.head) if len(chain) > 2 else ("↗️", b.head or "和上一页比")
    return (f'    <h2 class="mini-h"><span>{icon}</span> {html.escape(heading)}</h2>\n'
            f'    <section class="box cmp">\n' + "\n".join(out) + "\n"
            + (f'      <p class="sc-note" style="margin-top:4px">{rich(note)}</p>\n' if note else "")
            + f'    </section>\n')


def timeline(r: Report) -> str:
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
    legend = (f'      <div class="legend">\n'
              f'        <span><i style="background:var(--tl-speech)"></i>在读</span>\n'
              f'        <span><i style="background:var(--tl-end)"></i>句末停顿 · {counts["end"]} 次</span>\n'
              f'        <span><i style="background:var(--tl-long)"></i>句中长停 ≥0.8 秒 · {counts["long"]} 次</span>\n'
              f'        <span><i style="background:var(--tl-mid)"></i>句中短停 · {counts["mid"]} 次</span>\n'
              f'      </div>')
    note = joined(r.blocks["卡壳"].notes()) if "卡壳" in r.blocks else ""
    return (f'    <h2 class="mini-h"><span>⏱</span> 这 {round(r.duration)} 秒长什么样</h2>\n'
            f'    <section class="box tl">\n'
            + "\n".join("      " + l for l in svg.split("\n")) + "\n"
            + legend + "\n"
            + (f'      <p class="tl-note">{rich(note)}</p>\n' if note else "")
            + f'    </section>\n')


def auto_bounds(r: Report) -> list[float]:
    """从原文的句末标点推句末时刻。spec 没写 [句末] 时的兜底。"""
    ref = DATA / f"{r.slug}.ref.txt"
    if not (r.reading and ref.exists()):
        return []
    times = r.reading.get("alignment", {}).get("refTimes") or []
    words = re.findall(r"[A-Za-z0-9''\-]+[^\sA-Za-z0-9]*", ref.read_text(encoding="utf-8"))
    return [times[i] for i, w in enumerate(words)
            if i < len(times) and times[i] is not None and re.search(r"[.!?][\"']?$", w)]


def diffs(r: Report) -> str:
    """逐字比对。

    条目按「原文 / 实读」成对出现，缩进行是说明。用「识别成」代替「实读」
    表示这处转写不可信 —— 编号出 `?`，别让它长得像已经定案的。
    """
    b = r.blocks.get("比对")
    if not b:
        return ""

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
        out.append(
            f'      <div class="d{" doubt" if doubt else ""}">\n'
            f'        <span class="n">{num}</span>\n'
            f'        <span class="en"><span class="lbl">原文</span>{marked(it["ref"], "mark")}</span>\n'
            f'        <span class="en"><span class="lbl">{it["lbl"]}</span>{marked(it["read"], "ins")}</span>\n'
            + (f'        <span class="why">{rich(why)}</span>\n' if why else "")
            + f'      </div>'
        )
    # 抬头不写就自己数。存疑那条也算一处 —— 它同样是对不上的地方，
    # 只是判不准该算谁的，所以编号出 ? 而不是从计数里拿掉
    heading = b.head or f"逐字比对 · {len(items)} 处"
    return (f'    <h2 class="mini-h"><span>🔍</span> {html.escape(heading)}</h2>\n'
            f'    <div class="diff">\n\n' + "\n\n".join(out) + '\n\n    </div>\n')


def lines_block(r: Report, name: str, icon: str, default_head: str, cls: str = "text") -> str:
    """磕巴 / 亮点这类「几行内容 + 一段小字注」的区块。"""
    b = r.blocks.get(name)
    if not b:
        return ""
    body = [f'      <p class="{cls}" style="margin:0 0 8px">{marked(ln.strip(), "ins")}</p>'
            for ln in b.lines if ln.strip() and not ln[:1].isspace()]
    note = joined(b.notes())
    return (f'    <h2 class="mini-h"><span>{icon}</span> {html.escape(b.head or default_head)}</h2>\n'
            f'    <section class="box">\n' + "\n".join(body) + "\n"
            + (f'      <p class="note-soft">{rich(note)}</p>\n' if note else "")
            + f'    </section>\n')


def highlight(r: Report) -> str:
    """读得好的地方：主段是正文，缩进行是小字注。"""
    b = r.blocks.get("亮点")
    if not b:
        return ""
    mains = grouped([ln for ln in b.lines if ln.strip() and not ln[:1].isspace()])
    note = joined(b.notes())
    paras = "\n".join(f'      <p style="margin:0 0 6px">{rich(m)}</p>' for m in mains)
    return ('    <h2 class="mini-h"><span>🌟</span> 读得好的地方</h2>\n'
            '    <section class="box">\n'
            f'{paras}\n'
            + (f'      <p class="note-soft">{rich(note)}</p>\n' if note else "")
            + '    </section>\n')


def todos(r: Report) -> str:
    """下次试试这三件事。每条：一个 emoji 起头的标题行 + 缩进的说明行。"""
    b = r.blocks.get("三件事")
    if not b:
        return ""
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

    out = "\n".join(
        f'      <div class="t">\n'
        f'        <span class="ic">{html.escape(it["icon"])}</span>\n'
        f'        <span><p class="h">{rich(it["title"])}</p>\n'
        f'          <p class="d2">{rich(joined(it["desc"]))}</p></span>\n'
        f'      </div>' for it in items)
    return ('    <h2 class="mini-h"><span>✏️</span> 下次试试这三件事</h2>\n'
            f'    <div class="todo">\n{out}\n    </div>\n')


def slashes(r: Report) -> str:
    """画好斜线的版本 —— 按意群断句，一条斜线一口气。"""
    b = r.blocks.get("斜线")
    if not b:
        return ""
    # 斜线两边都要留空气 —— 它是「在这儿换口气」的记号，贴着字母会读成单词的一部分
    body = " <span class=\'sl\'>/</span>\n      ".join(
        html.escape(ln.strip()) for ln in b.lines if ln.strip() and not ln[:1].isspace())
    return ('    <h2 class="mini-h"><span>🪄</span> 画好斜线的版本</h2>\n'
            '    <section class="box">\n'
            f'      <p class="text" style="margin:0">{body}</p>\n'
            '    </section>\n')


def scales(r: Report) -> str:
    """三把尺子。三句 note 顺序固定：准确率 / WCPM / 断句语调。"""
    notes = grouped(r.blocks["尺子"].lines) if "尺子" in r.blocks else []
    while len(notes) < 3:
        notes.append("")
    prev_acc = None
    if r.prevs:
        prev_acc = getattr(r, "_prev_acc", None)
    return figures.block(r.accuracy, r.wcpm, r.naep, tuple(rich(n) for n in notes[:3]), prev_acc)


def how(r: Report) -> str:
    b = r.blocks.get("怎么来的")
    if not b:
        return ""
    paras = [f'      <p>{rich(para)}</p>' for para in grouped(b.lines)]
    return ('    <h2 class="mini-h"><span>📐</span> 分数是怎么来的</h2>\n'
            '    <section class="box how">\n' + "\n".join(paras) + "\n    </section>\n")


# ══════════════════════════════════════════════════════════════
# 组装
# ══════════════════════════════════════════════════════════════

def render(r: Report, others: dict[str, Report], out_dir: Path, pdf: bool) -> bool:
    fg, bg = figures.score_color(r.score)
    c = r.color_var

    body = (
        '<main class="wrap">\n'
        + hero(r)
        + score_box(r)
        + stats(r)
        + compare(r, others)
        + timeline(r)
        + diffs(r)
        + lines_block(r, "磕巴", "🌀", "磕巴（不计错，但能看出在想）")
        + highlight(r)
        + todos(r)
        + slashes(r)
        + scales(r)
        + how(r)
        + '    <a class="back" href="./">← 返回打卡评价</a>\n'
        + '    <p class="foot">打卡评价 · 每天的作业，一份成绩单 📋</p>\n'
        + '</main>'
    )

    desc = (f"{r.spec.get('book', '')}一段 {round(r.duration)} 秒朗读的逐字比对："
            f"读对 {r.correct}/{r.words} 个词，每分钟 {r.wcpm} 个正确词，"
            f"{r.pause_count} 次停顿，总分 {r.score} 分。")
    title = f"{r.title} 打卡评价"

    # 分类色和分数色按页注入。--read 是整页主色，--score 只给总分和四维条
    style = (f'<style>:root{{ --read:var(--c-{c}); --read-bg:var(--c-{c}-bg);'
             f' --score:{fg}; --score-bg:{bg}; }}</style>\n')

    out = page.write(
        out_dir / f"{r.slug}.html",
        page.render(
            title=title,
            description=desc,
            body=body,
            emoji="🎤",
            css=("review.css",),
            root="../..",
            noindex=True,          # 孩子的成绩单，不进搜索引擎
            extra_head=style,
        ),
    )
    print(f"    → review/{out.name}  （{r.accuracy}% · WCPM {r.wcpm} · {r.score} 分）")
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


def build_index(out_dir: Path, reports: list[Report], pdfs: dict[str, bool]) -> None:
    """目录页：按日期倒序分组，组内按分类顺序、再按 order。"""
    by_date: dict[str, list[Report]] = {}
    for r in reports:
        by_date.setdefault(r.date, []).append(r)

    cat_rank = {c: i for i, c in enumerate(CATS)}
    groups = []
    for date in sorted(by_date, reverse=True):
        rows = sorted(by_date[date], key=lambda x: (cat_rank.get(x.cat, 99), x.order))
        items = []
        for r in rows:
            fg, bg = figures.score_color(r.score)
            # 报告本身是网页（手机上看），PDF 只是想转发给别人时的附加件
            pdf_link = (f'<a class="pdf" href="{r.slug}.pdf">PDF</a>'
                        if pdfs.get(r.slug) else "")
            items.append(
                f'      <li style="--s:{fg};--sbg:{bg};--c:var(--c-{r.color_var});'
                f'--cbg:var(--c-{r.color_var}-bg)">\n'
                f'        <a class="main" href="{r.slug}.html">{html.escape(r.title)}'
                f'<small>{html.escape(r.sub)} · {r.accuracy}% · 每分钟 {r.wcpm} 词</small></a>\n'
                f'        <span class="meta"><span class="cat">{html.escape(r.cat)}</span>'
                f'<span class="sc">{r.score}</span>{pdf_link}</span>\n'
                f'      </li>')
        groups.append(f'    <h2 class="day">{pretty_date(date)}</h2>\n'
                      f'    <ul class="list">\n' + "\n".join(items) + "\n    </ul>")

    body = f"""<main class="wrap">
  <header class="hero">
    <a class="back" href="../../">‹ 学习小站</a>
    <h1>打卡评价</h1>
    <p class="sub">每天的朗读作业，一份能和下次比的成绩单 · 共 {len(reports)} 份</p>
  </header>
{chr(10).join(groups) if groups else '  <p class="empty">还没有报告 —— 用喂数据台跑一份录音，再往 specs/ 放一份 spec</p>'}
</main>"""

    page.write(
        out_dir / "index.html",
        page.render(
            title="打卡评价 · 英语",
            description="每天的朗读作业，一份能和下次比的成绩单：逐字比对、停顿地图、三把尺子上的位置。",
            body=body,
            emoji="🎤",
            css=("site.css", "review-index.css"),
            root="../..",
        ),
    )
    print(f"    → review/index.html  （{len(reports)} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    ket.build(dist, pdf=pdf)        # 词汇默写。放前面：打卡评价那段可能提前 return

    out_dir = dist / "review"
    specs = sorted(SPECS.glob("*.txt")) if SPECS.exists() else []
    if not specs:
        print("    · 打卡评价：specs/ 里还没有 spec，跳过")
        return

    reports = [Report(spec_lib.parse(p)) for p in specs]
    others = {r.slug: r for r in reports}

    # 三把尺子上要标出上一页的位置，得先把彼此认全
    for r in reports:
        if r.prevs and r.prevs[-1] in others:
            r._prev_acc = others[r.prevs[-1]].accuracy

    pdfs = {}
    for r in sorted(reports, key=lambda x: (x.date, x.order)):
        pdfs[r.slug] = render(r, others, out_dir, pdf)

    build_index(out_dir, reports, pdfs)
