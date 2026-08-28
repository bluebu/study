# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 学习小站 — 项目准则

给自己孩子做的学习站：语文、英语、数学的练习单和讲义，一处收齐。
手机/iPad 上翻，A4 打印。域名 `s.hi-ruby.com`（GitHub Pages）。

## 一条铁律：数据和代码分开，代码只放输入

```
storage/   ← 数据层。天天长，只累积不重排。data 机器测的 / spec 人写的 / result 算出来的
src/       ← 代码 + 资产：generator/ 各科生成器、templates/ 标记、assets/ 样式。**一个内容文件都不放**
lib/       ← 通用库。工具，不是内容
dist/      ← 产物（HTML + PDF）。**不进 git**，每次全新构建
```

按管道阶段分层，**层名就是职责**：

```
storage/data/     机器测的 —— ../feeder 产出，源没了就算不出来
storage/spec/     人写的判断 —— 哪几处算读错、几分、怎么归组
storage/result/   算出来的指标 —— build.py 全量重算覆盖，push 当回归基准
```

这么分是为了**原始数据落地一次、可以被计算多次**：改了算法重跑构建，报告和指标都变，
`storage/data/` 一个字不动。所以生成器一律走 `paths.spec(...)` / `paths.data(...)`
取路径（`lib/paths.py`），**别再用 `Path(__file__).parent` 往下拼** —— 代码在 `src/`、
数据在 `storage/`，两棵树的相对关系只在 `lib/paths.py` 写一次，改目录名也只改那一处。

生成出来的 HTML 和 PDF 一律不提交。老站（见下）把 `sheets/*.html` 和
`*.pdf` 全提交进仓库，翻历史全是产物噪音，这次不重复。

`dist/` 由 `build.py` 生成：本地 `make build`，线上 GitHub Actions 跑
**同一个** `build.py`。所以「本地能出」就等于「线上能出」，不存在两套构建逻辑。

**`storage/` 下哪条链路产出什么文件、要不要 push —— 见 [DATA.md](DATA.md)。**
那张表是 data 构成的唯一真源，`lib/paths.py`、`.gitignore`、各科生成器、
隔壁 `../feeder` 都照它执行。

## 目录

**数据层**（累积，push；命名和去向的唯一真源是 [DATA.md](DATA.md)）：

```
storage/
  data/               机器测的（../feeder 产出，不可再生）
    english/review/     打卡评价的测量数据。名字是「书/课/页」，斜杠就是目录：
                        super8/L3/p68.{ref.txt,read.json,json,words.tsv}
  spec/               人写的判断和内容
    english/review/     哪几处算读错、四维分数、点评。同名 slug 对应 data/：
                        super8/L3/p68.txt
    english/ket/words/       KET 词表 CSV（25 个主题，带 BOM 给 Excel 用）
    english/ket/selections/  抽选卷 spec：跨主题挑词，题号沿用原主题
    english/homework/   一天一份，文件名是 YYYYMMDD
    english/retell/     一个区块一个阶段，区块内一行一段
    chinese/practice/   语文 spec，文件名是 YYYYMMDD
    math/miji/          秘籍 spec：错题按错因分组写，练习题只写题面、答案脚本算
  result/             算出来的指标（可再生，push 当回归基准）
    english/review.csv  一行一次朗读的全部指标。趋势页读它
```

**代码层**（`src/` 一个内容文件都不放）：

