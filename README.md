# 学习小站

给孩子做的学习站：语文、英语、数学的练习单和讲义，一处收齐。
手机上翻，A4 打印。→ https://s.hi-ruby.com

## 用法

```bash
make up         # 构建 + 本地预览（手机同 WiFi 扫码就能看）
make pdf        # 构建 + 把打印单导成 PDF
make            # 看全部命令
```

需要 Python 3 和 Chrome（导 PDF 用，没有就只出 HTML）。
装了 `qrencode` 的话 `make up` 会打印二维码方便手机扫。

## 数据流

```
照片 / 录音 / 群公告            素材：留本机 inbox/，不进任何仓库
        │
        │   ../feeder  只做机器算得出的（转正、OCR、声学、逐词对齐）
        ▼
  测量数据  src/**/data/  ──┐   算不出第二遍，所以 push
                            │
  人的判断  src/**/specs/  ─┤   哪几处读错、几分、怎么归组。会话里写，push
                            ▼
                         build.py
                            ▼
                   dist/  HTML + PDF      产物，不进 git
```

两条输入线是有意分开的：机器给数字，人给判断。
只有打卡评价同时吃两条（`data/` + `specs/` 同名同路径配对），
其余栏目只有一份 spec。

产物一律不提交 —— 本地 `make build` 和线上 GitHub Actions 跑的是同一个
`build.py`，「本地能出」就等于「线上能出」。

哪条链路产出什么文件、要不要 push，见 [DATA.md](DATA.md)（唯一真源）。

## 结构

- `src/` — 内容源（spec、讲义、样式）
- `lib/` — Python 生成器
- `dist/` — 产物，**不进 git**；线上由 GitHub Actions 构建部署

改内容改 `src/`，加栏目改 `build.py` 顶部的 `SUBJECTS`。
详细约定见 `CLAUDE.md`。
