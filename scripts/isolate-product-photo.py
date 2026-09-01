#!/usr/bin/env python3
"""Remove background and export web-ready JPG + WebP on brand cream."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from rembg import remove

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BRAND_CREAM = (250, 245, 236)  # --cream


def load_rgb(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def isolate(
    src: Path,
    out_stem: str,
    *,
    max_edge: int = 1600,
    padding: float = 0.06,
    contrast: float = 1.06,
    color: float = 1.03,
) -> tuple[Path, Path]:
    rgb = load_rgb(src)
    # Downscale before rembg for speed on huge iPhone shots
    w, h = rgb.size
    if max(w, h) > 2200:
        scale = 2200 / max(w, h)
        rgb = rgb.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    cutout = remove(rgb)  # RGBA
    if cutout.mode != "RGBA":
        cutout = cutout.convert("RGBA")

    alpha = cutout.split()[-1]
    bbox = alpha.getbbox()
    if not bbox:
        raise SystemExit(f"No subject detected in {src}")

    cutout = cutout.crop(bbox)
    cw, ch = cutout.size
    pad = int(max(cw, ch) * padding)
    canvas = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (*BRAND_CREAM, 255))
    canvas.paste(cutout, (pad, pad), cutout)

    img = canvas.convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(color)

    w, h = img.size
    if max(w, h) > max_edge:
        if w >= h:
            img = img.resize((max_edge, int(h * max_edge / w)), Image.Resampling.LANCZOS)
        else:
            img = img.resize((int(w * max_edge / h), max_edge), Image.Resampling.LANCZOS)

    jpg = ASSETS / f"{out_stem}.jpg"
    webp = ASSETS / f"{out_stem}.webp"
    img.save(jpg, "JPEG", quality=84, optimize=True, progressive=True)
    img.save(webp, "WEBP", quality=82, method=6)
    print(f"  {src.name} → {jpg.name} ({jpg.stat().st_size // 1024} KB) + webp")
    return jpg, webp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("out_stem")
    parser.add_argument("--max", type=int, default=1600)
    args = parser.parse_args()
    isolate(Path(args.src), args.out_stem, max_edge=args.max)


if __name__ == "__main__":
    main()
