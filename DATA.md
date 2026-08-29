# 学习小站 — data 构成

哪条链路产出什么文件、叫什么名、落在哪、要不要 push。

**这是唯一真源。** `src/` 下的生成器、`lib/paths.py`、根 `CLAUDE.md`、`.gitignore`、隔壁
`../feeder`（喂数据台）全都照这张表执行 —— 别在别处再维护第二份说明，
四份口径互相漂移正是这张表被写出来的原因。

## 三层

```
素材（本机 inbox/，永不进仓库）
    │  ../feeder：转正、OCR、离线转写、逐词对齐、声学包络
    ▼
storage/data/     机器测的 —— 源没了就算不出来，所以 push
storage/spec/     人写的判断 —— 哪几处算读错、几分、怎么归组
    │  build.py（src/generator/ 下的生成器）
    ├──────────────► storage/result/   算出来的指标（可再生，push 当回归基准）
    │                      │
    ▼                      ▼
dist/  单页报告、练习单     dist/  趋势页、汇总列表
```

**层名就是职责**：`data` 抓来的 / `spec` 人定的 / `result` 算出来的。
改目录名只改 `lib/paths.py` 一处 —— 各科生成器一律走 `paths.spec(...)`、
`paths.data(...)`，不许再用 `Path(__file__).parent` 往下拼。

`storage/result/` 是**旁路不是必经**：单页报告仍直接吃 spec 全文 + 完整测量 JSON
（评语要逐字印在纸上、停顿地图要每次歇气的起止时刻），指标表装不下这些。
别为了「报告全从 result 出」把散文和大 JSON 塞进 result —— 那就成了 data 的副本。

## 五档去向

| 档 | 落在哪 | 要不要 push | 含义 | 谁来清 |
|---|---|---|---|---|
| **输入** | `storage/data/`<br>`storage/spec/` | ✅ push | 测量数据 + 人写的判断。站的真正输入 | 不清，长期留着 |
| **派生** | `storage/result/` | ✅ push | 算出来的指标。**可再生** —— push 它是判据的有意例外，见下 | 不清，每次构建全量覆盖 |
| **候选** | 和正式文件同目录 | ❌ gitignore | `.draft.*`，机器给的候选。人核对后**另存成正式名**才进 repo | 另存后删掉 draft |
| **临时** | 和正式文件同目录 | ❌ gitignore | 核对用的过程产物，看一眼就没用了 | 随手删 |
| **素材** | 本机 `inbox/` | ❌ 不进任何仓库 | 录音、视频、作业照片 | 自己归档 |

判据只有一条：**这份东西丢了还能不能再算出来。** 算不出来的必须 push，
算得出来的一律不留 —— `storage/result/` 是唯一的例外，理由在下面那节。

- 测量数据算不出来了 —— 录音和教材照片不进仓库，声学数字、逐词时间戳、
  红线划中的原文，源没了就永远没了。所以必须 push。
- 临时产物随时能从素材再算一遍，留着只是噪音（`.page.json` 一份 85 KB）。
- 候选是**机器的猜测不是结论**，没核过的东西不许混进仓库。

## 名字（slug）的规矩

打卡评价那套名字是「**书 / 课 / 页**」，**斜杠就是目录**：

```
super8/L3/p68   →   storage/data/english/review/super8/L3/p68.ref.txt
                    storage/spec/english/review/super8/L3/p68.txt
                    dist/english/review/<那天>.html#super8-L3-p68
```

- **一叠截图一次进来时，名字只填到「书 / 课」**（`super8/L3`），页码机器从页角
  那枚绿圆盘认。图片名（微信编号）和拖进来的顺序都不可靠。
- `review.py` 找数据全靠 `data/<slug>.<ext>` 拼路径，spec 里没有任何字段指向数据文件。
  **名字错了，spec 和数据就配不上对** —— 所以 feeder 在写盘前就校验名字，
  形状不对的名字根本跑不起来，不留到磁盘上再来收拾。

## 机器测出来的（`../feeder` 产出，人不手敲）

| 链路 | 名字填到哪 | 产出 | 落到 | 去向 |
|---|---|---|---|---|
| `read` 朗读录音 | `<书>/<课>/pNN`；一次读了几页写区间 `pNN-MM` | `.read.json` 主产物（声学 + 转写 + 逐字对齐）<br>`.json` 停顿声学（老站字段）<br>`.words.tsv` 逐词时间戳<br>`.read.json` 里的 `pages`：这次读了哪几页、每页多少词错几处（**从同一份对齐派生，不是分开测的**） | `storage/data/english/review/` | **进 repo** |
| `read --draft` | 同上 | `.draft.txt` spec 候选（`[比对]`/`[卡壳]`/`[磕巴]` 和文件头填好，判断留 `⟨⟩`） | `storage/spec/english/review/` | **候选** → 另存 `pNN.txt` |
| `scan` 教材截图 | `<书>/<课>`，**页码机器认** | `.ref.txt` 红线划中的课文原文 | `storage/data/english/review/` | **进 repo** |
| | | `.page.json` 整页 OCR + 坐标<br>`.marked.png` 核对图<br>`.full.txt` 整页全文（`--full`） | 同上 | **临时** |
| `cards` 单词卡 | `<NN>_<主题>` | `.draft.csv`（带 BOM 给 Excel） | `storage/spec/english/ket/words/` | **候选** → 另存 `<NN>_<主题>.csv` |
| | | `.cards.json` `.cards.marked.png` | 同上 | **临时** |
| `board` 白板 | `<故事slug>` | `.draft.txt` | `storage/spec/english/retell/` | **候选** → 另存 `<故事slug>.txt` |
| | | `.board.json` `.board.marked.png` | 同上 | **临时** |
| `pinyin` 生字词 | `<YYYYMMDD>` | `.draft.txt` | `storage/spec/chinese/practice/` | **候选** → 另存 `<YYYYMMDD>.txt` |
| `sheet` 口算卷 | 不需要名字 | `full.jpg` `block_N.png` `zoom_x_y.png` | 本机临时目录，**不落 `storage/`** | **临时** |
| `check` 判对错 | 不需要名字 | 只打 stdout，不落文件 | — | — |

