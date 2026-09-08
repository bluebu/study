"""语文 · 背诵单 —— 把要背的那段课文切成块，四天四轮背下来。

spec 在 storage/spec/chinese/recite/<课号>.txt，产物落在 dist/chinese/recite/：

    <课号>.html / .pdf   一页 A4，贴在书桌上或夹在语文书里
    index.html           目录页

**背诵慢多半不是记性问题，是方法**：多数孩子在「重读」，而重读几乎不产生
记忆。这张单子把四条真起作用的做法印在纸上，家长照着走：

1. **切块** —— 9 岁的工作记忆一次装 4±1 个单位，所以一段切成 4 块上下，
   一块一行。连的时候只连**相邻两块**，别每次从头
2. **提取练习** —— 读一遍就盖住说一遍。说不出来才看一眼；「难受」正是
   记忆在形成，看着书顺下来那种流利是假的
3. **提示递减** —— 三轮：全文 → 只看首字 → 白纸。每块右边三个格子，
   一轮打一个勾，孩子自己看得见进度
4. **间隔重复** —— `plan: 1,2,4,7` 是打卡的第几天。分四天、睡前过一遍
   （记忆在睡眠里固化），第二天早上那一遍最能暴露真实水平

判定「掌握」的四条判据在页底，**缺一条都不算**：流利（卡壳 0 次）、
准确（0 处错漏）、**中间切入**（随口报一块能接下一块）、保持（隔天再过）。
第三条最能识破假掌握 —— 只会顺流背的孩子从头能背，报中间那句就接不上，
说明他记的是一条声音链、不是内容。抽查点脚本自动挑，见 `_probes()`。

spec 的形状：一个区块 = 一个自然段，区块内**一行一块**（`原文 | 关键词`）。
**原文照课本逐字抄、标点也照书**；切块和关键词是判断（`make textbook`
核的是抽查单，这里的原文得自己拿书对 —— 印错一个字，孩子就背错一个字）。
"""

from __future__ import annotations

from pathlib import Path

from lib import page, paths, sheet, spec as spec_lib, tmpl

SPECS = paths.spec("chinese", "recite")

DEFAULTS = {"title": "背诵单", "plan": "1,2,4,7"}

ROUNDS = 3        # 提示递减三轮：全文 → 只看首字 → 白纸
PROBES = 3        # 抽查点：随口报一块，孩子接下一块


def _sections(sp: spec_lib.Spec) -> list[dict]:
    """区块 → 段，段内一行一块。块号跨段连续编（抽查点要按块号说话）。"""
    out, no = [], 0
    for b in sp.blocks:
        chunks = []
        for line in b.lines:
            text, _, key = line.strip().partition("|")
            text = text.strip()
            if not text:
                continue
            no += 1
            chunks.append({
                "no": no,
                "text": text,
                "first": text[0],          # 第 2 轮的提示：只给首字
                "key": key.strip(),        # 第 3 轮的提示：关键词
                "rounds": ROUNDS,
            })
        if chunks:
            out.append({"name": b.name, "chunks": chunks})

    if not out:
        spec_lib.die(f"{sp.path.name} 里没有任何 [自然段] 区块")
    return out


def _probes(sections: list[dict]) -> list[dict]:
    """抽查点：家长随口报一块，孩子接下一块。

    **跳过每段的第一块** —— 那是自然起点，谁都会背，测不出东西；也跳过
    全篇最后一块（没有下一块可接）。剩下的均匀挑 PROBES 个。
    """
    flat = [c for sec in sections for c in sec["chunks"]]
    starts = {sec["chunks"][0]["no"] for sec in sections}
    cand = [c for c in flat[:-1] if c["no"] not in starts]
    if not cand:
        return []

    step = max(1, round(len(cand) / PROBES))
    picked = cand[::step][:PROBES]
    nxt = {c["no"]: flat[i + 1] for i, c in enumerate(flat[:-1])}
    return [{"no": c["no"], "text": c["text"],
             "next_no": nxt[c["no"]]["no"], "next_text": nxt[c["no"]]["text"]}
            for c in picked]


def _plan(sp: spec_lib.Spec) -> list[dict]:
    """`plan: 1,2,4,7` → 四个打卡格。间隔递增，不是天天练。"""
    raw = sp.get("plan", DEFAULTS["plan"])
    days = []
    for part in raw.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            spec_lib.die(f"{sp.path.name}：plan 要写成天数，像 1,2,4,7，"
                         f"现在有一项是 {part!r}")
        days.append(int(part))
    if not days:
        spec_lib.die(f"{sp.path.name}：plan 是空的")
    return [{"day": d, "label": f"第 {d} 天"} for d in days]


def _render(sp: spec_lib.Spec, out_dir: Path, pdf: bool) -> tuple[bool, dict]:
    sections = _sections(sp)
    total = sum(len(s["chunks"]) for s in sections)

    heading = sp.get("title", DEFAULTS["title"])
    body = tmpl.body(
        "recite/sheet.html",
        heading=heading,
        sub=sp.get("range", ""),
        info=page.sheet_info("", show=True),
        require=sp.get("require", ""),
        sections=sections,
        probes=_probes(sections),
        plan=_plan(sp),
        total=total,
        tally=f"{len(sections)} 段 / {total} 块",
    )

    out = page.write(
        out_dir / f"{sp.path.stem}.html",
        page.render(
            title=f"{heading}　{sp.get('range', '')}".strip(),
            body=body,
            emoji="🎯",
            css=("print.css", "recite.css"),
            root="../..",
            noindex=True,          # 课文原文，不需要被搜索引擎收录
        ),
    )
    print(f"    → recite/{out.name}  （{len(sections)} 段 / {total} 块）")
    ok = bool(pdf) and sheet.to_pdf(out, out.with_suffix(".pdf"))
    return ok, {"sections": len(sections), "chunks": total}


def _index(out_dir: Path, entries: list[dict]) -> None:
    page.listing(
        out_dir,
        title="背诵单 · 语文",
        description="要背的那段课文切成块，三轮提示递减、四天间隔打卡，页底四条判据一眼判定会没会。",
        emoji="🎯",
        h1="背诵单",
        sub=f"切块背 · 隔天再测 · 共 {len(entries)} 份",
        sections=[(None, entries)],
        empty="还没有背诵单 —— 往 storage/spec/chinese/recite/ 放一份 spec",
        accent="chinese",
    )
    print(f"    → recite/index.html  （{len(entries)} 份）")


def build_recite(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "recite"
    specs = spec_lib.specs(SPECS)
    if not specs:
        print("    · 背诵单：storage/spec/chinese/recite/ 里还没有 spec，跳过")
        return

    entries = []
    for path in specs:
        sp = spec_lib.parse(path)
        pdf_ok, n = _render(sp, out_dir, pdf)
        entries.append({
            "href": f"{path.stem}.html",
            "label": sp.get("range", path.stem),
            "small": f"{n['sections']} 段 · {n['chunks']} 块 · 四天四轮",
            "pdf": f"{path.stem}.pdf" if pdf_ok else None,
        })

    _index(out_dir, entries)