```
build.py              总构建器。站点地图 SUBJECTS 就在文件头部
Makefile              日常命令入口
lib/
  paths.py            各层的位置。**改目录名只改这一个文件**
  spec.py             spec DSL 解析（三科共用）
  tmpl.py             Jinja2 环境。模板的三条规矩写在它的文档串里
  page.py             页面骨架 + 目录页 + 打印单页眉（都只填模板，不拼字符串）
  site.py             站点常量：备案号、访问统计。改页脚只改这一个文件
  sheet.py            A4 → PDF（无头 Chrome，路径自动探测）
src/
  CNAME               自定义域名，build.py 带进 dist/
  templates/          **所有 HTML / SVG 标记**。改版式改这儿，不动 .py
    page.html         全站页面骨架（head / og / 资产链接 / 页脚）
    foot.html         页脚（备案号 + 统计）
    home.html         总入口页的三张学科卡
    list.html         目录页，五个栏目共用
    sheet-info.html   打印单页眉「姓名 __ 日期 __ 得分 __」，三个栏目共用
    practice/ miji/ ket/ homework/ retell/   各栏目的打印单版式
    review/           成绩单 + 目录页 + 趋势页 + 按页注入的色变量
    figures/          三把尺子 / 停顿地图 / 趋势曲线的 SVG
  assets/
    palette.css       色板单一真源
    print.css         A4 打印锁
    grid.css          田字格 / 四线三格
    site.css          站点页面（入口页、目录页）
    foot.css          页脚（备案号 + 统计），page.py 挂页脚时自动引上
    trend.css         趋势页（曲线卡片 + 指标总表）
  generator/          **所有生成器 .py**，一科一层目录
    chinese/build.py  语文练习单
    english/          英语（CLAUDE.md 里有本科的教学准则和四个栏目的口径）
      build.py        只做分发：一个栏目一层 try
      review.py       打卡评价：朗读成绩单（数只写 words / errors，其余算出来）
                      末尾落 storage/result/english/review.csv，再出趋势页
      figures.py      三把尺子 + 停顿地图 + 趋势曲线，常模数值是一手来源
      ket.py          词汇默写：CSV → A4 默写卷（单主题 / 合集 / 抽选卷 / 答案对照）
      homework.py     每日打卡：群公告 → 一张 A4 作业清单
      retell.py       复述故事：关键词按情节五阶段分组，看着讲一遍
    math/build.py     计算秘籍：错题清单 + 口诀卡 + 重练题（两页 A4）
.github/workflows/pages.yml
.claude/skills/
  kousuan/            口算卷照片 → 错题清单 + 秘籍单（图和判对错都走 ../feeder）
  ket/                KET 词卡照片 → CSV，出卷 / 抽选卷的完整流程
  review/             点读视频 → 朗读成绩单（feeder read --draft 起草 spec，人只定性）
```

## 加科目 / 加栏目

改 `build.py` 顶部的 `SUBJECTS` 一处即可 —— 入口页的卡片、栏目列表、
`ready`/`soon` 状态全从它出。栏目做好了把 `"state": "soon"` 改成 `"ready"`。

各科的生成逻辑放 `src/generator/<科>/build.py`，约定暴露：

```python
def build(dist: Path, pdf: bool = False) -> None: ...
```

`build.py` 会自动发现并调用（没有这个文件就跳过，不报错）。

## HTML 模板（`src/templates/`）

**Python 里不拼标记。** 生成器只出上下文：算好的数、选好的类名、处理过的富文本；
`<div>` `<svg>` 那些全在 `src/templates/` 下的 `.html` / `.svg` 里。
引擎是 Jinja2（唯一的第三方依赖，版本钉在 `requirements.txt`，CI 里 pip 装）。

环境配置和三条规矩在 **`lib/tmpl.py`** 的文档串里，写代码前先读那一段。摘要：

- `autoescape=True`，模板里不写 escape。**`|safe` 只给自己生成的 HTML**
  （`rich()` / `marked()` / `inline()` / `figures.*` 这些内部先 escape 再插标签）
- `StrictUndefined`：写错变量名当场报错，不是静默出一个空字符串
- **上下文的键不许叫 `items` / `keys` / `values` / `get`** —— Jinja 的 `a.b` 先找属性，
  `sec.items` 会拿到 dict 自带的方法。踩过两次
- **行内元素之间不许留空白**：`.head .info`、`.foot .sign`、`.unit` 里的箭头、
  `.d .en` 的「原文」标签、`.legend` 的色块，这几处换行会多出一个空格、版式就变了。
  哪几处、为什么，各模板顶部的注释里写着
- `trim_blocks` / `lstrip_blocks` 都开着，模板按正常缩进写。但注意：
  `{% ... -%}` 和 `{#- ... -#}` 的**收尾减号会把下一行的缩进一起吃掉**，
  该缩进的地方别写那个减号（macro 的 `endmacro` 那侧要写，起始那侧不能写）

**行内标记替换留在 Python**：`**粗**` → `<b>`、`__` → 填空横线、`<<3>>` → 小方格、
`<x>` → 划掉。这些是在一段文字**内部**按内容定位插标签，模板表达不了。

## spec DSL

三段式，`lib/spec.py` 解析：

