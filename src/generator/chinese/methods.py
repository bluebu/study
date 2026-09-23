"""语文 · 学习方法 —— 把一册课文提炼成遇到难题时用的办法，一课一个。

spec 是 storage/spec/methods.txt（三科共用，读取口径在 lib/methods.py），
产物只有一页：dist/chinese/methods/index.html。

- **严格照课本顺序**：课文照课次，语文园地排在本单元最后一课后面，
  **园地也是一张卡**（梳理与交流、名言警句、日积月累、书写提示都在上面，
  写成「遇到问题时怎么用」，不列原文）
- **一张卡一行，左右两半**：左边是这一课的方法，右边是一条方法论 / 辩证法 /
  哲学 / 心理学常识，接着这一课讲
- 页头是五步主线（想要什么 → 收集信息 → 分析问题 → 解决问题 → 检查复盘）
  和一句态度；页底给大人（作业里怎么用）。**都直接露出来**，不做折叠
- 27 课全部放开，不按进度转灰（家长的决定）
"""

from __future__ import annotations

from pathlib import Path

from lib import methods, page, tmpl

BOOK = "四年级上册"


def build_methods(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "methods"
    bk = methods.book()
    n = sum(len(u["methods"]) for u in bk["units"])
    body = tmpl.body("methods/page.html", book_name=BOOK,
                     steps=bk["steps"], units=bk["units"])
    page.write(
        out_dir / "index.html",
        page.render(
            title="学习方法 · 语文",
            description=f"{BOOK}一课提炼一个遇到难题时用的办法，照课本顺序，名字就借那一课。",
            body=body,
            emoji="🧰",
            css=("site.css", "methods.css"),
            root="../..",
            noindex=True,
        ),
    )
    print(f"    → methods/index.html  （{n} 个方法）")
