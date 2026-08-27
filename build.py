#!/usr/bin/env python3
"""构建整站：src/ → dist/

    python3 build.py            只出 HTML
    python3 build.py --pdf      顺带把打印单导成 PDF
    python3 build.py --keep     不清空 dist/（默认每次全新构建）

dist/ 不进 git —— 本地靠这个脚本出，线上靠 .github/workflows/pages.yml
在部署时跑同一个脚本。所以「本地能出」就等于「线上能出」。
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
SRC = ROOT / "src"
DIST = ROOT / "dist"

sys.path.insert(0, str(ROOT))
from lib import page  # noqa: E402

CST = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════
# 站点地图：加科目 / 加栏目，只改这里
#
#   state:  "ready" 能点进去   |   "soon" 灰显待做
# ══════════════════════════════════════════════════════════════
SUBJECTS = [
    {
        "key": "chinese",
        "name": "语文",
        "emoji": "📖",
        "note": "生字词、背诵、抽查，都是能直接打印的 A4 单子",
        "sections": [
            {"name": "今日练习", "desc": "看拼音写汉字",       "href": "practice/", "state": "ready"},
            {"name": "朗读打卡", "desc": "大字课文 + 打卡圈",   "href": "recite/",   "state": "soon"},
            {"name": "抽查单",   "desc": "一课一张，家长照着问", "href": "check/",    "state": "soon"},
            {"name": "要求总表", "desc": "哪篇要背、哪首要默写", "href": "outline/",  "state": "soon"},
        ],
    },
    {
        "key": "english",
        "name": "英语",
        "emoji": "🔤",
        "note": "对标美国本土语法体系，不教中国式五大句型",
        "sections": [
            {"name": "语法小手册", "desc": "颜色教成分 + 点读",   "href": "grammar/",  "state": "soon"},
            {"name": "词汇默写",   "desc": "KET 核心词四线三格", "href": "ket/",      "state": "ready"},
            {"name": "每日打卡",   "desc": "作业清单，打印打勾",  "href": "homework/", "state": "soon"},
            {"name": "打卡评价",   "desc": "朗读流利度 + 成绩单", "href": "review/",   "state": "ready"},
        ],
    },
    {
        "key": "math",
        "name": "数学",
        "emoji": "🔢",
        "note": "把题型提炼成一句口诀，再用口诀解真题",
        "sections": [
            {"name": "计算秘籍", "desc": "错题清单 + 一条口诀", "href": "miji/",  "state": "ready"},
            {"name": "易错字本", "desc": "写错的字描红重练", "href": "zi/",    "state": "soon"},
        ],
    },
]


def build_index() -> None:
    """总入口页。"""
    cards = []
    for s in SUBJECTS:
        ready = sum(1 for x in s["sections"] if x["state"] == "ready")
        total = len(s["sections"])
        badge = f"{ready}/{total}" if ready else "筹备中"

        rows = []
        for sec in s["sections"]:
            inner = (f'{sec["name"]}<small>{sec["desc"]}</small>')
            if sec["state"] == "ready":
                rows.append(f'<li><a href="{s["key"]}/{sec["href"]}">{inner}</a></li>')
            else:
                rows.append(f"<li><span>{inner}</span></li>")

        cards.append(
            f'<article class="subj" data-s="{s["key"]}">\n'
            f'  <h2><span class="emo">{s["emoji"]}</span>{s["name"]}'
            f'<span class="cnt">{badge}</span></h2>\n'
            f'  <p class="note">{s["note"]}</p>\n'
            f'  <ul>\n    ' + "\n    ".join(rows) + "\n  </ul>\n"
            f"</article>"
        )

    stamp = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    body = f"""<main class="wrap">
  <header class="hero">
    <span class="eyebrow">HI-RUBY · STUDY</span>
    <h1>学习小站</h1>
    <p class="sub">语文 · 英语 · 数学，一处收齐</p>
  </header>

  <section class="subjects">
{chr(10).join(cards)}
  </section>

  <p class="foot">
    打印单点进栏目就能拿 PDF<br />
    本地预览 <code>make up</code> · 线上由 GitHub Actions 构建<br />
    构建于 {stamp}
  </p>
</main>"""

    page.write(
        DIST / "index.html",
        page.render(
            title="学习小站",
            description="语文、英语、数学的练习单和讲义，一处收齐。手机上翻，A4 打印。",
            body=body,
            emoji="📚",
            css=("site.css",),
            root=".",
        ),
    )
    print("  → dist/index.html")


def build_subjects(pdf: bool) -> None:
    """调各科自己的构建器 src/<科>/build.py（有就调，没有就跳过）。

    约定：各科 build.py 暴露 build(dist: Path, pdf: bool) -> None
    """
    for s in SUBJECTS:
        script = SRC / s["key"] / "build.py"
        if not script.exists():
            print(f"  · {s['name']}：还没有 src/{s['key']}/build.py，跳过")
            continue

        spec_ = importlib.util.spec_from_file_location(f"build_{s['key']}", script)
        mod = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(mod)
        print(f"  · {s['name']}：")
        mod.build(DIST / s["key"], pdf=pdf)


def main() -> int:
    pdf = "--pdf" in sys.argv
    keep = "--keep" in sys.argv

    if DIST.exists() and not keep:
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)

    print(f"\n构建 → {DIST.relative_to(ROOT)}/" + ("  (含 PDF)" if pdf else ""))

    shutil.copytree(SRC / "assets", DIST / "assets", dirs_exist_ok=True)
    print(f"  → dist/assets/  ({len(list((DIST / 'assets').iterdir()))} 个文件)")

    build_index()
    build_subjects(pdf)

    # 自定义域名：src/CNAME 存在就带上；不存在就走 github.io 默认域名
    cname = SRC / "CNAME"
    if cname.exists():
        shutil.copy2(cname, DIST / "CNAME")
        print(f"  → dist/CNAME  ({cname.read_text().strip()})")

    # GitHub Pages 不要 Jekyll 插手（否则 _ 开头的目录会被吞掉）
    (DIST / ".nojekyll").touch()

    n = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"\n完成：{n} 个文件\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
