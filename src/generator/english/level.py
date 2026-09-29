"""朗读水平：拿**全部历史**估「现在在什么水平」+ 逐月统计。趋势页顶上那两块。

单看最新一次不行：同一个孩子，一次朗读的准确率能差 ±3 个百分点、WCPM 能差 ±10，
课文换一段就变。所以「现在的水平」要从历史里估，而且估法要**回测过**：

── 回测（walk-forward）

站在第 i 次之前，只用前 i 次的数据预测第 i 次，看平均差多少（MAE）。候选：

    上一次        只看最近一次
    全部平均      按词数加权的历史平均
    指数平均 h    半衰期 h 次：越近的越重，h 次之前的权重减半

从第 MIN_HIST+1 次开始预测，MAE 最小的那个就是「现在的水平」的估法 ——
**模型是数据挑的，不是拍的**。9/29 那 23 次挑出来的是长半衰期 / 全部平均：
说明一次一次的起伏大多是波动，还看不出真的变化。

MAE 同时就是「一次朗读的正常波动」：下一次落在 水平 ± MAE 里，都不算进步或退步。

── 趋势

准确率 / WCPM / 分数对日期做最小二乘，斜率折成「每 30 天」，|t| < 2 就写「看不出在涨或在跌」。
23 个点的斜率很不稳，**t 不到 2 不下结论** —— 持平就是持平（英语 CLAUDE.md 准则第 1 条）。

── 为什么不按课文难度校正

试过：准确率和课文蓝思的相关是 +0.29（难的反而读得准一点），WCPM 是 0.01。
估算的蓝思解释不了她的准确率，硬放进模型只会加噪音。数据多了再回测一次。

── 逐月

月内**合计**，不是平均的平均：准确率 = Σ读对 ÷ Σ词数，WCPM = Σ读对 ÷ Σ时长 × 60。
月与月的差，超过两个月「月均值波动」合起来的 2 倍才标「超出波动」。
"""

from __future__ import annotations

import math
import statistics as st
from datetime import date

MIN_HIST = 3                      # 至少有 3 次历史才开始预测
HALF_LIVES = (2, 3, 4, 6, 8, 12)

# 三项：键、名字、小数位、单位
METRICS = (("accuracy", "准确率", 1, "%"), ("wcpm", "每分钟正确词", 0, ""), ("score", "分数", 0, ""))


def _ewma(ys, ws, hl):
    a, num, den = 0.5 ** (1 / hl), 0.0, 0.0
    for y, w in zip(ys, ws):
        num, den = num * a + y * w, den * a + w
    return num / den


def _ewma_neff(ws, hl):
    """指数平均的有效样本数 (Σw)² / Σw² —— 算水平本身有多不确定用。"""
    a = 0.5 ** (1 / hl)
    k = [w * a ** (len(ws) - 1 - i) for i, w in enumerate(ws)]
    return sum(k) ** 2 / sum(x * x for x in k)


def _models():
    yield "上一次", lambda ys, ws: ys[-1], lambda ws: 1.0
    yield "全部平均", lambda ys, ws: sum(y * w for y, w in zip(ys, ws)) / sum(ws), \
        lambda ws: sum(ws) ** 2 / sum(w * w for w in ws)
    for h in HALF_LIVES:
        yield f"指数平均（半衰期 {h} 次）", (lambda h: lambda ys, ws: _ewma(ys, ws, h))(h), \
            (lambda h: lambda ws: _ewma_neff(ws, h))(h)


def backtest(ys: list[float], ws: list[float]) -> list[dict]:
    """每个候选的回测 MAE，按 MAE 从小到大。"""
    out = []
    for name, pred, neff in _models():
        errs = [abs(pred(ys[:i], ws[:i]) - ys[i]) for i in range(MIN_HIST, len(ys))]
        out.append({"name": name, "mae": st.mean(errs), "pred": pred, "neff": neff})
    return sorted(out, key=lambda m: m["mae"])


def trend(days: list[int], ys: list[float]) -> dict:
    mx, my = st.mean(days), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in days)
    if len(ys) < 4 or not sxx:
        return {"per30": 0.0, "t": 0.0}
    b = sum((x - mx) * (y - my) for x, y in zip(days, ys)) / sxx
    res = [y - (my + b * (x - mx)) for x, y in zip(days, ys)]
    se = math.sqrt(sum(e * e for e in res) / (len(ys) - 2) / sxx)
    return {"per30": b * 30, "t": b / se if se else 0.0}


