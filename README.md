# 学习小站

给孩子做的学习站：语文、英语、数学的练习单和讲义，一处收齐。
手机上翻，A4 打印。→ https://study.hi-ruby.com

## 用法

```bash
make up         # 构建 + 本地预览（手机同 WiFi 扫码就能看）
make pdf        # 构建 + 把打印单导成 PDF
make            # 看全部命令
```

需要 Python 3 和 Chrome（导 PDF 用，没有就只出 HTML）。
装了 `qrencode` 的话 `make up` 会打印二维码方便手机扫。

## 结构

- `src/` — 内容源（spec、讲义、样式）
- `lib/` — Python 生成器
- `dist/` — 产物，**不进 git**；线上由 GitHub Actions 构建部署

改内容改 `src/`，加栏目改 `build.py` 顶部的 `SUBJECTS`。
详细约定见 `CLAUDE.md`。
