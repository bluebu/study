#!/usr/bin/env python3
"""口算卷照片 → 能看清手写答案的图。

手机拍的卷子有两个坎：纸是横躺的，字又小。这个脚本只做这两件事，
别的（识别、判对错）交给会话和 check.py。

    # 1) 先定方向：出三张缩略图，Read 一张就知道该转哪边
    python3 crop.py 照片.jpg -o out/

    # 2) 转正后按高度切块放大，逐块 Read 着抄题
    python3 crop.py 照片.jpg -o out/ --rot cw --blocks 3

    # 3) 某个答案看不准（0.07 还是 0.97）就局部放大，坐标按转正后的图量
    python3 crop.py 照片.jpg -o out/ --rot cw --zoom 215,558,330,600 --scale 10

⚠️ HEIC 转图别用 sips --cropOffset（偏移不生效，永远裁中心），裁切一律走 PIL。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROT = {"cw": Image.ROTATE_270, "ccw": Image.ROTATE_90, "180": Image.ROTATE_180}
MAX_EDGE = 4000          # 放太大反而看不动，也拖慢 Read


def _save(im: Image.Image, path: Path, scale: float, sharpen: bool) -> Path:
    if scale != 1:
        scale = min(scale, MAX_EDGE / max(im.size))
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    if sharpen:
        im = ImageEnhance.Contrast(im).enhance(2.2).filter(ImageFilter.SHARPEN)
    im.save(path)
    print(f"  → {path}  {im.width}×{im.height}")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("photo")
    ap.add_argument("-o", "--out", default=".", help="输出目录")
    ap.add_argument("--rot", choices=["cw", "ccw", "180", "none"],
                    help="转正方向；不给就出三张缩略图让人挑")
    ap.add_argument("--blocks", type=int, default=0, help="转正后按高度切几块")
    ap.add_argument("--zoom", help="局部放大 x1,y1,x2,y2（坐标按转正后的图）")
    ap.add_argument("--scale", type=float, default=0, help="放大倍数（块默认 3，局部默认 8）")
    args = ap.parse_args()

    src = Path(args.photo)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    print(f"{src.name}  {im.width}×{im.height}")

    # 没定方向：出三张缩略图，Read 一张定方向再回来
    if not args.rot:
        for k in ("cw", "ccw", "180"):
            _save(im.transpose(ROT[k]), out / f"full_{k}.jpg", 1, False)
        print("Read 一张看哪个方向正，再带 --rot 跑第二遍")
        return 0

    if args.rot != "none":
        im = im.transpose(ROT[args.rot])
    _save(im, out / "full.jpg", 1, False)

    if args.zoom:
        x1, y1, x2, y2 = (int(v) for v in args.zoom.split(","))
        _save(im.crop((x1, y1, x2, y2)), out / f"zoom_{x1}_{y1}.png",
              args.scale or 8, True)

    if args.blocks:
        n = args.blocks
        step = im.height / n
        pad = im.height * 0.02          # 块间留重叠，别把一行题劈成两半
        for i in range(n):
            top = max(0, int(i * step - pad))
            bot = min(im.height, int((i + 1) * step + pad))
            _save(im.crop((0, top, im.width, bot)), out / f"block_{i + 1}.png",
                  args.scale or 3, False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