```
# 首个 # 行是卷名，后续 # 行是注释
date: 8月26日            ← 文件头 key: value（排版旋钮）
copies: 2

[生字] copies=3           ← [名] 抬头 | 右标签  key=value
陡=dǒu, 崖=yá、
麻雀=má què               ← 项行，可跨行，, ， 、 都能当分隔
    今天写了 __ 遍         ← 缩进行 = 说明行
```

- `Block.items()` 拆项、`Block.notes()` 取缩进行、`Spec.int_()` 取整数旋钮
- 属性值可以带空格，**按下一个 `key=` 切断**。老站那条「`pass=` 必须写在
  属性最后」的限制在这里不存在
- **lib/spec.py 只解析骨架**。区块内容的语义（语文的「字=拼音」、
  英语的 `* + __ <<N>>`、抽查单的 `ask: 题面 | 答案`）各科自己解释。
  过度抽象比重复更难改

## 打印硬约定（`src/assets/print.css`，每条都是踩坑换来的）

1. `@page { size:A4; margin:0 }`，边距用 mm 写在 `.sheet` 上。
   不这么做，手机 / Epson 会沿用屏幕窄宽度排版再缩放，打出来是「移动布局」
2. `print-color-adjust: exact` 必须留着，否则田字格红线、四线格、色条全消失
3. `.screen-only` / `.print-only` 分屏幕和纸
4. **改完排版一定 Read 生成的 PDF 自检**，别凭 HTML 源码想象效果

田字格（`grid.css`）：相邻格靠负边距共享边线，**别改成每格各画一圈边框**
（相邻边会叠成双倍粗线）。

## 页脚：备案号 + 访问统计

都在 **`lib/site.py`** 一处：备案号 `BEIAN`、不蒜子开关 `ANALYTICS`。
换号、换统计、想关掉（置空串）都只动这一个文件，各栏目的生成器一行不改。

`lib/page.py` 自动决定挂不挂：

```
引了 print.css 的页面（打印单）    → 不挂。纸上不印备案号
其余页面（入口页、目录页、报告页）  → 挂，样式走 foot.css，@media print 里隐藏
noindex 的页面（孩子的成绩单）     → 只出备案号，不挂统计
```

最后一条是有意的：不蒜子是第三方，挂上等于把这些私页的地址连同 Referer 送出去。
要单独控制传 `page.render(footer=False)`。

⚠️ **本地预览时不蒜子的数字是假的**（localhost 会显示七百多万）。它按域名计数，
线上才是本站的真数 —— 老站 english.hi-ruby.com 现在是 uv 53 / pv 65，正常。
别在本地看到大数就去"修"。

## 视觉

- 颜色只改 `palette.css`。三科色沿用家族取值（语文橙 / 英语蓝 / 数学绿），
  和老站对齐过，别随手换
- **分类色里刻意没有红** —— 红专属「分数越差越红」
- 移动优先是硬约束：手机和 iPad 上好用优先于电脑
- og:title / og:description **逐字照抄本页 title / description**，
  分享到群里的卡片要和页面标题一致
- 不想被搜到的页面（讲义之类）用 `page.render(noindex=True)`，
  **别用 robots.txt Disallow** —— 那样爬虫读不到 noindex 反而会收录

## 字体（PDF 里的中文全靠它）

- PDF 是 GitHub Actions 的 ubuntu runner 导出的，那儿**不带任何中文字体**。
  不装的话整份 PDF 的中文都是方块（拼音是拉丁字符，照常显示，所以很容易漏看）。
  workflow 里装 `fonts-noto-cjk`（正文黑体）+ `fonts-arphic-ukai`（田字格范字的楷体）
- `palette.css` 的每个字体栈都必须同时带 mac / win / **linux** 三套名字。
  CI 日志里「可用的中文字体」那一步会打印实际装到的 family 名，对不上就看那儿
- **本地和线上字形不一样**：本地 mac 用 PingFang + Kaiti，线上 ubuntu 用
  Noto Sans CJK + AR PL UKai。田字格是固定尺寸、字在格里居中，所以只是字形差异、
  不影响排版；拼音那行 Times New Roman 和 Liberation Serif 是等宽替换，宽度一致。
  **家长实际点「打印单」拿到的是线上那份**，所以线上字形才是要紧的
- 嫌文鼎 UKai 的楷体字形旧，可以换开源的 **LXGW WenKai**（霞鹜文楷，专为中文阅读
  设计，字形好得多）：在 workflow 里 curl 它 release 的 TTF 丢进
  `/usr/share/fonts/` 再 `fc-cache -f`。字体栈里已经把 `"LXGW WenKai"`
  排在 UKai 前面了，装上就自动生效

