# 学习小站 — data 构成

哪条链路产出什么文件、叫什么名、落在哪、要不要 push。

**这是唯一真源。** `src/` 下的生成器、根 `CLAUDE.md`、`.gitignore`、隔壁
`../feeder`（喂数据台）全都照这张表执行 —— 别在别处再维护第二份说明，
四份口径互相漂移正是这张表被写出来的原因。

## 四档去向

| 档 | 要不要 push | 含义 | 谁来清 |
|---|---|---|---|
| **进 repo** | ✅ push | 测量数据 + 人写的判断。站的真正输入 | 不清，长期留着 |
| **候选** | ❌ gitignore | `.draft.*`，机器给的候选。人核对后**另存成正式名**才进 repo | 另存后删掉 draft |
| **临时** | ❌ gitignore | 核对用的过程产物，看一眼就没用了 | 随手删 |
| **素材** | ❌ 不进任何仓库 | 录音、视频、照片。留本机 `inbox/` | 自己归档 |

判据只有一条：**这份东西丢了还能不能再算出来。**

- 测量数据算不出来了 —— 录音和教材照片不进仓库，声学数字、逐词时间戳、
  红线划中的原文，源没了就永远没了。所以必须 push。
- 临时产物随时能从素材再算一遍，留着只是噪音（`.page.json` 一份 85 KB）。
- 候选是**机器的猜测不是结论**，没核过的东西不许混进仓库。

## 名字（slug）的规矩

打卡评价那套名字是「**书 / 课 / 页**」，**斜杠就是目录**：

```
super8/L3/p68   →   src/english/review/data/super8/L3/p68.ref.txt
                    src/english/review/specs/super8/L3/p68.txt
                    dist/english/review/super8/L3/p68.html
```

- **一叠截图一次进来时，名字只填到「书 / 课」**（`super8/L3`），页码机器从页角
  那枚绿圆盘认。图片名（微信编号）和拖进来的顺序都不可靠。
- `review.py` 找数据全靠 `data/<slug>.<ext>` 拼路径，spec 里没有任何字段指向数据文件。
  **名字错了，spec 和数据就配不上对** —— 所以 feeder 在写盘前就校验名字，
  形状不对的名字根本跑不起来，不留到磁盘上再来收拾。

## 机器测出来的（`../feeder` 产出，人不手敲）

| 链路 | 名字填到哪 | 产出 | 落到 | 去向 |
|---|---|---|---|---|
| `read` 朗读录音 | `<书>/<课>/pNN` 人给全 | `.read.json` 主产物（声学 + 转写 + 逐字对齐）<br>`.json` 停顿声学（老站字段）<br>`.words.tsv` 逐词时间戳 | `src/english/review/data/` | **进 repo** |
| `scan` 教材截图 | `<书>/<课>`，**页码机器认** | `.ref.txt` 红线划中的课文原文 | `src/english/review/data/` | **进 repo** |
| | | `.page.json` 整页 OCR + 坐标<br>`.marked.png` 核对图<br>`.full.txt` 整页全文（`--full`） | 同上 | **临时** |
| `cards` 单词卡 | `<NN>_<主题>` | `.draft.csv`（带 BOM 给 Excel） | `src/english/ket/words/` | **候选** → 另存 `<NN>_<主题>.csv` |
| | | `.cards.json` `.cards.marked.png` | 同上 | **临时** |
| `board` 白板 | `<故事slug>` | `.draft.txt` | `src/english/retell/specs/` | **候选** → 另存 `<故事slug>.txt` |
| | | `.board.json` `.board.marked.png` | 同上 | **临时** |
| `pinyin` 生字词 | `<YYYYMMDD>` | `.draft.txt` | `src/chinese/specs/` | **候选** → 另存 `<YYYYMMDD>.txt` |
| `sheet` 口算卷 | 不需要名字 | `full.jpg` `block_N.png` `zoom_x_y.png` | 本机临时目录，**不落 `src/`** | **临时** |
| `check` 判对错 | 不需要名字 | 只打 stdout，不落文件 | — | — |

**为什么 `read` / `scan` 的产出不带 `.draft.`**：那是测量数据，机器算的就是最终值。
`cards` / `board` / `pinyin` 出的是候选 —— 词性、关键词归哪个阶段、多音字按课文读哪个音，
判断在人这儿。

## 人写的判断（会话产出，全部**进 repo**）

| 栏目 | 目录 | 命名 | 读它的生成器 |
|---|---|---|---|
| 打卡评价 | `src/english/review/specs/` | `<书>/<课>/pNN.txt` | `src/english/review.py` |
| 词汇默写 | `src/english/ket/words/`<br>`src/english/ket/selections/` | `<NN>_<主题>.csv`<br>`<YYYYMMDD>.txt` | `src/english/ket.py` |
| 每日打卡 | `src/english/homework/specs/` | `<YYYYMMDD>.txt` | `src/english/homework.py` |
| 复述故事 | `src/english/retell/specs/` | `<故事slug>.txt` | `src/english/retell.py` |
| 语文练习 | `src/chinese/specs/` | `<YYYYMMDD>.txt` | `src/chinese/build.py` |
| 数学秘籍 | `src/math/specs/` | `<错因slug>.txt` | `src/math/build.py` |

**只有打卡评价读 spec 之外的数据文件**，其余六个栏目都是 spec 单一输入。
打卡评价的三份数据里 `.json` 是必需的（缺了直接报错），`.read.json` 和 `.ref.txt` 可选；
`.words.tsv` **目前没有生成器读它**，留着是给人核对时间戳用的。

## 一眼看清：哪些扩展名要 push

```
进 repo   .ref.txt  .read.json  .json  .words.tsv     ← 打卡评价的测量数据
          .txt（各 specs/）   .csv（ket/words/）      ← 人写的判断
候选      .draft.csv  .draft.txt                      ← 核完另存，别直接 push
临时      .marked.png  .page.json  .cards.json
          .board.json  .full.txt                      ← 看完就扔
素材      .mov .mp4 .m4a .jpg .heic                   ← 留本机，永不进仓库
```

`dist/` 整个不进 git —— 每次由 `build.py` 全新构建，本地和 CI 跑同一个脚本。
