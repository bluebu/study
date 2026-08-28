"""站点级配置 —— 备案号、访问统计。**改这里，全站页脚跟着变。**

页脚由 `lib/page.py` 自动挂上，各栏目的生成器一行都不用改。挂在哪儿：

    引了 print.css 的页面（打印单）   → 不挂。纸上不印备案号
    其余页面（入口页、目录页、报告页） → 挂

`noindex` 的页面（孩子的成绩单）只出备案号、**不挂统计** —— 不蒜子是第三方，
挂上等于把这些私页的地址连同 Referer 送出去。

关了就是空串：`BEIAN = ""` 不出备案行，`ANALYTICS = ""` 不出统计行。
"""

from __future__ import annotations

# 备案号。和老站（english / cn / math.hi-ruby.com）同一个主体，沿用同一个号
BEIAN = "京ICP备13029686号-1"
BEIAN_URL = "https://beian.miit.gov.cn/"

# 访问统计。目前只认 "busuanzi"（不蒜子，免费、无需注册、不用埋 key）
ANALYTICS = "busuanzi"
BUSUANZI_JS = "//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"


def foot_html(*, analytics: bool = True) -> str:
    """页脚 HTML（含统计脚本）。两项都关掉时返回空串。标记在 templates/foot.html。"""
    hits = analytics and ANALYTICS == "busuanzi"
    if not (BEIAN or hits):
        return ""
    # 循环 import：page → site → tmpl → paths，tmpl 不引 page，所以放函数里就够了
    from . import tmpl
    return tmpl.render("foot.html", beian=BEIAN, beian_url=BEIAN_URL,
                       hits=hits, busuanzi_js=BUSUANZI_JS).rstrip("\n")