def fmt(v: float, digits: int) -> str:
    return f"{v:.{digits}f}" if digits else str(round(v))


def assess(rows: list[dict]) -> dict:
    """rows = review.csv 读回来的行（字符串），按时间排好。"""
    d0 = date.fromisoformat(rows[0]["date"])
    days = [(date.fromisoformat(r["date"]) - d0).days for r in rows]
    ws = [float(r["words"]) for r in rows]
    out = []
    for key, name, digits, unit in METRICS:
        ys = [float(r[key]) for r in rows]
        bt = backtest(ys, ws)
        best, last = bt[0], next(m for m in bt if m["name"] == "上一次")
        level = best["pred"](ys, ws)
        # 水平本身的不确定：历史的离散度 ÷ √有效样本数，取 ±2 倍
        sd = st.pstdev(ys)
        band = 2 * sd / math.sqrt(best["neff"](ws))
        tr = trend(days, ys)
        if abs(tr["t"]) < 2:
            verdict, cls = "看不出在涨或在跌", "flat"
        else:
            up = tr["per30"] > 0
            verdict = f"在{'涨' if up else '跌'}，每月约 {'+' if up else '−'}{fmt(abs(tr['per30']), digits)}{unit}"
            cls = "up" if up else "down"
        out.append({
            "key": key, "name": name, "unit": unit,
            "level": fmt(level, digits), "band": fmt(max(band, 10 ** -digits if digits else 1), digits),
            "swing": fmt(best["mae"], digits),
            "latest": fmt(ys[-1], digits),
            "model": best["name"], "mae": fmt(best["mae"], digits),
            "mae_last": fmt(last["mae"], digits),
            "verdict": verdict, "cls": cls,
            "per30": fmt(tr["per30"], digits), "t": f"{tr['t']:.1f}",
        })
    return {"n": len(rows), "tested": len(rows) - MIN_HIST, "metrics": out}


def monthly(rows: list[dict]) -> list[dict]:
    """逐月合计，和上个月比。"""
    months: dict[str, list[dict]] = {}
    for r in rows:
        months.setdefault(r["date"][:7], []).append(r)
    out, prev = [], None
    for ym, sub in sorted(months.items()):
        W = sum(float(r["words"]) for r in sub)
        C = sum(float(r["correct"]) for r in sub)
        D = sum(float(r["duration"]) for r in sub)
        lex = [(float(r["lexile"]), float(r["words"])) for r in sub if r.get("lexile")]
        acc_s = [float(r["accuracy"]) for r in sub]
        wc_s = [float(r["wcpm"]) for r in sub]
        m = {
            "label": f"{int(ym[5:])} 月", "n": len(sub), "words": int(W),
            "acc": C / W * 100, "wcpm": C / D * 60,
            "score": st.mean(float(r["score"]) for r in sub),
            "lexile": round(sum(l * w for l, w in lex) / sum(w for _, w in lex) / 10) * 10 if lex else None,
            # 月均值的波动：单次的标准差 ÷ √次数
            "se_acc": st.stdev(acc_s) / math.sqrt(len(sub)) if len(sub) > 1 else None,
            "se_wcpm": st.stdev(wc_s) / math.sqrt(len(sub)) if len(sub) > 1 else None,
        }
        for k, se, digits in (("acc", "se_acc", 1), ("wcpm", "se_wcpm", 0)):
            if prev is None:
                m[f"d_{k}"] = None
                continue
            delta = m[k] - prev[k]
            noise = 2 * math.sqrt((m[se] or 0) ** 2 + (prev[se] or 0) ** 2)
            m[f"d_{k}"] = {
                "text": f"{'+' if delta > 0 else '−' if delta < 0 else '±'}{fmt(abs(delta), digits)}",
                "cls": "flat" if abs(delta) <= noise else ("up" if delta > 0 else "down"),
                "tip": "在波动内" if abs(delta) <= noise else "超出波动",
            }
        out.append(m)
        prev = m
    for m in out:
        m["acc_s"] = f"{m['acc']:.1f}%"
        m["wcpm_s"] = str(round(m["wcpm"]))
        m["score_s"] = str(round(m["score"]))
    return out
