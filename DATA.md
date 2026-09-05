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

`inbox/` 在 `.gitignore` 里**不带斜杠**：素材堆在别处时这儿往往是一条软链
（`ln -s ~/Downloads/study inbox`），而软链在 git 眼里是文件，`inbox/` 挡不住。

### 素材的唯一一处下游：报告里点词听读音

打卡评价的 `[比对]` 里点词能听音，两种颜色两个音源（`review-play.js`）：

| 点哪个 | 听到的 | 音源 | 时刻从哪来 |
|---|---|---|---|
| **红**（她读的） | 她自己读的那一句 | `read.json` 里记的源录音 | `alignment.refTimes` + 差异条目的 `start`/`end` |
| **绿**（原文） | 课本配套朗读里那一句 | `pNN.ref.json` 里记的 `source` | `pNN.ref.json` 的逐词 `start`/`end` |

音源都不是新落的文件 —— `build.py` 按 JSON 里记的**文件名**去 `inbox/` 找，
在 `dist/` 里**软链**一条过去（不拷贝：源文件几十兆，而 `dist/` 本来就不进 git）。

绿词那条还有一半取决于原文是哪来的：`ref`（配套朗读转写）才有真人音，
`scan`（教材截图 OCR）只有合成音 —— 超8 走的是后者，所以那些页的绿词
点了仍旧是浏览器念。**同一份报告里两种混着出现是正常的。**

**这条链路只在本地成立，这是设计不是缺陷**：CI 上 `inbox/` 不存在 → `paths.material()`
返回 None → 页面里一个 `<audio>` 都不出，点词退回去念那个词（浏览器 TTS，零字节）。
不需要任何开关，也就没有「忘了关」把孩子的声音、或者版权音频带上公网的可能 ——
线上那份报告永远是纯文字的。

判据只有一条：**这份东西丢了还能不能再算出来。** 算不出来的必须 push，
算得出来的一律不留 —— `storage/result/` 是唯一的例外，理由在下面那节。

- 测量数据算不出来了 —— 录音和教材照片不进仓库，声学数字、逐词时间戳、
  划线划中的原文，源没了就永远没了。所以必须 push。
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
  奇偶也是判据：**对开页左页偶数、右页奇数**，读数对不上就当没读出来
  （6 和 9 只差一个方向，Vision 在 35px 的圆盘上真会读反）。
- **划线红笔黑笔都认**（第一册橙红马克笔，第二册直接在数字教材上画黑线），
  按「哪支笔划中的词多」自己挑。整页 OCR 之前先把线擦掉 ——
  线画在字上，不擦那一行会整行读坏。口径在 `PageScanner.Pen`。
- **换册不换书名**：超8 **每 3 课一册**（L1–L3 第一册、L4–L6 第二册……），
  课次接着数、页码每册重新从 1 起。同一课自己一层目录，所以第二册的 p6
  和第一册 L1 的 p6 不会撞 —— 书名仍旧 `super8`，只是多一层 `L4`。
  **课次是名字里唯一定得住册次的东西**：打卡单抬头没写 `Lesson N` 时
  feeder 直接不给名字（不拿「最近那一课」凑，那样会把第二册的页落进 L3）。
- `review.py` 找数据全靠 `data/<slug>.<ext>` 拼路径，spec 里没有任何字段指向数据文件。
  **名字错了，spec 和数据就配不上对** —— 所以 feeder 在写盘前就校验名字，
  形状不对的名字根本跑不起来，不留到磁盘上再来收拾。

## 机器测出来的（`../feeder` 产出，人不手敲）

