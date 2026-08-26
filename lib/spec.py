"""spec DSL 解析器 —— 三科打印单的共同输入格式。

三段式（老站 chinese / english 各栏目原本各写一份，这里收成一份）：

    # 这一行是卷名（首个 # 行）
    # 后续 # 行都是注释
    date: 8月25日            ← 文件头：key: value
    copies: 2

    [生字] copies=3           ← 区块：[名] 抬头文字 | 右标签  key=value
    陡=dǒu, 崖=yá,
    麻雀=má què               ← 项行，可跨行，支持 , ， 、 三种分隔
        今天实际写了 __ 遍     ← 缩进行：说明行，原样交给各科处理

设计边界：本模块只解析**骨架**（文件头 / 卷名 / 区块 / 属性 / 原始行），
不碰区块内容的语义 —— 语文的「字=拼音」、英语的「* + __ <<N>>」、
抽查单的「ask: 题面 | 答案」差异太大，各科自己解释自己的行。
过度抽象比重复更难改。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 项行的分隔符：中英文逗号 + 顿号
ITEM_SEPS = ",，、"

# 行内属性 key= 的位置。key 限定 ASCII 词，避免误伤中文里的等号
_ATTR_KEY = re.compile(r"(?:^|\s)([A-Za-z_][\w-]*)\s*=")


@dataclass
class Block:
    """一个 [区块]。"""

    name: str                                  # [] 里的区块名，如「生字」「听」
    head: str = ""                             # [] 之后、第一个 key= 之前的文字
    tag: str = ""                              # head 里 | 右边的部分（右侧小标签）
    attrs: dict[str, str] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)   # 区块内原始行（保留缩进）

    def attr(self, key: str, default=None):
        return self.attrs.get(key, default)

    def items(self, seps: str = ITEM_SEPS) -> list[tuple[str, str]]:
        """把非缩进的项行拆成 [(左, 右)]，支持跨行。

        「陡=dǒu, 麻雀=má què」 → [("陡","dǒu"), ("麻雀","má què")]
        没有等号的项右边为空串：「观潮」 → [("观潮","")]
        """
        flat = " ".join(ln.strip() for ln in self.lines if ln.strip() and not ln[:1].isspace())
        out = []
        for chunk in re.split(f"[{re.escape(seps)}]", flat):
            chunk = chunk.strip()
            if not chunk:
                continue
            left, _, right = chunk.partition("=")
            out.append((left.strip(), right.strip()))
        return out

    def notes(self) -> list[str]:
        """缩进行（说明行），去掉缩进后原样返回。"""
        return [ln.strip() for ln in self.lines if ln[:1].isspace() and ln.strip()]


@dataclass
class Spec:
    path: Path
    title: str = ""                            # 首个 # 行，约定为卷名
    meta: dict[str, str] = field(default_factory=dict)
    blocks: list[Block] = field(default_factory=list)

    def get(self, key: str, default=None):
        return self.meta.get(key, default)

    def int_(self, key: str, default: int) -> int:
        """取整数设置项（copies / cell / size / times 这类排版旋钮）。"""
        raw = self.meta.get(key)
        if raw is None or raw == "":
            return default
        try:
            return int(str(raw).strip())
        except ValueError:
            die(f"{self.path.name}: 设置项 {key} 要是整数，现在是 {raw!r}")


def die(msg: str) -> None:
    """spec 写错就明确报错退出，别猜着往下跑。"""
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def _split_attrs(text: str) -> tuple[str, dict[str, str]]:
    """把 '听外教音频 | 120 分钟  copies=3 pass=错 ≤ 1 个' 拆成
    ('听外教音频 | 120 分钟', {'copies':'3', 'pass':'错 ≤ 1 个'})

    值可以带空格：按下一个 key= 的位置切断。
    所以老站那条「pass= 必须写在属性最后」的限制在这里不存在。
    """
    hits = list(_ATTR_KEY.finditer(text))
    if not hits:
        return text.strip(), {}

    head = text[: hits[0].start()].strip()
    attrs: dict[str, str] = {}
    for i, m in enumerate(hits):
        key = m.group(1)
        val_from = m.end()
        val_to = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        attrs[key] = text[val_from:val_to].strip()
    return head, attrs


def parse(path: str | Path) -> Spec:
    """读一份 spec 文件。"""
    path = Path(path)
    if not path.exists():
        die(f"spec 不存在：{path}")

    spec = Spec(path=path)
    current: Block | None = None
    in_body = False          # 见到第一个 [区块] 之后，文件头就结束了

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue

        # 注释 / 卷名
        if line.lstrip().startswith("#"):
            text = line.lstrip("# \t").strip()
            if not spec.title and text:
                spec.title = text
            continue

        # 区块头 [名] ...
        m = re.match(r"\s*\[([^\]]+)\]\s*(.*)$", line)
        if m:
            in_body = True
            rest, attrs = _split_attrs(m.group(2))
            head, _, tag = rest.partition("|")
            current = Block(
                name=m.group(1).strip(),
                head=head.strip(),
                tag=tag.strip(),
                attrs=attrs,
            )
            spec.blocks.append(current)
            continue

        # 文件头 key: value（只在第一个区块之前，且不带缩进）
        if not in_body and not line[:1].isspace():
            key, sep, val = line.partition(":")
            if sep and re.fullmatch(r"[A-Za-z_][\w-]*", key.strip()):
                spec.meta[key.strip()] = val.strip()
                continue

        # 其余都是区块内容行，原样保留（缩进有意义）
        if current is None:
            die(f"{path.name}: 第一个 [区块] 之前出现了内容行：{line.strip()!r}")
        current.lines.append(line)

    return spec


def latest(spec_dir: str | Path, pattern: str = "*.txt") -> Path:
    """spec_dir 里最近改动的一份 spec。

    不给文件名时的默认行为 —— 老站四个脚本各自复制了一份这个逻辑。
    """
    spec_dir = Path(spec_dir)
    found = sorted(spec_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not found:
        die(f"{spec_dir}/ 里没有 {pattern}")
    return found[-1]
