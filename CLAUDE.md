# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 学习小站 — 项目准则

给自己孩子做的学习站：语文、英语、数学的练习单和讲义，一处收齐。
手机/iPad 上翻，A4 打印。域名 `s.hi-ruby.com`（GitHub Pages）。

## 一条铁律：源码只放输入

```
src/       ← 内容源：spec、讲义、样式、图。只有「输入」
lib/       ← Python 生成器。工具，不是内容
dist/      ← 产物（HTML + PDF）。**不进 git**，每次全新构建
```

生成出来的 HTML 和 PDF 一律不提交。老站（见下）把 `sheets/*.html` 和
`*.pdf` 全提交进仓库，翻历史全是产物噪音，这次不重复。

`dist/` 由 `build.py` 生成：本地 `make build`，线上 GitHub Actions 跑
**同一个** `build.py`。所以「本地能出」就等于「线上能出」，不存在两套构建逻辑。

## 目录

```
build.py              总构建器。站点地图 SUBJECTS 就在文件头部
Makefile              日常命令入口
lib/
  spec.py             spec DSL 解析（三科共用）
  page.py             HTML 页面骨架（head / og / 资产链接）
  sheet.py            A4 → PDF（无头 Chrome，路径自动探测）
src/
  assets/
    palette.css       色板单一真源
    print.css         A4 打印锁
    grid.css          田字格 / 四线三格
    site.css          站点页面（入口页、目录页）
  chinese/specs/      语文 spec
  english/            英语（CLAUDE.md 里有本科的教学准则和 review 口径）
    figures.py        三把尺子 + 停顿地图，常模数值是一手来源
    review/data/      喂数据台产出的测量数据（进 git —— 录音不进，这些再也算不出来）
    review/specs/     人的判断：哪几处算读错、四维分数、点评
    ket.py            词汇默写：CSV → A4 默写卷（单主题 / 合集 / 抽选卷 / 答案对照）
    ket/words/        KET 词表 CSV（25 个主题，带 BOM 给 Excel 用）
    ket/selections/   抽选卷 spec：跨主题挑词，题号沿用原主题
  math/
    build.py          计算秘籍：错题清单 + 口诀卡 + 重练题（两页 A4）
    specs/            秘籍 spec：错题按错因分组写，练习题只写题面、答案脚本算
    lessons/          数学讲义源
.github/workflows/pages.yml
.claude/skills/
  kousuan/            口算卷照片 → 错题清单 + 秘籍单
                      crop.py 转正放大照片、check.py 逐题判对错（数字别自己数）
```

## 加科目 / 加栏目

改 `build.py` 顶部的 `SUBJECTS` 一处即可 —— 入口页的卡片、栏目列表、
`ready`/`soon` 状态全从它出。栏目做好了把 `"state": "soon"` 改成 `"ready"`。

各科的生成逻辑放 `src/<科>/build.py`，约定暴露：

```python
def build(dist: Path, pdf: bool = False) -> None: ...
```

`build.py` 会自动发现并调用（没有这个文件就跳过，不报错）。

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
- 用 `str.replace` 改样式/脚本时**加 assert**，否则锚点写错会静默失败，
  然后你会去调一个根本没改动的文件

## 内容准则

- **不增不删**：给的字词一个不落、也不自己加练习项；课次分组照抄，不重排合并
- 内容有歧义（字词数量对不上、看不出哪一课）**先问，别猜**
- 中文与数字/英文之间留空格（`16 课`）
- 各科的教学体系准则（英语对标美国本土语法体系、语文多音字按课文语境定音、
  数学用算术不用代数方程）在搬对应科目内容时写进 `src/<科>/CLAUDE.md`

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

## 喂数据台（../feeder）

朗读评价的输入不是手敲的，是隔壁那个 mac 客户端产出的：

```
指读视频 + 教材截图  ──►  feeder  ──►  src/english/review/data/<slug>.{read.json,ref.txt,json,words.tsv}
                                          │
                                          └─►  src/english/review/specs/<slug>.txt   ← 人在会话里写的判断
                                                    │
                                                    └─►  src/english/build.py  ──►  dist/
```

`feeder` 只做机器算得出的事（抽音轨、转写、逐词时间戳、停顿声学、OCR、红线检测、
逐字对齐候选），判断留给会话。它的准则在 `../feeder/CLAUDE.md`。

两条要记住的：

- **声学口径不能动。** `feeder` 里那五个常数是老站 `analyze.py` 的逐行复刻，
  报告里「和上一页比」直接拿新旧数字比。`cd ../feeder && make test` 会拿老站
  昨天那批数据回归，六个字段加停顿明细必须完全一致
- **`*.marked.png` 是核对图**，看一眼红线框对不对就没用了，已经在 `.gitignore` 里

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

老站 `../english/grammar/`（11 关儿童语法，颜色教成分 + 点击朗读）**那一版作废了**，
不搬也不参照。将来真要做语法内容，从 `src/english/CLAUDE.md` 的「对标美国本土」
那节重新起手。

⚠️ 老站的坑（别再踩）：
- Chrome 路径硬编码成 mac 的 `/Applications/...`，CI 里跑不了 →
  `lib/sheet.py` 改成自动探测
- HEIC 转图**别用 `sips --cropOffset`**，实测偏移不生效（永远裁中心），
  要裁切改用 PIL
