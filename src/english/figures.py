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
"""

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
    """准确率标尺：88%–100%，三档分区。

    字号按 viewBox 单位给：整张图在手机上会被压到 ~310px 宽（缩放约 0.31），
    32 号字落地才 10px 出头 —— 别再往小调。
    """
    lo, hi, W = 88.0, 100.0, 1000.0
    x = lambda v: round((v - lo) / (hi - lo) * W, 1)
    y, h = 34, 64
    s = [f'<svg viewBox="0 -32 {W:.0f} 240" role="img" '
         f'aria-label="准确率 {acc}% 落在 Fountas &amp; Pinnell 的哪一档">']
    for a, b, fill, name in [(lo, 95, 'var(--sc-hard)', '偏难'),
                             (95, 98, 'var(--sc-inst)', '要带一带'),
                             (98, hi, 'var(--sc-indep)', '能自己读')]:
        s.append(f'<rect x="{x(a)}" y="{y}" width="{x(b)-x(a)}" height="{h}" fill="{fill}"/>')
        s.append(f'<text x="{(x(a)+x(b))/2}" y="{y+h/2+11}" font-size="32" fill="var(--ink)" '
                 f'text-anchor="middle" opacity=".7">{name}</text>')
    s.append(f'<rect x="0" y="{y}" width="{W:.0f}" height="{h}" rx="10" fill="none" '
             f'stroke="var(--line)" stroke-width="2"/>')
    for v in (95, 98):
        s.append(f'<line x1="{x(v)}" y1="{y}" x2="{x(v)}" y2="{y+h}" stroke="var(--card)" stroke-width="4"/>')
        s.append(f'<text x="{x(v)}" y="{y+h+34}" font-size="28" fill="var(--ink-soft)" '
                 f'text-anchor="middle">{v}%</text>')
    if prev is not None:
        s.append(f'<circle cx="{x(prev)}" cy="{y+h+64}" r="9" fill="none" '
                 f'stroke="var(--ink-soft)" stroke-width="3"/>')
        s.append(f'<text x="{x(prev)}" y="{y+h+112}" font-size="28" fill="var(--ink-soft)" '
                 f'text-anchor="middle">上一页 {prev}%</text>')
    s.append(f'<path d="M{x(acc)} {y-4} l-13 -18 h26 z" fill="var(--read)"/>')
    s.append(f'<text x="{x(acc)}" y="{y-34}" font-size="36" font-weight="700" fill="var(--read)" '
             f'text-anchor="middle">本页 {acc}%</text>')
    s.append('</svg>')
    return '\n'.join(s)


def wcpm_svg(wcpm):
    """WCPM 标尺：各年级秋季 10–90 百分位带 + 本次位置。"""
    W, GUT, MAX = 1000.0, 176.0, 190.0
    x = lambda v: round(GUT + v / MAX * (W - GUT), 1)
    rows, rh, gap, top = list(ORF_FALL.items()), 44, 16, 34
    bottom = top + len(rows) * (rh + gap) - gap
    s = [f'<svg viewBox="0 -32 {W:.0f} {bottom+212:.0f}" role="img" '
         f'aria-label="每分钟正确词数 {wcpm} 与美国母语学生各年级秋季常模的比较">']
    for i, (grade, (p10, p25, p50, p75, p90)) in enumerate(rows):
        yy = top + i * (rh + gap)
        s.append(f'<text x="{GUT-18}" y="{yy+rh/2+11}" font-size="32" fill="var(--ink-soft)" '
                 f'text-anchor="end">{grade}</text>')
        s.append(f'<rect x="{x(p10)}" y="{yy+11}" width="{x(p90)-x(p10)}" height="{rh-22}" rx="6" '
                 f'fill="var(--sc-band1)"/>')
        s.append(f'<rect x="{x(p25)}" y="{yy}" width="{x(p75)-x(p25)}" height="{rh}" rx="8" '
                 f'fill="var(--sc-band2)"/>')
        s.append(f'<line x1="{x(p50)}" y1="{yy-5}" x2="{x(p50)}" y2="{yy+rh+5}" '
                 f'stroke="var(--sc-mid)" stroke-width="5"/>')
    s.append(f'<line x1="{x(wcpm)}" y1="6" x2="{x(wcpm)}" y2="{bottom+8}" stroke="var(--tl-long)" '
             f'stroke-width="4" stroke-dasharray="9 7"/>')
    s.append(f'<text x="{x(wcpm)}" y="-4" font-size="36" font-weight="700" fill="var(--tl-long)" '
             f'text-anchor="middle">本页 {wcpm}</text>')
    ax = bottom + 20
    s.append(f'<line x1="{GUT}" y1="{ax}" x2="{W:.0f}" y2="{ax}" stroke="var(--line)" stroke-width="2"/>')
    for v in (0, 50, 100, 150):
        s.append(f'<line x1="{x(v)}" y1="{ax}" x2="{x(v)}" y2="{ax+9}" stroke="var(--ink-soft)" stroke-width="2"/>')
        s.append(f'<text x="{x(v)}" y="{ax+40}" font-size="28" fill="var(--ink-soft)" text-anchor="middle">{v}</text>')
    s.append(f'<text x="{W:.0f}" y="{ax+40}" font-size="26" fill="var(--ink-soft)" text-anchor="end">WCPM</text>')
    l1, l2 = ax + 86, ax + 138
    s.append(f'<rect x="{GUT}" y="{l1-23}" width="48" height="25" rx="6" fill="var(--sc-band2)"/>')
    s.append(f'<text x="{GUT+66}" y="{l1}" font-size="28" fill="var(--ink-soft)">中间一半 · 25–75 百分位</text>')
    s.append(f'<line x1="{GUT+22}" y1="{l2-27}" x2="{GUT+22}" y2="{l2+4}" stroke="var(--sc-mid)" stroke-width="5"/>')
    s.append(f'<text x="{GUT+66}" y="{l2}" font-size="28" fill="var(--ink-soft)">一半人在这条线上 · 50 百分位</text>')
    s.append('</svg>')
    return '\n'.join(s)


def naep_html(level):
    out = ['      <div class="naep">']
    for lv, desc in NAEP:
        cls = ' now' if lv == level else ''
        tag = '<span class="you">在这里</span>' if lv == level else ''
        out.append(f'        <div class="nv{cls}"><span class="lv">{lv}</span>'
                   f'<span class="ds">{desc}</span>{tag}</div>')
    out.append('      </div>')
    return '\n'.join(out)


def block(acc, wcpm, level, notes, prev_acc=None):
    """notes = (准确率一句话, WCPM 一句话, NAEP 一句话)"""
    ind = lambda svg: '\n'.join('      ' + l for l in svg.split('\n'))
    return f"""    <h2 class="mini-h"><span>📍</span> 三把尺子上的位置</h2>
    <section class="box scales">

      <p class="sc-h">准确率 · Fountas &amp; Pinnell 分档</p>
{ind(accuracy_svg(acc, prev_acc))}
      <p class="sc-note">{notes[0]}</p>

      <p class="sc-h sc-sep">每分钟正确词数 · Hasbrouck &amp; Tindal 2017 秋季常模</p>
{ind(wcpm_svg(wcpm))}
      <p class="sc-note">{notes[1]}</p>

      <p class="sc-h sc-sep">断句语调 · NAEP 朗读流利度 4 级</p>
{naep_html(level)}
      <p class="sc-note">{notes[2]}</p>

    </section>
