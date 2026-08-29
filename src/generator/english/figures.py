#!/usr/bin/env python3
"""报告里的图：停顿地图 + 「三把尺子上的位置」（准确率 / WCPM 常模 / NAEP 断句）。

从老站 ../english/review/tools/figures.py 搬过来，**三组常模数值一个都没动**。
它们来自一手来源，改动前先回去核：

  · Fountas & Pinnell Benchmark Assessment System 1, p.40（Heinemann 官方）
    L–N 级及以上：≥98% 独立 / 95–97% 教学 / <95% 偏难（A–K 级另一套：95–100 / 90–94）
  · Hasbrouck & Tindal (2017) Technical Report #1702, Table 4「Compiled ORF Norms 2017」
    存的是**秋季**一列，按录音季节换
  · NAEP 2002 Special Study of Oral Reading，朗读流利度 4 级量表

颜色一律走 CSS 变量（`var(--sc-hard)` 这些定义在 src/assets/palette.css），
SVG 里不写死任何色值 —— 换色只改色板一处。

用法：import 后调 block(...) / timeline_svg(...)，返回可直接塞进报告页的 HTML 片段。
标记（那些 <svg> / <rect> / <text>）全在 `src/templates/figures/` 下，
**这个文件只算坐标** —— 换版式改模板，改常模改下面那两张表。
"""

from lib import tmpl

# Hasbrouck & Tindal 2017 · Table 4 · 秋季（10 / 25 / 50 / 75 / 90 百分位）
ORF_FALL = {
    "二年级": (23, 36, 50, 84, 111),
    "三年级": (40, 59, 83, 104, 134),
    "四年级": (60, 75, 94, 125, 153),
    "五年级": (64, 87, 121, 153, 179),
}

NAEP = [
    (4, "整句成组读，有语调、有表情"),
    (3, "三四个词一组，断句基本合在意思上"),
    (2, "两个词一组，偶尔三四个，还没什么语调"),
    (1, "一个词一个词往外蹦"),
]


def accuracy_svg(acc, prev=None):
    """准确率标尺：88%–100%，三档分区。标记在 templates/figures/accuracy.svg。

    档位分界（95 / 98）来自 Fountas & Pinnell，见本文件顶部的出处。
    """
    lo, hi, W = 88.0, 100.0, 1000.0
    x = lambda v: round((v - lo) / (hi - lo) * W, 1)
    y, h = 34, 64
    return tmpl.render(
        "figures/accuracy.svg",
        acc=acc, W=f"{W:.0f}", y=y, h=h, y2=y + h,
        zones=[{"x": x(a), "w": x(b) - x(a), "mid": (x(a) + x(b)) / 2,
                "ty": y + h / 2 + 11, "fill": fill, "name": name}
               for a, b, fill, name in [(lo, 95, "var(--sc-hard)", "偏难"),
                                        (95, 98, "var(--sc-inst)", "要带一带"),
                                        (98, hi, "var(--sc-indep)", "能自己读")]],
        ticks=[{"x": x(v), "v": v, "ty": y + h + 34} for v in (95, 98)],
        prev=None if prev is None else
             {"x": x(prev), "cy": y + h + 64, "ty": y + h + 112, "v": prev},
        mark={"x": x(acc), "y": y - 4, "ty": y - 34},
    ).rstrip("\n")


def wcpm_svg(wcpm):
    """WCPM 标尺：各年级秋季 10–90 百分位带 + 本次位置。

    标记在 templates/figures/wcpm.svg，这儿只算坐标。
    常模数值在 ORF_FALL（Hasbrouck & Tindal 2017 Table 4 秋季列），别动。
    """
    W, GUT, MAX = 1000.0, 176.0, 190.0
    x = lambda v: round(GUT + v / MAX * (W - GUT), 1)
    rows, rh, gap, top = list(ORF_FALL.items()), 44, 16, 34
    bottom = top + len(rows) * (rh + gap) - gap
    ax = bottom + 20
    l1, l2 = ax + 86, ax + 138

    grades = []
    for i, (grade, (p10, p25, p50, p75, p90)) in enumerate(rows):
        yy = top + i * (rh + gap)
        grades.append({
            "grade": grade, "y": yy, "ty": yy + rh / 2 + 11,
            "x10": x(p10), "w10": x(p90) - x(p10), "y_band1": yy + 11, "h_band1": rh - 22,
            "x25": x(p25), "w25": x(p75) - x(p25),
            "x50": x(p50), "y_mid1": yy - 5, "y_mid2": yy + rh + 5,
        })

    return tmpl.render(
        "figures/wcpm.svg",
        wcpm=wcpm, W=f"{W:.0f}", view_h=f"{bottom + 212:.0f}",
        GUT=GUT, gut_label=GUT - 18, rh=rh,
        grades=grades,
        now={"x": x(wcpm), "y2": bottom + 8},
        ax=ax, ax9=ax + 9, ax40=ax + 40,
        ticks=[{"x": x(v), "v": v} for v in (0, 50, 100, 150)],
        lg={"band_y": l1 - 23, "text_x": GUT + 66, "l1": l1, "l2": l2,
            "tick_x": GUT + 22, "tick_y1": l2 - 27, "tick_y2": l2 + 4},
    ).rstrip("\n")


