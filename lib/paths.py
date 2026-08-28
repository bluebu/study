"""仓库各层的位置 —— **改目录名只改这一个文件**。

    storage/data/     机器测的（../feeder 产出，源没了就算不出来 → push）
    storage/spec/     人写的判断和内容（会话产出 → push）
    storage/result/   算出来的指标（可再生，push 当回归基准）
    src/              代码 + 资产（生成器 .py、assets/*.css、CNAME）
    dist/             产物，不进 git，每次全新构建

四档去向和各链路产出什么文件，见根目录 DATA.md（唯一真源）。

各科生成器一律走 `paths.spec(...)` / `paths.data(...)` 取路径，**别再用
`Path(__file__).parent` 往下拼** —— 代码在 src/ 下，数据在 storage/ 下，
两棵树的相对关系只在这儿写一次。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STORAGE = ROOT / "storage"
DATA = STORAGE / "data"
SPEC = STORAGE / "spec"
RESULT = STORAGE / "result"

SRC = ROOT / "src"
DIST = ROOT / "dist"


def data(*parts: str) -> Path:
    """storage/data/<...> —— 机器测出来的。"""
    return DATA.joinpath(*parts)


def spec(*parts: str) -> Path:
    """storage/spec/<...> —— 人写的判断。"""
    return SPEC.joinpath(*parts)


def result(*parts: str) -> Path:
    """storage/result/<...> —— 算出来的指标。"""
    return RESULT.joinpath(*parts)
