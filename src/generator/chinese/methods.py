"""语文 · 学习方法 —— 把一册课文提炼成遇到难题时用的办法，一课一个。

spec 是 storage/spec/methods.txt（三科共用，读取口径在 lib/methods.py），
产物只有一页：dist/chinese/methods/index.html。

- **严格照课本顺序**：第 1 课到第 27 课，按单元分组。卡片上的「步骤」
  （为什么 / 看 / 问 / 想 / 做 / 回头看）只是小标签，不拿来重排
- 上半页给孩子（卡片：名字、问自己的那一句、课文里那件事），下半页给大人
  （作业里怎么用）。**都直接露出来**，不做点开才出的折叠
- 没学到的课转灰。进度只改 spec 头的 `learned:` 一个数
"""

from __future__ import annotations

from pathlib import Path

from lib import methods, page, tmpl

BOOK = "四年级上册"


def build_methods(dist: Path, pdf: bool = False) -> None:
    out_dir = dist / "methods"
    bk = methods.book()
    n = sum(len(u["methods"]) for u in bk["units"])
    body = tmpl.body("methods/page.html", book_name=BOOK, learned=bk["learned"],
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
    print(f"    → methods/index.html  （{n} 个方法 · 学到第 {bk['learned']} 课）")