## 自检（改完排版必看，但工具有坑）

- **改模板要拿旧产物对比**：`make build` 前先 `cp -r dist <临时目录>`，改完
  `diff -rq`。HTML 是确定性输出，**理想结果是字节级零差异**；有差异就得逐条能解释
  （空白归一化、`&#x27;` vs `&#39;` 这类），解释不了的就是真改坏了。
  空白差异再用真实视口截图做**像素比对**（`ImageChops.difference(...).getbbox()`
  返回 `None` 才算过）—— 光看 diff 判断不了 flex/grid 里的空白到底有没有影响
- **打印单**：Read 生成的 **PDF**，别凭 HTML 源码想象效果
- **网页**：Chrome headless 截图**不能**用 `--window-size` 模拟手机视口 ——
  它的布局视口恒为 **500px**，`--window-size` 只是把 500px 的渲染结果裁成那个尺寸。
  同理 `--dump-dom` 量出来的 `innerWidth` 永远是 500，`--headless=new` 也一样。
  临时注入 `<style>html{width:390px}</style>` 只对**没有 media query 的页面**等价 ——
  media query 读的是视口宽度，不是 html 的宽度，注入了也不会触发。
  `review-index.css` 和 `review.css` 现在都有 media query，所以量它们必须用真实视口：

  ```bash
  npm i playwright-core          # 浏览器缓存 ~/Library/Caches/ms-playwright 里已经有了
  node shot.mjs <url> <out.png> 390     # newPage({ viewport:{width:390}, isMobile:true })
  ```

  跑完打一行 `innerWidth` 确认没被静默改掉 —— 拿不到 390 就是没模拟上，量出来的白量
- 探针 HTML **必须放在 `dist/` 里对应的目录下**，否则 CSS 的相对路径会 404，
  量到的是一个没有样式的布局 —— 看着像 bug，其实是探针自己坏了
- **打印单在手机上要量一次横向溢出**：`.sheet` 有 `max-width:100%`，元素本身
  会缩到屏幕宽，但**里面的内容不一定跟着缩** —— 多列 grid、`max-content` 的列、
  `white-space:nowrap` 的长算式都压不动，于是内容跑到纸外面，屏幕上看着就是
  「白色背景不全、右边一条内容浮在灰底上」。量法：

  ```js
  document.documentElement.scrollWidth   // > 视口宽就是溢出了
  document.querySelector('.sheet').scrollWidth
  ```

  排查顺序：先找 `right` 最大的**叶子**节点，再把可疑容器克隆到
  `width:min-content` 里量 —— 撑破纸的常常是容器（一行两列的 grid），
  不是文本。**`max-content` 的列宽是「不换行时的宽度」，光给子元素解 nowrap
  压不下来，必须改列定义本身**（踩过：改了 `.compare` 的列，可真正是 grid 的是
  `.compare .row`，白改一轮）。
  修完两件事都要验：手机上零溢出，以及 **PDF 还是原来的版式**
  （只在 `@media screen` 里改，`@media print` 一个字都不动）
- 用 `str.replace` 改样式/脚本时**加 assert**，否则锚点写错会静默失败，
  然后你会去调一个根本没改动的文件

## 内容准则

- **不增不删**：给的字词一个不落、也不自己加练习项；课次分组照抄，不重排合并
- 内容有歧义（字词数量对不上、看不出哪一课）**先问，别猜**
- 中文与数字/英文之间留空格（`16 课`）
- 各科的教学体系准则（英语对标美国本土语法体系、语文多音字按课文语境定音、
  数学用算术不用代数方程）在搬对应科目内容时写进 `src/generator/<科>/CLAUDE.md`

## 命令

```bash
make            # 看全部命令
make build      # 构建到 dist/
make pdf        # 构建 + 导 PDF
make up         # 构建 + 本地预览（8002，手机同 WiFi 可看，带扫码）
make clean      # 删 dist/
```

## 发布

- 分支 **master**，远端 `git@github.com:bluebu/study.git`
- GitHub Pages 用 **Actions 部署**（不是 branch 部署）：
  仓库 Settings → Pages → Source 选 "GitHub Actions"
- 自定义域名：在 `src/` 下放 `CNAME` 文件，`build.py` 会带进 `dist/`
- **提交策略：改完自检（截图 / Read PDF）后直接 commit + push，不用问、不用等确认**