| 链路 | 名字填到哪 | 产出 | 落到 | 去向 |
|---|---|---|---|---|
| `read` 朗读录音 | `<书>/<课>/pNN`；一次读了几页写区间 `pNN-MM` | `.read.json` 主产物（声学 + 转写 + 逐字对齐）<br>`.json` 停顿声学（老站字段）<br>`.words.tsv` 逐词时间戳<br>`.read.json` 里的 `pages`：这次读了哪几页、每页多少词错几处（**从同一份对齐派生，不是分开测的**）<br>`.read.json` 里的 `refSuspects`：原文里 OCR 认得可疑的词，从 `page.json` 取回 —— `page.json` 是临时的、会被清掉，这份进 repo 的才是长期凭据 | `storage/data/english/review/` | **进 repo** |
| `read --draft` | 同上 | `.draft.txt` spec 候选（`[比对]`/`[卡壳]`/`[磕巴]` 和文件头填好，判断留 `⟨⟩`） | `storage/spec/english/review/` | **候选** → 另存 `pNN.txt` |
| `scan` 教材截图 | `<书>/<课>`，**页码机器认** | `.ref.txt` 手画线划中的课文原文（红笔黑笔都认，见下） | `storage/data/english/review/` | **进 repo** |
| | | `.page.json` 整页 OCR + 坐标 + `spellFlags`（OCR 认得可疑的词）<br>`.marked.png` 核对图<br>`.suspect-<词>.png` 可疑词裁出来放大 6 倍，一个词一张<br>`.full.txt` 整页全文（`--full`） | 同上 | **临时** |
| `ref` 原文朗读 | `<书>/<课>`，**页码切完段人填** | `.ref.txt` 整本原文，按朗读自己的停顿切成段（段间空行）<br>`.ref.json` 段表（起止时刻 / 词数 / 段前停多久 / 占第几到第几个词）+ 整本的逐词时刻 + 要人核的词（把握低或拼不出，带识别器候选） | `storage/data/english/review/` | **进 repo** |
| `ref --pages` | 同上 | 直接落成 `pNN.ref.txt` 一页一份（`+` 并进上一段、`-` 丢掉）<br>`pNN.ref.json` 那一页的**逐词时刻** + 音源文件名 —— 报告里绿词播真人音靠它<br>`book.ref.json` 放进那一课的目录，记的是「这些 pNN 是怎么切出来的」（切了页就不再留一份逐词时刻，那是页文件的事） | 同上 | **进 repo** |
| `cards` 单词卡 | `<NN>_<主题>` | `.draft.csv`（带 BOM 给 Excel） | `storage/spec/english/ket/words/` | **候选** → 另存 `<NN>_<主题>.csv` |
| | | `.cards.json` `.cards.marked.png` | 同上 | **临时** |
| `board` 白板 | `<故事slug>` | `.draft.txt` | `storage/spec/english/retell/` | **候选** → 另存 `<故事slug>.txt` |
| | | `.board.json` `.board.marked.png` | 同上 | **临时** |
| `pinyin` 生字词 | `<YYYYMMDD>` | `.draft.txt` | `storage/spec/chinese/practice/` | **候选** → 另存 `<YYYYMMDD>.txt` |
| `sheet` 口算卷 | 不需要名字 | `full.jpg` `block_N.png` `zoom_x_y.png` | 本机临时目录，**不落 `storage/`** | **临时** |
| `check` 判对错 | 不需要名字 | 只打 stdout，不落文件 | — | — |

**原文有两条来路，产出同一样东西**：`scan` 从教材截图 OCR，`ref` 从配套的官方朗读
音频转写，落的都是 `.ref.txt`，下游 `read --ref` 认不出区别也不需要认出。
挑哪条看素材：书有电子版或拍得清楚 → `scan`（自带页边界，最省事）；
只有朗读音频、或者拿不准手上的电子版是不是孩子那一档 → `ref`（**念的就是她那一版**）。

`ref` 的代价是音频没有页边界，所以按朗读自己的停顿切段 —— 念的人翻页换节都会停。
实测 Wonders G3 那本 158 次停顿里 ≥1.5 秒的 19 次**每一次都是真的页/节边界**
（1.2–1.5 秒之间一次都没有），切出来的三页词数和老站那份人工核过的原文**逐个精确相等**。
⚠️ 切段**必须用声学停顿，不能用转写词之间的时间差** —— 识别器的时间戳是连着的，
静音被前后两个词的区间抻满了，同一份音频里词间隔 >1.2 秒的**一次都没有**。

`ref` 比 `scan` 多给一样东西：**每个原文词在朗读里的起止时刻**（`pNN.ref.json`），
报告里绿词播真人音就靠它。下标和 `.ref.txt` 的词序一一对应，
和孩子那份 `alignment.refTimes` 平行 —— 同一个下标，绿词播录音棚那一句、
红词播她读的那一句。

⚠️ **`.ref.txt` 是人核过的，词数可能和时刻对不上**：转写把 `Leimert` 听成
`Le Mert`，人改回来那一页就少两个词。所以 study 那边**逐页比一次词数**，
不等就把那一页的时刻整页丢掉、绿词退回浏览器念（wonders3/u1w3 十四页里
p16 正是这一种）。错一位在页面上只表现成「点绿词听到别处的声音」，比不给点更糟。

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
| 一周课表 | `storage/spec/schedule/week/` | `<YYYYMMDD>.txt` | `src/generator/schedule/build.py` |

**只有打卡评价读 spec 之外的数据文件**，其余七个栏目都是 spec 单一输入。
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
| `english/review-errors.csv` | **一行一处错**：页 / 日期 / 书 / 原文词 / 类型（八类之一） | 同上 | 趋势页的「错在哪一类」和「先解决这三个」 |

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
临时      .marked.png  .page.json  .suspect-*.png  .cards.json
          .board.json  .full.txt                      ← 看完就扔
素材      .mov .mp4 .m4a .jpg .heic                   ← 留本机，永不进仓库
```

`dist/` 整个不进 git —— 每次由 `build.py` 全新构建，本地和 CI 跑同一个脚本。
