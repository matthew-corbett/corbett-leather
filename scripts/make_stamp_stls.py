#!/usr/bin/env python3
"""Build smooth PLA leather-stamp STLs via matthew-corbett/STLBuilder.

Uses STLBuilder's image→contour→CadQuery pipeline (not voxel extrusion).
Source marks are crisped / upscaled first so curves stay clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "stamps" / "stl"
PREP = ROOT / "assets" / "stamps" / "prep"
LOGOS = ROOT / "assets" / "logos"

STLBUILDER_CANDIDATES = [
    ROOT.parent / "STLBuilder",
    Path("/tmp/STLBuilder"),
    Path.home() / "STLBuilder",
]

SIZES_IN = (0.75, 1.0, 1.25, 1.5, 2.0)
PREP_PX = 1800


def _add_stlbuilder() -> Path:
    for candidate in STLBUILDER_CANDIDATES:
        if (candidate / "stlbuilder" / "image_stamp.py").is_file():
            sys.path.insert(0, str(candidate))
            return candidate
    raise SystemExit(
        "STLBuilder not found. Clone https://github.com/matthew-corbett/STLBuilder "
        "next to this repo (or into /tmp/STLBuilder)."
    )


def inch_label(inches: float) -> str:
    if float(inches).is_integer():
        return f"{int(inches)}in"
    return f"{str(inches).replace('.', 'p')}in"


def prepare_mark(src: Path, out: Path, size: int = PREP_PX) -> Path:
    """Write a crisp black-on-white PNG for STLBuilder contouring."""
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    g = ImageOps.autocontrast(Image.alpha_composite(bg, im).convert("L"))
    # Upscale with LANCZOS then hard-threshold → smoother contour input
    g = g.resize((size, int(size * im.height / im.width)), Image.Resampling.LANCZOS)
    bw = g.point(lambda x: 0 if x < 170 else 255).convert("L")
    bw = bw.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    out.parent.mkdir(parents=True, exist_ok=True)
    bw.save(out, optimize=True)
    return out


def main() -> None:
    stlbuilder_root = _add_stlbuilder()
    # Denser curve sampling if SVG path is used later
    import stlbuilder.svg_stamp as svg_stamp

    svg_stamp._CURVE_SAMPLES = 48

    import cv2
    import stlbuilder.image_stamp as image_stamp
    import cadquery as cq
    from stlbuilder.image_stamp import ImageStampSettings, build_image_stamp
    from stlbuilder.stamp_generator import StampGenerationError
    from shapely.geometry import Polygon

    def export_stl_smooth(model, path: Path) -> Path:
        """Export with tight tessellation so small letter curves stay round."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(
            model,
            str(path),
            tolerance=0.01,  # mm — default 0.1 is too coarse for stamp lettering
            angularTolerance=0.02,  # rad — default 0.1 facets circles
        )
        return path

    # Denser source contours than STLBuilder's default CHAIN_APPROX_SIMPLE
    def _dense_contours_to_polygons(mask, simplify: float):
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE
        )
        if hierarchy is None or len(contours) == 0:
            return []
        hierarchy = hierarchy[0]
        outers, holes_by_parent = {}, {}
        for idx, cnt in enumerate(contours):
            if len(cnt) < 3:
                continue
            parent = hierarchy[idx][3]
            approx = image_stamp._simplify_contour(cnt, simplify)
            if len(approx) < 3:
                continue
            ring = approx.reshape(-1, 2)
            if parent == -1:
                outers[idx] = ring
            else:
                holes_by_parent.setdefault(parent, []).append(ring)
        polygons = []
        img_h = mask.shape[0]
        for idx, outer in outers.items():
            holes = holes_by_parent.get(idx, [])
            outer_xy = [(float(x), float(img_h - y)) for x, y in outer]
            hole_xy = [[(float(x), float(img_h - y)) for x, y in hole] for hole in holes]
            try:
                poly = Polygon(outer_xy, hole_xy)
            except ValueError:
                continue
            if poly.is_empty or poly.area < 4:
                continue
            if not poly.is_valid:
                poly = poly.buffer(0)
                if poly.is_empty or poly.geom_type != "Polygon":
                    continue
            polygons.append(poly)
        return polygons

    image_stamp._contours_to_polygons = _dense_contours_to_polygons

    print(f"Using STLBuilder at {stlbuilder_root}")

    jobs = [
        ("seal", LOGOS / "corbett-mark-seal.png"),
        ("headknife", LOGOS / "corbett-mark-headknife.png"),
    ]
    for i, (key, path) in enumerate(jobs):
        if not path.exists():
            alt = LOGOS / f"option-{'a' if key == 'seal' else 'o'}-stamp-positive.png"
            if not alt.exists():
                raise SystemExit(f"Missing mark image: {path}")
            jobs[i] = (key, alt)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.stl"):
        old.unlink()

    for key, src in jobs:
        src = Path(src)
        prep = prepare_mark(src, PREP / f"corbett-{key}-crisp.png")
        print(f"\n=== {key}: prepared {prep.name} ===")

        for inches in SIZES_IN:
            width_mm = inches * 25.4
            label = inch_label(inches)
            out = OUT / f"corbett-{key}-{label}-raised-mirror.stl"
            settings = ImageStampSettings(
                image_path=str(prep),
                width_mm=width_mm,
                imprint_depth=2.0,
                base_thickness=3.0,
                margin=2.0,
                mirror_for_leather=True,
                threshold=128,
                invert=False,
                # Very low simplify % keeps letter/circle curves round
                simplify=0.05,
                max_pixels=1800,
                raised_border=False,
            )
            try:
                model = build_image_stamp(settings)
                export_stl_smooth(model, out)
            except StampGenerationError as exc:
                raise SystemExit(f"Failed {out.name}: {exc}") from exc
            print(
                f"Wrote {out.name:48} {width_mm:5.1f} mm  "
                f"{out.stat().st_size/1024:6.0f} KB"
            )

    (ROOT / "assets" / "stamps" / "README.md").write_text(
        "\n".join(
            [
                "# Corbett & Co. — PLA leather stamp STLs",
                "",
                "Generated with **[STLBuilder](https://github.com/matthew-corbett/STLBuilder)** "
                "(contour → CadQuery extrusion), after crisping the brand PNGs.",
                "Not voxel/pixel extrusion — curves are polygonal contours from OpenCV.",
                "",
                "All files are **mirrored** so leather imprints read correctly.",
                "",
                "## Files",
                "",
                "| Pattern | Mark |",
                "|---------|------|",
                "| `stl/corbett-seal-*-raised-mirror.stl` | Circular seal |",
                "| `stl/corbett-headknife-*-raised-mirror.stl` | Head knife |",
                "",
                "## Sizes (width)",
                "",
                "| Label | Size |",
                "|-------|------|",
                "| `0p75in` | 0.75\" (~19 mm) |",
                "| `1in` | 1.00\" (~25 mm) |",
                "| `1p25in` | 1.25\" (~32 mm) |",
                "| `1p5in` | 1.50\" (~38 mm) |",
                "| `2in` | 2.00\" (~51 mm) |",
                "",
                "## Print",
                "",
                "- PLA · 0.12–0.16 mm layers · relief up · no supports",
                "- Base 3 mm · imprint depth 2 mm · margin 2 mm",
                "",
                "## Regenerate",
                "",
                "```bash",
                "pip install -r /path/to/STLBuilder/requirements.txt",
                "python3 scripts/make_stamp_stls.py",
                "```",
                "",
            ]
        )
    )
    print(f"\nDone → {OUT}")


if __name__ == "__main__":
    main()
