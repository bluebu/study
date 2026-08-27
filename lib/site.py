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
    """页脚 HTML（含统计脚本）。两项都关掉时返回空串。"""
    rows = []
    if BEIAN:
        rows.append(f'  <p class="beian"><a href="{BEIAN_URL}" target="_blank"'
                    f' rel="noopener">{BEIAN}</a></p>')

    script = ""
    if analytics and ANALYTICS == "busuanzi":
        # 不蒜子拿到数字后才把这两段显出来 —— 先藏起来，不占位、不闪动
        rows.append(
            '  <p class="hits">'
            '<span id="busuanzi_container_site_uv" style="display:none;">'
            '👀 <span id="busuanzi_value_site_uv"></span> 位小朋友来过</span>'
            '<span id="busuanzi_container_site_pv" style="display:none;">'
            ' · 共翻开 <span id="busuanzi_value_site_pv"></span> 次</span></p>')
        script = f'\n<script async src="{BUSUANZI_JS}"></script>'

    if not rows:
        return ""
    return '<footer class="site-foot">\n' + "\n".join(rows) + "\n</footer>" + script
