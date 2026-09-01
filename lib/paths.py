"""仓库各层的位置 —— **改目录名只改这一个文件**。

    storage/data/     机器测的（../feeder 产出，源没了就算不出来 → push）
    storage/spec/     人写的判断和内容（会话产出 → push）
    storage/result/   算出来的指标（可再生，push 当回归基准）
    src/              代码 + 资产（一个内容文件都不放）
      generator/      各科生成器 .py
      templates/      HTML / SVG 标记
      assets/         *.css、CNAME
    inbox/            本机素材（录音 / 照片）。**永不进任何仓库**
    dist/             产物，不进 git，每次全新构建

四档去向和各链路产出什么文件，见根目录 DATA.md（唯一真源）。

各科生成器一律走 `paths.spec(...)` / `paths.data(...)` 取路径，**别再用
`Path(__file__).parent` 往下拼** —— 代码在 src/ 下，数据在 storage/ 下，
两棵树的相对关系只在这儿写一次。
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STORAGE = ROOT / "storage"
DATA = STORAGE / "data"
SPEC = STORAGE / "spec"
RESULT = STORAGE / "result"

SRC = ROOT / "src"
GEN = SRC / "generator"          # 各科生成器：generator/<科>/build.py
TEMPLATES = SRC / "templates"
ASSETS = SRC / "assets"
DIST = ROOT / "dist"

# 本机素材（录音、作业照片）。**永不进任何仓库** —— 见 DATA.md 的「素材」那一档。
# 默认 inbox/（.gitignore 里就有），素材放在别处就 `export STUDY_INBOX=~/Downloads/study`，
# 或者干脆软链一条过来：`ln -s ~/Downloads/study inbox`。
# CI 上这个目录不存在，凡是依赖它的东西都会自动降级 —— 那正是我们要的：
# 录音只在本地听得到，线上一个字节都没有。
INBOX = Path(os.environ.get("STUDY_INBOX") or ROOT / "inbox").expanduser()


def gen(*parts: str) -> Path:
    """src/generator/<...> —— 各科的生成器代码。"""
    return GEN.joinpath(*parts)


def data(*parts: str) -> Path:
    """storage/data/<...> —— 机器测出来的。"""
    return DATA.joinpath(*parts)


def spec(*parts: str) -> Path:
    """storage/spec/<...> —— 人写的判断。"""
    return SPEC.joinpath(*parts)


def result(*parts: str) -> Path:
    """storage/result/<...> —— 算出来的指标。"""
    return RESULT.joinpath(*parts)


def material(name: str) -> Path | None:
    """在本机素材堆里按**文件名**找一份原始素材，找不到给 None。

    `read.json` 只记了源文件名（`9e43….mp4`），没记路径 —— 素材本来就不进仓库，
    记了路径也是别人机器上的。所以这儿递归找一遍，找不到就当没有。

    **不存在「找不到就报错」这一说**：CI 上永远找不到，那是设计的一部分。
    """
    if not name or not INBOX.is_dir():
        return None
    hit = INBOX / name
    return hit if hit.is_file() else next(iter(sorted(INBOX.rglob(name))), None)