def block(acc, wcpm, level, notes, prev_acc=None):
    """三把尺子整块。notes = (准确率一句话, WCPM 一句话, NAEP 一句话)，顺序固定。"""
    return tmpl.render(
        "figures/scales.html",
        accuracy_svg=accuracy_svg(acc, prev_acc),
        wcpm_svg=wcpm_svg(wcpm),
        naep=[{"level": lv, "desc": desc, "now": lv == level} for lv, desc in NAEP],
        notes=notes,
    )


def timeline_svg(data, bounds, stalls):
    """停顿地图：83~86 秒里每一次歇气。

    data   = analyze.py 的输出（dict）
    bounds = 原文真正的句末 / 段落切换时刻，用来区分「该停的」和「断在句子中间的」
    stalls = [(起, 止, 标注)] 想额外圈出来的大卡壳
    """
    D, P = data['duration'], data['pauses']
    W, H, TOP = 1000.0, 40.0, 26.0
    x = lambda t: round(t / D * W, 2)

    def kind(p):
        if any(p['start'] - .6 <= b <= p['end'] + .6 for b in bounds):
            return 'end'
        return 'long' if p['dur'] >= .8 else 'mid'

    counts = {'end': 0, 'long': 0, 'mid': 0}
    pauses = []
    for p in P:
        k = kind(p); counts[k] += 1
        pauses.append({"x": x(p["start"]), "kind": k,
                       # 最窄 1.4：再细就看不见了，一次歇气该在图上留下痕迹
                       "w": max(x(p["end"]) - x(p["start"]), 1.4)})

    step = 10 if D <= 120 else 20 if D <= 300 else 60   # 长录音刻度放宽，否则末尾两个标签会叠在一起
    tk = list(range(0, int(D) + 1, step))

    # 卡壳标签排成一行，挤不下的往上错一行 —— 长录音里两处卡壳常常挨得很近
    # （p70-72 的 47.3-52.7 和 52.7-58.4 只隔 0 秒），标签叠在一起就是一团看不清的字。
    # 只有真挤到了才多开一行，单行时 viewBox 和原来逐字节一致。
    y_label = TOP - 20
    rows, marks = [], []
    for a, b, label in sorted(stalls):
        x1, x2 = x(a), x(b)
        mid = (x1 + x2) / 2
        # font-size 16 的粗体：中文一个字约 16 个单位，数字和拉丁字母约 8.5
        half = sum(16.0 if ord(c) > 0x2E80 else 8.5 for c in label) / 2
        r = 0
        while r < len(rows) and rows[r] > mid - half - 8:
            r += 1
        (rows.append(mid + half) if r == len(rows) else rows.__setitem__(r, mid + half))
        # 文字居中在括号上，但两头夹住不许伸出 viewBox —— 伸出去会被 SVG 裁掉半行字
        # （p70-72 末尾那处卡壳一直到 376 秒，标签中心几乎贴着右边）
        tx = mid if half * 2 + 4 > W else min(max(mid, half + 2), W - half - 2)
        marks.append({"x1": x1, "x2": x2, "mid": round(tx, 2), "label": label,
                      "y": y_label - r * 20})
    extra = max(len(rows) - 1, 0) * 20

    svg = tmpl.render(
        "figures/timeline.svg",
        W=f"{W:.0f}", H=f"{H:.0f}", TOP=TOP,
        vb_top=f"{-4 - extra:.0f}", vb_h=f"{TOP + H + 28 + extra:.0f}",
        seconds=int(D),
        pauses=pauses,
        base=TOP + H, base5=TOP + H + 5, base20=TOP + H + 20,
        ticks=[{"x": x(t), "v": t,
                "anchor": "start" if t == tk[0] else "end" if t == tk[-1] else "middle"}
               for t in tk],
        stalls=marks,
        y_bracket_lo=TOP - 8, y_bracket_hi=TOP - 14,
    ).rstrip("\n")
    return svg, counts


