# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 学习小站 — 项目准则

给自己孩子做的学习站：语文、英语、数学的练习单和讲义，一处收齐。
手机/iPad 上翻，A4 打印。域名 `study.hi-ruby.com`（GitHub Pages）。

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
  english/specs/      英语 spec
  math/lessons/       数学讲义源
.github/workflows/pages.yml
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
| 儿童语法关卡（颜色教成分 + 点击朗读） | `../english/grammar/` |
| 数学讲义版式、竖式排版 | `../math/docs/*.html` |
| 各科教学体系准则 | 三份 `../*/CLAUDE.md` |

⚠️ 老站的坑（别再踩）：
- Chrome 路径硬编码成 mac 的 `/Applications/...`，CI 里跑不了 →
  `lib/sheet.py` 改成自动探测
- HEIC 转图**别用 `sips --cropOffset`**，实测偏移不生效（永远裁中心），
  要裁切改用 PIL