"""


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
    out = [f'<rect x="0" y="{TOP}" width="{W:.0f}" height="{H:.0f}" rx="8" fill="var(--tl-speech)"/>']
    for p in P:
        k = kind(p); counts[k] += 1
        w = max(x(p['end']) - x(p['start']), 1.4)
        out.append(f'<rect x="{x(p["start"])}" y="{TOP}" width="{w}" height="{H:.0f}" fill="var(--tl-{k})"/>')
    out.append(f'<rect x="0" y="{TOP}" width="{W:.0f}" height="{H:.0f}" rx="8" fill="none" '
               f'stroke="var(--line)" stroke-width="1.5"/>')
    step = 10 if D <= 120 else 20 if D <= 300 else 60   # 长录音刻度放宽，否则末尾两个标签会叠在一起
    ticks = list(range(0, int(D) + 1, step))
    for t in ticks:
        anchor = 'start' if t == ticks[0] else 'end' if t == ticks[-1] else 'middle'
        out.append(f'<line x1="{x(t)}" y1="{TOP+H}" x2="{x(t)}" y2="{TOP+H+5}" stroke="var(--ink-soft)" stroke-width="1.4"/>')
        out.append(f'<text x="{x(t)}" y="{TOP+H+20}" font-size="15" fill="var(--ink-soft)" text-anchor="{anchor}">{t}s</text>')
    for a, b, label in stalls:
        out.append(f'<path d="M{x(a)} {TOP-8} L{x(a)} {TOP-14} L{x(b)} {TOP-14} L{x(b)} {TOP-8}" '
                   f'fill="none" stroke="var(--tl-long)" stroke-width="2"/>')
        out.append(f'<text x="{(x(a)+x(b))/2}" y="{TOP-20}" font-size="16" font-weight="700" '
                   f'fill="var(--tl-long)" text-anchor="middle">{label}</text>')
    svg = (f'<svg viewBox="0 -4 {W:.0f} {TOP+H+28:.0f}" role="img" aria-label="{int(D)} 秒朗读的停顿分布：'
           f'绿色是发声，蓝色是句末停顿，橙色和灰色是句中停顿">\n'
           + ''.join(f'  {s}\n' for s in out) + '</svg>')
    return svg, counts


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
