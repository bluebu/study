---
name: ket
description: 单词卡照片 → CSV → A4 默写卷（src/english/ket/ + dist/english/ket/）。把 KET 词汇书的单词卡照片整理成 CSV 词表，或从已有词表出默写卷（看中文写英文、四线三格）、答案对照版、跨主题抽选卷。当用户发来单词表照片要求整理，或要出默写卷、抽选某几个词、要打印 PDF 时使用。
argument-hint: [主题编号 + 照片，或要抽选的词号]
---

# ket：单词卡照片 → CSV → A4 默写卷

```
单词卡照片 ──feeder cards──► <NN>_<主题>.draft.csv ──人核对──► src/english/ket/words/<NN>_<主题>.csv
                             + 核对图 + .cards.json                      │
                    src/english/ket/selections/*.txt  ← 抽选卷 spec（人挑的词号）
                                        ▼
                          python3 build.py --pdf
                                        ▼
              dist/english/ket/  单主题 · 合集（上下册）· 抽选卷 · 各自的答案对照版
```

CSV 是唯一输入，卷子全是产物 —— **改词表就重新构建，不要手改产物**。
主题编号由用户指定（对应词汇书板块序号，不是字母序）。已用 01–25，新主题没给编号先问。

## 工作流 1：照片 → CSV（这段最容易出错）

先让**喂数据台**（`../feeder`）扫一遍，它做机器该做的两件事：OCR 成词条、
把相邻照片的重叠去掉；认不准的（贴着图边、把握低、音标没认住）全标出来。

```bash
../feeder/bin/feeder cards 卡1.jpg 卡2.jpg --slug 26_body_and_face
   # → src/english/ket/words/26_body_and_face.draft.csv（候选，gitignore 掉了）
   #   + .cards.json（每条的把握程度和出处）+ 核对图
```

**照片顺序就是词表顺序**，按文件编号从小到大给参数，别让它自己排。
HEIC 直接吃，不用先转 PNG。

然后逐条核对 —— 这一步是人的活：

1. **⚠️ 标出来的那几条对着照片看**（核对图里红框就是）。贴边的多半是
   两张照片的接缝，要么被裁了一半，要么和上一张重了。
2. **音标要补**。Vision 认 IPA 十有八九退成 ASCII（`/ˈæksɪdənt/` → `/'zeksident/`），
   认不住的一律留空了 —— 印一个错音标比不印更糟。看着照片把音标填回去。
3. **忠实转录**：词性、释义照卡片原文写，看着像印刷错误也保留（用户明确要求过，
   如 boil 卡片印 n.），只在汇报时口头提一句。全角标点（；，（））保留，
   正好避开 CSV 的逗号转义。
4. **CSV 格式**：表头 `no,word,phonetic,pos,meaning`，带 UTF-8 BOM（feeder 已经写上了）。
   `no` 从 1 开始、每个主题独立编号（默写卷题号直接用它）。
   词组（ice cream、wash up）卡片上没音标词性就留空。
5. 核完**另存成正式文件名**（去掉 `.draft`），draft 不进 git。
6. 新主题要在 `src/english/ket.py` 的 `TITLES` 里加一条显示名（key 是去掉编号前缀的文件名）。
   **英文名太长会把页眉挤成两行**，取个短名（见 personal_feelings 那条）。
7. 汇报总词数、板块起止词、边界行的核对结论。

照片糊到 OCR 认不动（`.cards.json` 里把握普遍很低）就退回老办法：逐张 Read 手抄。
裁切放大用 PIL，**别用 `sips --cropOffset`**（实测偏移不生效，永远裁中心）。

## 工作流 2：出卷子

```bash
python3 build.py --pdf        # 全站构建：25 个主题 + 4 份合集 + 抽选卷，一次全出
```

单独调一份 PDF（改样式时快速看效果）：

```python
from lib import sheet; from pathlib import Path
h = Path("dist/english/ket/words_1.html"); sheet.to_pdf(h, h.with_suffix(".pdf"))
```

抽选卷：用户点名「第 N 章的第 x,y,z 个词」时，写 `src/english/ket/selections/<名字>.txt`：

```
# 20260820 词汇          ← 首个 # 行是卷名，页眉显示「20260820 词汇 默写」
10:1,2,6,9,13,16,46-50   ← 主题号:题号，支持 a-b 区间，顺序照写
11:10-19
```

章节标题和题号一律沿用原词表，不重新编号。默写版和答案对照版会一起生成。
用户给的题号有歧义（漏逗号的 `1316`）先问清。

## 自检（每次改排版都要做）

- **Read 生成的 PDF**，别凭 HTML 源码想象。
- **HTML 里 `.sheet` 的个数必须等于 PDF 页数**。不等就是某页装不下、被 Chrome
  二次分页，打出来夹半张空页 —— 答案版的切页是脚本按 px 估算的（`ANS_PAGE_H`），
  改页眉页脚或字号都会让它失准。
- 量实际高度用 playwright 真实视口，不要用 `--window-size`（布局视口恒为 500px）。

## 已定稿的格式（改动要用户同意）

- A4 两栏，一页 30 词；页眉标题 + 姓名/日期/得分，页脚词数 + 页码。
- 题型「看中文写英文」：序号 + 中文释义 + 灰色词性提示 + 四线三格。
- 四线三格绿线 + 红基线、总高 11mm（小学英语本习惯，孩子四年级，行距宁松勿密）。
  旋钮在 `src/assets/grid.css` 的 `:root`，别在 ket.css 里覆盖。
- 合集分上下册：`words_1` 固定 01–12（定稿不动），`words_2` 收 13 起 —— 范围在
  `ket.py` 的 `VOLUMES`。章节之间不分页，标题占一整行、且不落在页面最后一行。
- 答案对照版：紧凑无线格，竖排 5 个一组、一行两组，交替浅底，英文靠右 + 音标。

## 用户提过但还没做

打乱顺序防背字母序、简化过长释义（如 cut 的「（从动物躯体上）割下的一块肉」）。做之前先问。
