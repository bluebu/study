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
装依赖：`pip install -r requirements.txt`（只有一个 Jinja2，做 HTML 模板）。
装了 `qrencode` 的话 `make up` 会打印二维码方便手机扫。

## 数据流

```
照片 / 录音 / 群公告            素材：留本机 inbox/，不进任何仓库
        │
        │   ../feeder  只做机器算得出的（转正、OCR、声学、逐词对齐）
        ▼
  测量数据  storage/data/  ──┐   算不出第二遍，所以 push
                             │
  人的判断  storage/spec/  ──┤   哪几处读错、几分、怎么归组。会话里写，push
                             ▼
                          build.py
                             │
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
  storage/result/  算出来的指标            dist/  单页报告、练习单
  （可再生，push 当回归基准）                 HTML + PDF，不进 git
        │
        └──► dist/  趋势页、汇总列表
```

两条输入线是有意分开的：机器给数字，人给判断。
只有打卡评价同时吃两条（`data/` + `spec/` 同名同路径配对），
其余栏目只有一份 spec。

**原始数据落地一次、可以被计算多次** —— 这是分层的全部理由。改了算法重跑构建，
报告和 `storage/result/` 里的指标都变，`storage/data/` 一个字不动。

`storage/result/` 是**旁路不是必经**：单页报告仍直接吃 spec 全文 + 完整测量 JSON
（评语要逐字印在纸上、停顿地图要每次歇气的起止时刻），指标表装不下这些。

产物一律不提交 —— 本地 `make build` 和线上 GitHub Actions 跑的是同一个
`build.py`，「本地能出」就等于「线上能出」。

哪条链路产出什么文件、要不要 push，见 [DATA.md](DATA.md)（唯一真源）。

## 结构

- `storage/` — 数据层，累积、push。`data/` 机器测的 / `spec/` 人写的 / `result/` 算出来的
- `src/` — 代码 + 资产（生成器 `.py`、`templates/*.html`、`assets/*.css`），
  **一个内容文件都不放**。标记全在 `templates/`，Python 里不拼 HTML
- `lib/` — 通用库。各层的位置全在 `lib/paths.py` 一处，改目录名只改它
- `dist/` — 产物，**不进 git**；线上由 GitHub Actions 构建部署

改内容改 `storage/`，改版式改 `src/templates/`，改样式改 `src/assets/`，
加栏目改 `build.py` 顶部的 `SUBJECTS`。
详细约定见 `CLAUDE.md`。
