#!/usr/bin/env python3
"""Build printable PLA leather-stamp STLs from Corbett mark bitmaps.

Raised-relief stamps, mirrored so the leather imprint reads correctly.
Units: millimeters. Outputs only the mirrored print-ready files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from stl import mesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "stamps" / "stl"
LOGOS = ROOT / "assets" / "logos"

SIZES_IN = (0.75, 1.0, 1.25, 1.5, 2.0)
BASE_THICKNESS_MM = 2.4
RELIEF_HEIGHT_MM = 1.8
EDGE_PAD_MM = 1.2
# Cap grid resolution so STLs stay downloadable / slice-friendly
MAX_GRID = 140


def load_mask(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    g = ImageOps.autocontrast(Image.alpha_composite(bg, im).convert("L"))
    bw = g.point(lambda x: 255 if x < 190 else 0)
    bw = bw.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    bbox = bw.getbbox()
    if bbox:
        bw = ImageOps.expand(bw.crop(bbox), border=6, fill=0)
    return bw


def prepare(mask: Image.Image, target_mm: float) -> tuple[np.ndarray, float]:
    """Return (raised bool HxW, mm_per_px) for mirrored stamp."""
    work = ImageOps.mirror(mask)
    w, h = work.size
    longest = max(w, h)
    content_mm = max(4.0, target_mm - 2 * EDGE_PAD_MM)
    px = min(MAX_GRID, max(48, int(round(content_mm / 0.28))))
    scale = px / longest
    nw, nh = max(8, int(round(w * scale))), max(8, int(round(h * scale)))
    resized = work.resize((nw, nh), Image.Resampling.NEAREST)
    pad_px = max(2, int(round(EDGE_PAD_MM / (content_mm / px))))
    padded = ImageOps.expand(resized, border=pad_px, fill=0)
    arr = np.array(padded, dtype=np.uint8) > 127
    mm_per_px = content_mm / px
    return arr, mm_per_px


def add_box(triangles: list[np.ndarray], x0, x1, y0, y1, z0, z1) -> None:
    """Append 12 triangles for an axis-aligned box."""
    v = np.array(
        [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
        ],
        dtype=np.float64,
    )
    faces = [
        (0, 2, 1), (0, 3, 2),  # bottom -z
        (4, 5, 6), (4, 6, 7),  # top +z
        (0, 1, 5), (0, 5, 4),  # -y
        (2, 3, 7), (2, 7, 6),  # +y
        (0, 4, 7), (0, 7, 3),  # -x
        (1, 2, 6), (1, 6, 5),  # +x
    ]
    for a, b, c in faces:
        triangles.append(np.array([v[a], v[b], v[c]]))


def build_stamp_mesh(raised: np.ndarray, mm_per_px: float) -> mesh.Mesh:
    h, w = raised.shape
    width = w * mm_per_px
    height = h * mm_per_px
    ox, oy = -width / 2, -height / 2

    tris: list[np.ndarray] = []
    # Base plate
    add_box(tris, ox, ox + width, oy, oy + height, 0.0, BASE_THICKNESS_MM)

    # Merge raised runs into larger boxes (row-wise RLE) for fewer triangles
    z0 = BASE_THICKNESS_MM
    z1 = BASE_THICKNESS_MM + RELIEF_HEIGHT_MM
    for i in range(h):
        j = 0
        y0 = oy + i * mm_per_px
        y1 = y0 + mm_per_px
        while j < w:
            if not raised[i, j]:
                j += 1
                continue
            j2 = j + 1
            while j2 < w and raised[i, j2]:
                j2 += 1
            x0 = ox + j * mm_per_px
            x1 = ox + j2 * mm_per_px
            add_box(tris, x0, x1, y0, y1, z0, z1)
            j = j2

    data = np.zeros(len(tris), dtype=mesh.Mesh.dtype)
    m = mesh.Mesh(data, remove_empty_areas=False)
    for idx, tri in enumerate(tris):
        m.vectors[idx] = tri
    return m


def inch_label(inches: float) -> str:
    if float(inches).is_integer():
        return f"{int(inches)}in"
    return f"{str(inches).replace('.', 'p')}in"


def main() -> None:
    # Clean previous bulky exports
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.stl"):
        old.unlink()

    jobs = [
        ("seal", LOGOS / "corbett-mark-seal.png"),
        ("headknife", LOGOS / "corbett-mark-headknife.png"),
    ]
    if not jobs[0][1].exists():
        jobs[0] = ("seal", LOGOS / "option-a-stamp-positive.png")
    if not jobs[1][1].exists():
        jobs[1] = ("headknife", LOGOS / "option-o-stamp-positive.png")

    for key, src in jobs:
        if not src.exists():
            raise SystemExit(f"Missing source: {src}")
        mask = load_mask(src)
        for inches in SIZES_IN:
            target_mm = inches * 25.4
            label = inch_label(inches)
            raised, mm_per_px = prepare(mask, target_mm)
            m = build_stamp_mesh(raised, mm_per_px)
            out = OUT / f"corbett-{key}-{label}-raised-mirror.stl"
            m.save(str(out))
            print(
                f"Wrote {out.name:48} "
                f"{raised.shape[1]*mm_per_px:5.1f}×{raised.shape[0]*mm_per_px:5.1f} mm  "
                f"tris={len(m.vectors)}  {out.stat().st_size/1024:.0f}KB"
            )

    readme = ROOT / "assets" / "stamps" / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Corbett & Co. — PLA leather stamp STLs",
                "",
                "Raised-relief stamps from **Seal A** and **Head Knife O**.",
                "All files are **mirrored** so the imprint on leather reads correctly.",
                "",
                "## Print these",
                "",
                "| File pattern | Mark |",
                "|--------------|------|",
                "| `corbett-seal-*-raised-mirror.stl` | Circular seal |",
                "| `corbett-headknife-*-raised-mirror.stl` | Head knife |",
                "",
                "## Sizes (longest axis)",
                "",
                "| Label | Size |",
                "|-------|------|",
                "| `0p75in` | 0.75\" (~19 mm) |",
                "| `1in` | 1.00\" (~25 mm) |",
                "| `1p25in` | 1.25\" (~32 mm) |",
                "| `1p5in` | 1.50\" (~38 mm) |",
                "| `2in` | 2.00\" (~51 mm) |",
                "",
                "## Suggested print settings",
                "",
                "- PLA · layer height 0.12–0.16 mm · 3+ walls · 20–40% infill",
                "- Print **flat, relief up** · no supports",
                f"- Base **{BASE_THICKNESS_MM} mm** · relief **{RELIEF_HEIGHT_MM} mm**",
                "",
                "Regenerate:",
                "",
                "```bash",
                "python3 scripts/make_stamp_stls.py",
                "```",
                "",
            ]
        )
    )
    print(f"\nDone → {OUT}")


if __name__ == "__main__":
    main()