# ── 趋势：一条随时间的折线 ──────────────────────────────────
# 数据来自 storage/result/english/review.csv（result 层），不是从 spec 现算的。

def trend_svg(points, lo, hi, ticks, unit="", color="var(--c-read)"):
    """一条随时间的折线。points = [(标签, 数值), ...]，按时间顺序给。

    x **等距**排开，不按真实日期间距 —— 朗读不是每天都有，按日期排会挤成一堆，
    而且同一天读两页就重叠了（p68 / p69 就是同一天）。标签写页码，日期在下面的表里。
    y 线性映射到 [lo, hi]，超出范围的夹住（免得一次异常把整张图压平）。
    字号按 viewBox 单位给：整张图在手机上会被压到 ~330px 宽，别再往小调。
    """
    if len(points) < 2:
        return ""
    # PAD 是右侧留白：末点的 x 标签 text-anchor=middle，留少了会伸出 viewBox 被裁掉
    W, GUT, TOP, H, PAD = 1000.0, 96.0, 60.0, 300.0, 80.0
    n, bot = len(points), TOP + H
    x = lambda i: round(GUT + i * (W - GUT - PAD) / (n - 1), 1)
    y = lambda v: round(TOP + (1 - (min(max(v, lo), hi) - lo) / (hi - lo)) * H, 1)

    return tmpl.render(
        "figures/trend.svg",
        W=f"{W:.0f}", view_h=f"{bot + 96:.0f}", GUT=GUT, right=f"{W - PAD:.0f}",
        bot=bot, label_x=GUT - 16, label_y=bot + 44, unit_y=bot + 88,
        n=n, unit=unit, color=color,
        first=points[0][1], last=points[-1][1],
        ticks=[{"y": y(v), "ty": y(v) + 10, "v": v} for v in ticks],
        path=" ".join(f"{'M' if i == 0 else 'L'}{x(i)} {y(v)}"
                      for i, (_, v) in enumerate(points)),
        points=[{"x": x(i), "y": y(v), "vy": y(v) - 26, "v": v, "label": label}
                for i, (label, v) in enumerate(points)],
    ).rstrip("\n")


# ── 分数色：越差越红 ────────────────────────────────────────────
# 五个锚点，中间线性插值。和分类色是两回事：
#   分类色说「这是哪一类」，分数色说「做得怎么样」，同一张卡上各管各的。
SCORE_STOPS = [
    (40, (0xD2, 0x68, 0x5F)),   # 红   吃力
    (55, (0xDE, 0x8A, 0x45)),   # 橙   要补
    (70, (0xD9, 0xA7, 0x27)),   # 金   一般
    (82, (0x8F, 0xAE, 0x49)),   # 黄绿 不错
    (92, (0x4F, 0xA9, 0x7A)),   # 绿   很好
]
PAPER = (0xFF, 0xFD, 0xF8)      # 底色，用来调出浅色版


def score_color(score, tint=0.86):
    """分数 → (前景色, 浅底色)。分数可以是 0–100 的数，也可以是 None/'-'。"""
    if score is None or score == "-":
        return "#9A8C7C", "rgba(120,104,84,.10)"
    v = float(score)
    lo, hi = SCORE_STOPS[0], SCORE_STOPS[-1]
    if v <= lo[0]:
        rgb = lo[1]
    elif v >= hi[0]:
        rgb = hi[1]
    else:
        for (a, ca), (b, cb) in zip(SCORE_STOPS, SCORE_STOPS[1:]):
            if a <= v <= b:
                t = (v - a) / (b - a)
                rgb = tuple(round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3))
                break
    fg = "#%02X%02X%02X" % rgb
    bg = "#%02X%02X%02X" % tuple(round(rgb[i] + (PAPER[i] - rgb[i]) * tint) for i in range(3))
    return fg, bg
