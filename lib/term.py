"""学期日历 —— `storage/spec/schedule/term.txt` 的读取口径，全站共用。

**日期是内容不是代码**：学校通知改期就改那份 spec，这个文件一行都不用动。
反过来也一样 —— 想在别处印「还有几天」，从这儿取，别再解析一遍那份 spec。

现在两处在用，两处的**基准日不一样**，这是有意的：

    build.py 的 countdown()              首页并排两条，基准日是**打开页面那天**
    src/generator/english/homework.py    打卡单页头右上角，基准日是**打卡那天**

首页的数字构建时定死会漂（隔天打开就少一天），所以那儿印的只是兜底、
真正的数由 `assets/countdown.js` 在打开时重算；打卡单是**纸**，一张纸就是
某一天的作业单，按那天算出来的数印上去反而不会漂 —— 见各自的文档串。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple

from lib import paths, spec as spec_lib

CST = timezone(timedelta(hours=8))
TERM = paths.spec("schedule", "term.txt")
WEEKDAYS = "一二三四五六日"


class Milestone(NamedTuple):
    """学期里的一个日子。`tentative` 是 spec 里日期后面带了 `?` —— 学校还没
    通知具体哪天，是按学期进度估的，页面上要标「暂定」。"""

    day: date
    name: str
    tentative: bool

    @property
    def iso(self) -> str:
        return self.day.isoformat()

    @property
    def when(self) -> str:
        return f"{self.day.month} 月 {self.day.day} 日 · 周{WEEKDAYS[self.day.weekday()]}"

    def days_from(self, since: date) -> int:
        return (self.day - since).days


def now() -> datetime:
    """当下（东八区）。全站的「今天」都从这儿来，别各自 datetime.now()。"""
    return datetime.now(CST)


def today() -> date:
    return now().date()


def milestones() -> list[Milestone]:
    """日历里的全部里程碑，按日期升序。spec 不在就返回空表。"""
    if not TERM.exists():
        return []
    sp = spec_lib.parse(TERM)
    out = []
    for b in sp.blocks:
        for name, when in b.items():
            if not when:
                continue
            try:
                day = date.fromisoformat(when.rstrip("?"))
            except ValueError:
                spec_lib.die(f"{TERM.name}：[{b.name}] {name} 的日期要写成 "
                             f"2026-11-09（后面可以带 ? 表示暂定），现在是 {when!r}")
            out.append(Milestone(day, name, when.endswith("?")))
    return sorted(out)


def ahead(since: date, limit: int | None = None) -> list[Milestone]:
    """`since` 当天及以后还没到的里程碑，最近的排在前面。

    **过一个少一个**：期中考完，取到的第一个自动变成期末 —— 用它的地方
    都不用写死是哪个里程碑。全过完了返回空表，调用方自己决定不出那一块。
    """
    out = [m for m in milestones() if m.day >= since]
    return out[:limit] if limit else out