**为什么 `read` / `scan` 的**测量数据**不带 `.draft.`**：那是机器算的最终值，
没有「候选」一说 —— 停顿就是那么多次，逐词时间戳就是那个时刻。
`cards` / `board` / `pinyin` 出的才是候选：词性、关键词归哪个阶段、多音字按课文
读哪个音，判断在人这儿。

`read --draft` 是**同一条链路的第二个去向**，不矛盾：它出的不是测量数据，是一份
**spec 候选**（人写的那一层），所以带 `.draft.`、落 `storage/spec/`。read 因此是
唯一一条两层都写的链路 —— 测量进 data，候选进 spec。

**带 `.draft.` 的文件生成器一律跳过**（`lib/spec.py` 的 `specs()`，各科发现 spec
都走它）。所以草稿躺在 spec 目录里既不进 git、也不会被建成一页。

## 人写的判断（会话产出，全部**进 repo**）

| 栏目 | 目录 | 命名 | 读它的生成器 |
|---|---|---|---|
| 打卡评价 | `storage/spec/english/review/` | `<书>/<课>/pNN.txt` | `src/generator/english/review.py` |
| 词汇默写 | `storage/spec/english/ket/words/`<br>`storage/spec/english/ket/selections/` | `<NN>_<主题>.csv`<br>`<YYYYMMDD>.txt` | `src/generator/english/ket.py` |
| 每日打卡 | `storage/spec/english/homework/` | `<YYYYMMDD>.txt` | `src/generator/english/homework.py` |
| 复述故事 | `storage/spec/english/retell/` | `<故事slug>.txt` | `src/generator/english/retell.py` |
| 语文练习 | `storage/spec/chinese/practice/` | `<YYYYMMDD>.txt` | `src/generator/chinese/build.py` |
| 数学秘籍 | `storage/spec/math/miji/` | `<错因slug>.txt` | `src/generator/math/build.py` |

**只有打卡评价读 spec 之外的数据文件**，其余六个栏目都是 spec 单一输入。
`.read.json` 里每条逐字比对差异都带着**规则分出来的类**：`category`（词尾 / 小词 /
原文印错 / 专名 / 转写乱段 / 自己改对 / 实词 / 漏读 / 多读）、`label`（中文标签）、
`suggest`（建议计错 / 存疑 / 不计错）、`why`（一句话理由）。

⚠️ **口径只在喂数据台那一份**（`../feeder` 的 `Output/DiffTriage.swift`）。
这边要用就**读字段、原样印**：不许在 Python 里再写一遍规则，也不许再翻一遍标签 ——
同一个口径两份实现早晚会漂。老的 `.read.json` 没有这四个字段（音频不在仓库里、
重跑不出来），所以读的时候一律「有就用、没有就跳过」，别拿它当必填。

打卡评价的三份数据里 `.json` 是必需的（缺了直接报错），`.read.json` 和 `.ref.txt` 可选；
`.words.tsv` **目前没有生成器读它**，留着是给人核对时间戳用的。

## 算出来的指标（`storage/result/`）

| 表 | 一行是什么 | 谁写 | 谁读 |
|---|---|---|---|
| `english/review.csv` | 一次朗读的全部指标 | `src/generator/english/review.py` 的 `write_result()` | 趋势页 `dist/english/review/trend.html`；别的工具直接读 CSV |

列就是 `review.py` 已经在算的那些：`accuracy` `wcpm` `per_group` `correct` +
spec 里人给的 `words` `errors` `score` `naep`。**不新增任何计算** —— 这张表是
把内存里算好的数落到盘上，不是第二套算法。

三条硬规矩：

- **全量重算覆盖，不追加。** 追加不幂等（重复构建会重复追加），也没必要 ——
  全部 spec 和测量数据都在 git 里，历史随时能重算一遍。
- **只放纯数据，一个 HTML 标签都不许进来。** 这张表要能直接喂给别的工具
  （notebook、Excel）。混进 `<a>` 就得先清洗才能用。
- **push 它，尽管它可再生** —— 这是「算得出来就不留」那条判据的唯一例外。
  理由不是记住历史（历史能重算），而是 **`git diff` 能看出「改了算法，
  哪些指标动了」**。和 `../feeder` 用 `make test` 拿老站数据回归是同一个思路。

## 一眼看清：哪些扩展名要 push

```
输入      .ref.txt  .read.json  .json  .words.tsv     ← storage/data/：测量数据
          .txt（各栏目）  .csv（ket/words/）        ← storage/spec/：人写的判断
派生      .csv（storage/result/）                   ← 算出来的指标，全量覆盖
候选      .draft.csv  .draft.txt                      ← 核完另存，别直接 push
临时      .marked.png  .page.json  .cards.json
          .board.json  .full.txt                      ← 看完就扔
素材      .mov .mp4 .m4a .jpg .heic                   ← 留本机，永不进仓库
```

`dist/` 整个不进 git —— 每次由 `build.py` 全新构建，本地和 CI 跑同一个脚本。