## 喂数据台（../feeder）—— 统一录入

**素材不手敲。** 照片、录音、板书进隔壁那个 mac 客户端，出来的是这边能直接用的输入：

```
指读视频 + 教材截图 ──► read / scan   ──► 打卡评价的测量数据
口算卷照片          ──► sheet / check ──► 转正分块图 + 逐题对错
单词卡照片          ──► cards         ──► KET 词表候选
白板照片            ──► board         ──► 复述关键词候选
生字词 / 生字表照片 ──► pinyin        ──► 拼音候选 + 多音字标记
                                              │
                          人在会话里核对、定性、归组、定多音字
                                              │
                                     正式的 spec / CSV ──► build.py ──► dist/
```

**每条链路产出哪些文件、叫什么名、落在哪、要不要 push —— 见 [DATA.md](DATA.md)。**
别在这儿重复一遍：四份口径互相漂移正是那张表被写出来的原因。

命令行 `../feeder/bin/feeder <动词>`（没编过先 `cd ../feeder && make cli`），
或者开客户端把文件拖进去 —— 它自己猜链路，猜错了在下拉里改。

`feeder` 只做机器算得出的事，判断留给会话。它的准则在 `../feeder/CLAUDE.md`。
三条要记住的：

- **一段录音跨几页也不用先剪。** `read --split`：名字只填到「书/课」，
  `--ref` 按朗读顺序给几份，页边界机器从对齐算（每页末词读完的时刻）。
  实测拿 p68/p69 反推，算出的切点和当初人手切的那一刀差 0.16 秒。
  算完边界**每页单独裁一段音频各跑一遍** —— 声学阈值是从那一段的本底噪声推的，
  整段算一次再切会让阈值变、和历史数据没法比。
- **一叠教材截图一次进来，页码机器自己认。** 页角那枚绿圆盘（对开页在外侧，
  左页左下、右页右下）—— 名字只填到「书/课」（`super8/L3`），17 页一次落成
  `data/super8/L3/p63.ref.txt` … `p79.ref.txt`，不用一张张改名。
  图片名和拖进来的顺序都不可靠：那批里第 63 页和第 65 页相邻、第 64 页排在最后。
  客户端三张以上自动按页拆，命令行加 `--split`。**名字形状不对会被当场拒掉** ——
  把图片文件名当成书课名，是落一地 `微信图片_2026….ref.txt` 的唯一来路，
  现在跑都跑不起来。认不出页码的那张退回原图名，跑完还会报
  「认出第 63–79 页，中间不缺页」
- **机器认不准的地方它自己会说**：口算卷的手写数字根本不认（题是人抄的）、
  音标认不住就留空、多音字全标出来。这几处别嫌它啰嗦，那正是要人做的判断
- **声学口径不能动。** `feeder` 里那五个常数是老站 `analyze.py` 的逐行复刻，
  报告里「和上一页比」直接拿新旧数字比。`cd ../feeder && make test` 会拿老站
  那批数据回归，六个字段加停顿明细必须完全一致

## 老站：只当参照，不要改

`../english`、`../chinese`、`../math` 是这个站的前身，各自还在线上跑
（`english.hi-ruby.com`、`cn.hi-ruby.com`、`math.hi-ruby.com`），
**逐渐作废**。新内容只进 study，老内容不搬。

要参照实现时去翻它们，尤其这几处成熟的东西：

| 想做什么 | 去看 |
|---|---|
| 语文练习单 / 朗读单 / 抽查单 / 总表 | `../chinese/{practice,recite,check,outline}/` + 各自 README |
| KET 四线三格默写卷、群公告 → 打卡单 | `../english/{ket,homework}/` + `.claude/skills/` |
| 朗读声学分析（本机 Speech 离线转写 + 逐词时间戳） | `../english/review/tools/{words.swift,analyze.py}` |
| 数学讲义版式、竖式排版 | `../math/docs/*.html` |
| 各科教学体系准则 | 三份 `../*/CLAUDE.md` |

⚠️ 老站的坑（别再踩）：
- Chrome 路径硬编码成 mac 的 `/Applications/...`，CI 里跑不了 →
  `lib/sheet.py` 改成自动探测
- HEIC 转图**别用 `sips --cropOffset`**，实测偏移不生效（永远裁中心），
  要裁切改用 PIL
