"""英语 · 词汇默写 —— KET 核心词汇的 A4 默写卷（看中文写英文）。

从老站 ../english/ket/ 搬过来，格式一条没动（用户拍过板），改的只是地基：
Chrome 路径不再写死（走 lib/sheet.py 自动探测）、样式抽进 src/assets/ket.css、
版式抽进 src/templates/ket/sheet.html、目录页由脚本生成而不是手写 18 KB 的 index.html。

    storage/spec/english/ket/words/<NN>_<主题>.csv    词表（唯一输入，带 BOM）
    storage/spec/english/ket/selections/<名字>.txt    抽选卷 spec（跨主题挑词）
                    ↓
    dist/english/ket/<NN>_<主题>.html/.pdf   单主题默写卷
                     words_1[_answers].*     上册合集 01–12（默写 / 答案对照）
                     words_2[_answers].*     下册合集 13 起
                     <spec 名>[_answers].*   抽选卷
                     index.html              目录页

三个已定稿的格式决策（改动要用户同意）：
  · A4 两栏，一页 30 词；页眉标题 + 姓名/日期/得分，页脚词数 + 页码
  · 题型是「看中文写英文」：序号 + 中文释义 + 灰色词性提示 + 四线三格
  · 四线三格绿线红基线、总高 11mm —— 旋钮在 grid.css，别在这里改
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

WORDS = paths.spec("english", "ket", "words")
SELECTIONS = paths.spec("english", "ket", "selections")

PER_PAGE = 30        # 默写卷：2 栏 × 15 行。四线格 11mm + row-gap 20px 正好一页

# 答案对照版：竖排 ANS_GROUP 个一组、一行两组，按估算高度(px)切页
ANS_GROUP = 5
ANS_ROW_H, ANS_ROW_GAP = 20, 6      # 单行高、组内行距
ANS_BAND_GAP = 8                    # 组行上下留白（padding 3+3 + margin 2）
ANS_SEC_H, ANS_SEC_GAP = 26, 8      # 章节标题行
ANS_PAGE_H = 930                    # 一页能放多少 px 的内容
# 930 是量出来的，不是拍的：A4 1123px − .sheet 上下 padding 106 − 页眉 57
# − 页脚 25 = 934，留 4px 给 CI 上不同字体的行高差。
# 老站那份是 970，搬过来直接溢出（.sheet 的 padding 比老站 @page margin 大）。
# 验收标准：HTML 里 .sheet 的个数必须等于 PDF 的页数 —— 不等就是某页装不下，
# 被 Chrome 二次分页，打出来会夹半张空页。

# 合集分册：out_stem → 收录的主题编号范围。
# 上册 01–12 已定稿不再变动，新主题一律进下册。
VOLUMES = {
    "words_1": (1, 12),
    "words_2": (13, 99),
}

# 主题显示名。加新主题在这里加一条（key 去掉编号前缀）——
# 英文名太长会把页眉挤成两行，取个短名即可（见 personal_feelings 那条）。
TITLES = {
    "appliances": "Appliances 家电",
    "clothes_and_accessories": "Clothes and Accessories 服装与饰品",
    "colours": "Colours 颜色",
    "communication_and_technology": "Communication and Technology 通信与技术",
    "documents_and_texts": "Documents and Texts 文件和文本",
    "education": "Education 教育",
    "entertainment_and_media": "Entertainment and Media 娱乐和媒体",
    "family_and_friends": "Family and Friends 家人和朋友",
    "food_and_drink": "Food and Drink 食物和饮料",
    "health_medicine_and_exercise": "Health, Medicine and Exercise 健康、医药和锻炼",
    "hobbies_and_leisure": "Hobbies and Leisure 爱好和休闲",
    "house_and_home": "House and Home 房子和家",
    "measurements": "Measurements 计量",
    "personal_feelings_opinions_and_experiences": "Personal Feelings 个人感受、观点和经历",
    "places_buildings": "Places: Buildings 地点：建筑",
    "places_countryside": "Places: Countryside 地点：乡村",
    "places_town_and_city": "Places: Town and City 地点：城镇和城市",
    "services": "Services 服务",
    "shopping": "Shopping 购物",
    "sport": "Sport 体育运动",
    "the_natural_world": "The Natural World 自然世界",
    "time": "Time 时间",
    "travel_and_transport": "Travel and Transport 旅游和运输",
    "weather": "Weather 天气",
    "work_and_jobs": "Work and Jobs 工作与职业",
}


def topic_title(stem: str) -> str:
    """01_appliances → 01 Appliances 家电（编号是词汇书的板块序号）。"""
    m = re.match(r"^(\d+)_(.+)$", stem)
    topic_no, key = (m.group(1), m.group(2)) if m else ("", stem)
    title = TITLES.get(key, key.replace("_", " ").title())
    return f"{topic_no} {title}" if topic_no else title


def read_rows(src: Path) -> list[dict]:
    with open(src, encoding="utf-8-sig") as f:      # CSV 带 BOM（给 Excel 用）
        return list(csv.DictReader(f))


# ── 一个词位 ──────────────────────────────────────────────

def _no(row: dict, fallback: int) -> str:
    return (row.get("no", "").strip() or str(fallback)) + "."


def _item(row: dict, fallback: int) -> dict:
    """默写版一个词位：序号 + 中文 + 词性 + 四线三格。"""
    return {"kind": "item", "no": _no(row, fallback),
            "zh": row["meaning"], "pos": row["pos"].strip()}


def _ans_item(row: dict, fallback: int) -> dict:
    """答案版一个词位：序号 + 中文 + 词性 → 英文（靠右）+ 音标。"""
    return {"no": _no(row, fallback), "zh": row["meaning"],
            "pos": row["pos"].strip(), "en": row["word"],
            "ph": row["phonetic"].strip()}


PAD = {"kind": "pad"}


def _page(title: str, cells: list[dict], total: int, page_no: int,
          page_count: int, *, cls: str = "", info: str | None = None) -> str:
    if info is None:
        info = page.sheet_info("得分")
    return tmpl.body("ket/sheet.html", title=title, info=info, cls=cls,
                     cells=cells, total=total,
                     page_no=page_no, page_count=page_count)


def _write(out_dir: Path, stem: str, title: str, pages: list[str], pdf: bool) -> bool:
    out = page.write(
        out_dir / f"{stem}.html",
        page.render(
            title=title,
            body="\n".join(pages),
            emoji="🔤",
            css=("print.css", "grid.css", "ket.css"),
            root="../..",
            noindex=True,          # 默写卷不需要被搜索引擎收录
        ),
    )
    return bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))


# ── 成卷 ──────────────────────────────────────────────────

def _answer_doc(sections: list[tuple[str, list[dict]]], stem: str, title: str,
                out_dir: Path, pdf: bool) -> dict:
    """答案对照版：整组不跨页，章节标题也不落在页尾（后面至少跟一组）。"""
    blocks, total = [], 0        # blocks: (高度, cell, 是不是章节标题)
    for sec_title, rows in sections:
        total += len(rows)
        blocks.append((ANS_SEC_H + ANS_SEC_GAP,
                       {"kind": "ans-section", "title": sec_title}, True))
        items = [_ans_item(r, i) for i, r in enumerate(rows, 1)]
        groups = [items[i:i + ANS_GROUP] for i in range(0, len(items), ANS_GROUP)]
        for i in range(0, len(groups), 2):
            pair = groups[i:i + 2]
            n = max(len(g) for g in pair)
            blocks.append((n * ANS_ROW_H + (n - 1) * ANS_ROW_GAP + ANS_BAND_GAP,
                           {"kind": "band", "alt": (i // 2) % 2 == 1, "groups": pair},
                           False))

    paged, cur, used = [], [], 0
    for i, (h, cell, is_sec) in enumerate(blocks):
        need = h + (blocks[i + 1][0] if is_sec and i + 1 < len(blocks) else 0)
        if cur and used + need > ANS_PAGE_H:
            paged.append(cur)
            cur, used = [], 0
        cur.append(cell)
        used += h
    if cur:
        paged.append(cur)

    pages = [_page(title, items, total, p + 1, len(paged), cls=" compact", info="")
             for p, items in enumerate(paged)]
    return {"stem": stem, "title": title, "total": total, "pages": len(pages),
            "pdf": _write(out_dir, stem, title, pages, pdf)}


def _doc(sections: list[tuple[str, list[dict]]], stem: str, title: str,
         out_dir: Path, pdf: bool, answers: bool = False) -> dict:
    """把若干 (章节标题, rows) 连排成一份卷子。

    章节之间不分页；章节标题占一整行（2 个词位），起点不在行首时补空位，
    而且不让标题落在页面最后一行。题号沿用各章 CSV 里的 no。
    """
    if answers:
        return _answer_doc(sections, stem, title, out_dir, pdf)

    cells, total = [], 0          # cells: (占几个词位, html)
    for sec_title, rows in sections:
        total += len(rows)
        used = sum(s for s, _ in cells)
        if used % 2 == 1:                       # 补齐到行首
            cells.append((1, PAD))
            used += 1
        if used % PER_PAGE == PER_PAGE - 2:     # 标题别落在页面最后一行
            cells += [(1, PAD), (1, PAD)]
        cells.append((2, {"kind": "section", "title": sec_title}))
        cells += [(1, _item(r, i)) for i, r in enumerate(rows, 1)]

    paged, cur, used = [], [], 0
    for slots, cell in cells:
        if used + slots > PER_PAGE:
            paged.append(cur)
            cur, used = [], 0
        cur.append(cell)
        used += slots
    if cur:
        paged.append(cur)

    pages = [_page(title, items, total, p + 1, len(paged))
             for p, items in enumerate(paged)]
    return {"stem": stem, "title": title, "total": total, "pages": len(pages),
            "pdf": _write(out_dir, stem, title, pages, pdf)}


def _topic(src: Path, out_dir: Path, pdf: bool) -> dict:
    """单主题默写卷：没有章节标题，一页 30 词直接切。"""
    rows = read_rows(src)
    title = topic_title(src.stem) + " 默写"
    count = (len(rows) + PER_PAGE - 1) // PER_PAGE
    pages = [
        _page(title,
              [_item(r, p * PER_PAGE + 1 + i)
               for i, r in enumerate(rows[p * PER_PAGE:(p + 1) * PER_PAGE])],
              len(rows), p + 1, count)
        for p in range(count)
    ]
    return {"stem": src.stem, "title": title, "total": len(rows),
            "pages": count, "pdf": _write(out_dir, src.stem, title, pages, pdf)}


def _volume(stem: str, out_dir: Path, pdf: bool, answers: bool) -> dict | None:
    """一册合集：把该册范围内的主题连排。"""
    lo, hi = VOLUMES[stem]
    paths = [p for p in spec_lib.specs(WORDS, "[0-9]*_*.csv")
             if lo <= int(p.stem.split("_")[0]) <= hi]
    if not paths:
        return None
    nos = [int(p.stem.split("_")[0]) for p in paths]
    span = f"{min(nos):02d}–{max(nos):02d}"
    title = f"KET 核心词汇 {span} " + ("答案对照" if answers else "默写")
    return _doc([(topic_title(p.stem), read_rows(p)) for p in paths],
                stem + ("_answers" if answers else ""), title,
                out_dir, pdf, answers)


def _parse_nos(text: str) -> list[int]:
    """'1,2,6,13-16' → [1, 2, 6, 13, 14, 15, 16]（按书写顺序，不排序）"""
    nos = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            nos.extend(range(int(a), int(b) + 1))
        else:
            nos.append(int(part))
    return nos


def _selection(path: Path, out_dir: Path, pdf: bool, answers: bool) -> dict:
    """抽选卷：按 spec 从各主题挑词，章节标题和题号都沿用原主题。"""
    name, picks = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if name is None:
                name = line.lstrip("# ").strip()
            continue
        topic, _, nos = line.partition(":")
        picks.append((topic.strip(), _parse_nos(nos)))

    sections = []
    for topic, nos in picks:
        matches = spec_lib.specs(WORDS, f"{int(topic):02d}_*.csv")
        if not matches:
            spec_lib.die(f"{path.name}：找不到主题 {topic} 的词表")
        src = matches[0]
        by_no = {r["no"].strip(): r for r in read_rows(src)}
        rows = []
        for n in nos:
            row = by_no.get(str(n))
            if row is None:
                spec_lib.die(f"{path.name}：{src.name} 里没有第 {n} 号词")
            rows.append(row)
        sections.append((topic_title(src.stem), rows))

    title = (name or path.stem) + (" 答案对照" if answers else " 默写")
    return _doc(sections, path.stem + ("_answers" if answers else ""), title,
                out_dir, pdf, answers)


# ── 目录页 ────────────────────────────────────────────────

def _index(out_dir: Path, groups: list[tuple[str, list[dict]]]) -> None:
    total = sum(len(e) for _, e in groups)
    page.listing(
        out_dir,
        title="词汇默写 · 英语",
        description="KET 核心词汇的 A4 默写卷：看中文写英文，四线三格，点进去直接打印。",
        emoji="🔤",
        h1="词汇默写",
        sub=f"KET 核心词 · 看中文写英文 · 共 {total} 份",
        # 空的那节整节不出（没有抽选卷时不该留一个空标题）
        sections=[(name, [{"href": f'{e["stem"]}.html',
                           "label": e["title"],
                           "small": f'{e["total"]} 词 · {e["pages"]} 页',
                           "pdf": f'{e["stem"]}.pdf' if e["pdf"] else None}
                          for e in entries])
                  for name, entries in groups if entries],
        accent="english",
    )
    print(f"    → ket/index.html  （{total} 份）")


def build(dist: Path, pdf: bool = False) -> None:
    """dist 是 dist/english/。"""
    if not WORDS.exists():
        print("    · 词汇默写：ket/words/ 里还没有词表，跳过")
        return

    out_dir = dist / "ket"
    topics = [_topic(p, out_dir, pdf) for p in spec_lib.specs(WORDS, "[0-9]*_*.csv")]

    volumes = []
    for stem in VOLUMES:
        for answers in (False, True):
            got = _volume(stem, out_dir, pdf, answers)
            if got:
                volumes.append(got)

    picks = []
    for path in spec_lib.specs(SELECTIONS):
        picks += [_selection(path, out_dir, pdf, False),
                  _selection(path, out_dir, pdf, True)]

    n_pdf = sum(1 for e in topics + volumes + picks if e["pdf"])
    print(f"    → ket/  （{len(topics)} 个主题 · {len(volumes)} 份合集 · "
          f"{len(picks)} 份抽选卷" + (f" · {n_pdf} 份 PDF）" if pdf else "）"))

    _index(out_dir, [("合集", volumes), ("抽选卷", picks), ("分主题", topics)])
