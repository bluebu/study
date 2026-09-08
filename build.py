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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))
from lib import page, paths, spec as spec_lib, tmpl  # noqa: E402

# 各层的位置全在 lib/paths.py 一处定义，这儿只是取个短名
SRC, GEN, DIST = paths.SRC, paths.GEN, paths.DIST

CST = timezone(timedelta(hours=8))

# 学期日历。**日期是内容不是代码** —— 学校通知改期就改
# storage/spec/schedule/term.txt 那一处，这个文件一行都不用动
TERM = paths.spec("schedule", "term.txt")
WEEKDAYS = "一二三四五六日"


# 首页并排放几条倒计时。两条：期中 + 期末，正好一行两列，手机上也不挤
COUNTDOWNS = 2


def countdown() -> list[dict]:
    """首页那两条倒计时 —— 学期日历里**接下来还没到的**里程碑，最多 COUNTDOWNS 条。

    过一个少一个，自动往后顺（期中考完 → 期末 + 本学期结束），
    全过完了返回空列表、首页那一行整个不出。
    日期后面带 `?` 的是估的（学校还没通知具体哪天），页面上标「暂定」。

    **这儿算出来的天数只是兜底**：站是静态的，构建时定死的数字停在最后一次
    push 那天 —— 隔天打开就少一天、周末不提交能差两天，而倒计时给错天数比
    不给更糟。页面上真正显示的数字由 `assets/countdown.js` 在打开时按当天重算，
    这个数只在没 JS 时露脸。
    """
    if not TERM.exists():
        return []
    sp = spec_lib.parse(TERM)
    today = datetime.now(CST).date()
    ahead = []
    for b in sp.blocks:
        for name, when in b.items():
            if not when:
                continue
            try:
                day = date.fromisoformat(when.rstrip("?"))
            except ValueError:
                spec_lib.die(f"{TERM.name}：[{b.name}] {name} 的日期要写成 "
                             f"2026-11-09（后面可以带 ? 表示暂定），现在是 {when!r}")
            if day >= today:
                ahead.append((day, name, when.endswith("?")))
    return [{"name": name, "iso": day.isoformat(), "days": (day - today).days,
             "when": f"{day.month} 月 {day.day} 日 · 周{WEEKDAYS[day.weekday()]}",
             "tentative": tentative}
            for day, name, tentative in sorted(ahead)[:COUNTDOWNS]]


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
            {"name": "背诵单",   "desc": "切块背，隔天再测",     "href": "recite/",   "state": "ready"},
            {"name": "抽查单",   "desc": "一课一张，家长照着问", "href": "check/",    "state": "ready"},
            {"name": "教材总览", "desc": "哪篇要背、哪首要默写", "href": "overview/", "state": "ready"},
        ],
    },
    {
        "key": "english",
        "name": "英语",
        "emoji": "🔤",
        "note": "对标美国本土语法体系，不教中国式五大句型",
        "sections": [
            {"name": "词汇默写",   "desc": "KET 核心词四线三格", "href": "ket/",      "state": "ready"},
            {"name": "每日打卡",   "desc": "作业清单，打印打勾",  "href": "homework/", "state": "ready"},
            {"name": "打卡评价",   "desc": "朗读流利度 + 成绩单", "href": "review/",   "state": "ready"},
            {"name": "复述故事",   "desc": "关键词地图，看着讲",  "href": "retell/",   "state": "ready"},
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
    {
        "key": "schedule",
        "name": "课程表",
        "emoji": "🗓️",
        "note": "一张纸看完一周，装书包照着带书",
        "sections": [
            {"name": "一周课表", "desc": "六节课 + 午休，A4 贴桌前", "href": "week/", "state": "ready"},
            {"name": "放学检查", "desc": "作业抄没抄，三科逐项过", "href": "afterschool/", "state": "ready"},
        ],
    },
]


def build_index() -> None:
    """总入口页。卡片内容全从 SUBJECTS 出，版式在 src/templates/home.html。"""
    subjects = []
    for s in SUBJECTS:
        ready = sum(1 for x in s["sections"] if x["state"] == "ready")
        subjects.append({**s,
                         "badge": f"{ready}/{len(s['sections'])}" if ready else "筹备中"})

    body = tmpl.body(
        "home.html",
        subjects=subjects,
        counts=countdown(),
        stamp=datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
    )

    page.write(
        DIST / "index.html",
        page.render(
            title="学习小站",
            description="语文、英语、数学的练习单和讲义，外加一张课程表，一处收齐。手机上翻，A4 打印。",
            body=body,
            emoji="📚",
            css=("site.css",),
            js=("countdown.js",),
            root=".",
        ),
    )
    print("  → dist/index.html")


def build_subjects(pdf: bool) -> None:
    """调各科自己的构建器 src/generator/<科>/build.py（有就调，没有就跳过）。

    约定：各科 build.py 暴露 build(dist: Path, pdf: bool) -> None
    """
    for s in SUBJECTS:
        script = GEN / s["key"] / "build.py"
        if not script.exists():
            print(f"  · {s['name']}：还没有 src/generator/{s['key']}/build.py，跳过")
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

    shutil.copytree(paths.ASSETS, DIST / "assets", dirs_exist_ok=True)
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
