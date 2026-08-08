#!/usr/bin/env python3
"""Build Corbett & Co. logos in a true leather head-knife / round-knife silhouette.

Classic Osborne-style top-down shape:
- ~250–270° circular cutting blade with two tips (point-to-point)
- Shallow back between the tips (not a full pizza-cutter disc)
- Short oval hardwood handle with ferrule attached at the back
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

OUT = "assets/logos"


def head_knife_mask(size: int = 1400, blade_span_deg: float = 205.0):
    """Return (mask, cx, cy, r) for a top-down leather head knife / round knife.

    Shape matches the classic tool: wide crescent cutting blade (point-to-point),
    shallow concave back, brass ferrule, oval hardwood handle.
    """
    im = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(im)

    # Blade sits left; handle extends right with real tool proportions.
    cx, cy = int(size * 0.36), size // 2
    r = int(size * 0.36)

    # Cutting arc centered on the left (west). Image angles: 0=east, clockwise.
    half = blade_span_deg / 2.0
    tip1 = 180.0 - half
    tip2 = 180.0 + half

    pts: list[tuple[float, float]] = []
    n = 160
    for i in range(n + 1):
        a = math.radians(tip1 + (tip2 - tip1) * (i / n))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    # Concave back between tips (toward handle) — classic head-knife throat.
    tip1_pt = pts[0]
    tip2_pt = pts[-1]
    back_ctrl = (cx - r * 0.05, cy)  # pull back left of center for crescent depth
    for i in range(1, 36):
        t = i / 36
        x = (1 - t) ** 2 * tip2_pt[0] + 2 * (1 - t) * t * back_ctrl[0] + t**2 * tip1_pt[0]
        y = (1 - t) ** 2 * tip2_pt[1] + 2 * (1 - t) * t * back_ctrl[1] + t**2 * tip1_pt[1]
        pts.append((x, y))

    d.polygon(pts, fill=255)

    # Tang stub from blade back into ferrule
    tang_x0 = int(cx + r * 0.02)
    tang_x1 = int(cx + r * 0.22)
    tang_h = int(size * 0.07)
    d.polygon(
        [
            (tang_x0, cy - tang_h * 0.55),
            (tang_x1, cy - tang_h * 0.70),
            (tang_x1, cy + tang_h * 0.70),
            (tang_x0, cy + tang_h * 0.55),
        ],
        fill=255,
    )

    # Brass ferrule (cylindrical band)
    ferrule_x0 = tang_x1 - 2
    ferrule_w = int(size * 0.055)
    ferrule_h = int(size * 0.125)
    fy0 = cy - ferrule_h // 2
    d.rounded_rectangle(
        [ferrule_x0, fy0, ferrule_x0 + ferrule_w, fy0 + ferrule_h],
        radius=4,
        fill=255,
    )

    # Oval hardwood handle — longer, clearly a knife grip
    handle_w = int(size * 0.28)
    handle_h = int(size * 0.135)
    hx0 = ferrule_x0 + ferrule_w - 4
    hy0 = cy - handle_h // 2
    d.ellipse([hx0, hy0, hx0 + handle_w, hy0 + handle_h], fill=255)

    return im, cx, cy, r


def erode(mask: Image.Image, steps: int) -> Image.Image:
    out = mask
    for _ in range(steps):
        out = out.filter(ImageFilter.MinFilter(3))
    return out


def dilate(mask: Image.Image, steps: int) -> Image.Image:
    out = mask
    for _ in range(steps):
        out = out.filter(ImageFilter.MaxFilter(3))
    return out


def outline_logo(mask: Image.Image, stroke: int = 15, gap: int = 11) -> tuple[Image.Image, Image.Image]:
    """Double-outline knife on white; returns (logo_rgb, interior_mask)."""
    size = mask.size[0]
    outer = dilate(mask, stroke // 2 + 1)
    interior = erode(mask, stroke)
    inner_line_outer = interior
    inner_line_inner = erode(interior, gap)

    rgb = Image.new("RGB", (size, size), (255, 255, 255))
    black = Image.new("RGB", (size, size), (0, 0, 0))
    rgb.paste(black, mask=outer)
    rgb.paste(Image.new("RGB", (size, size), (255, 255, 255)), mask=interior)

    # Inner accent ring
    band = Image.new("L", (size, size), 0)
    a = inner_line_outer.load()
    b = inner_line_inner.load()
    p = band.load()
    for y in range(size):
        for x in range(size):
            if a[x, y] > 128 and b[x, y] < 128:
                p[x, y] = 255
    rgb.paste(black, mask=band)
    rgb.paste(Image.new("RGB", (size, size), (255, 255, 255)), mask=inner_line_inner)
    return rgb, inner_line_inner


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_arc_text(
    base: Image.Image,
    text: str,
    cx: float,
    cy: float,
    radius: float,
    fnt: ImageFont.ImageFont,
    start_ang: float,
    end_ang: float,
    fill=(0, 0, 0),
    feet_in: bool = True,
) -> None:
    """Place characters along an arc (degrees, 0=east, clockwise, y-down)."""
    n = len(text)
    if n == 0:
        return
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        ang = start_ang + (end_ang - start_ang) * (i / max(n - 1, 1))
        bbox = fnt.getbbox(ch)
        gw = bbox[2] - bbox[0] + 8
        gh = bbox[3] - bbox[1] + 8
        glyph = Image.new("RGBA", (gw + 24, gh + 24), (255, 255, 255, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((12 - bbox[0], 12 - bbox[1]), ch, font=fnt, fill=fill + (255,))
        # feet_in: baseline toward center (classic seal). Else upright-ish along bottom.
        rot = (-ang - 90) if feet_in else (-ang + 90)
        rotated = glyph.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
        rad = math.radians(ang)
        x = cx + radius * math.cos(rad) - rotated.width / 2
        y = cy + radius * math.sin(rad) - rotated.height / 2
        base.paste(rotated, (int(x), int(y)), rotated)


def clip_to_interior(outline: Image.Image, content: Image.Image, interior: Image.Image) -> Image.Image:
    out = outline.copy()
    out.paste(content, mask=interior)
    return out


def make_seal() -> Image.Image:
    size = 1600
    mask, cx, cy, r = head_knife_mask(size)
    outline, interior = outline_logo(mask)
    content = outline.copy()
    d = ImageDraw.Draw(content)

    # Anchor type in the thickest part of the crescent (left of geometric center).
    tx, ty = cx - r * 0.22, cy

    f_mono = font(int(r * 0.34))
    f_top = font(int(r * 0.11))
    f_bot = font(int(r * 0.095))

    mono = "C&C"
    bbox = d.textbbox((0, 0), mono, font=f_mono)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((tx - tw / 2, ty - th / 2 - 4), mono, font=f_mono, fill=(0, 0, 0))

    mr = int(r * 0.30)
    d.ellipse([tx - mr, ty - mr, tx + mr, ty + mr], outline=(0, 0, 0), width=4)

    draw_arc_text(content, "CORBETT & CO.", tx, ty, r * 0.55, f_top, 235, 305, feet_in=True)
    draw_arc_text(content, "LEATHER WORKS", tx, ty, r * 0.52, f_bot, 120, 60, feet_in=False)

    for ang in (155.0, 205.0):
        rad = math.radians(ang)
        x = tx + r * 0.55 * math.cos(rad)
        y = ty + r * 0.55 * math.sin(rad)
        s = 7
        d.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], fill=(0, 0, 0))

    return clip_to_interior(outline, content, interior)


def make_monogram() -> Image.Image:
    size = 1600
    mask, cx, cy, r = head_knife_mask(size)
    outline, interior = outline_logo(mask, stroke=17, gap=12)
    content = outline.copy()
    d = ImageDraw.Draw(content)
    tx, ty = cx - r * 0.22, cy
    f_mono = font(int(r * 0.44))
    mono = "C&C"
    bbox = d.textbbox((0, 0), mono, font=f_mono)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((tx - tw / 2, ty - th / 2), mono, font=f_mono, fill=(0, 0, 0))
    return clip_to_interior(outline, content, interior)


def make_knockout() -> Image.Image:
    size = 1600
    mask, cx, cy, r = head_knife_mask(size)
    rgb = Image.new("RGB", (size, size), (255, 255, 255))
    rgb.paste(Image.new("RGB", (size, size), (0, 0, 0)), mask=mask)

    tx, ty = cx - r * 0.22, cy
    f_mono = font(int(r * 0.36))
    f_top = font(int(r * 0.09))
    overlay = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(overlay)
    mono = "C&C"
    bbox = d.textbbox((0, 0), mono, font=f_mono)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((tx - tw / 2, ty - th / 2), mono, font=f_mono, fill=255)

    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_arc_text(tmp, "CORBETT", tx, ty, r * 0.52, f_top, 235, 305, fill=(255, 255, 255))
    alpha = tmp.split()[-1]
    overlay = Image.composite(Image.new("L", (size, size), 255), overlay, alpha)

    rgb.paste(Image.new("RGB", (size, size), (255, 255, 255)), mask=overlay)
    return rgb


def stamp_pack(key: str, src: Image.Image, label: str, meta: dict) -> None:
    # Trim and square
    g = src.convert("L")
    inv = ImageOps.invert(g)
    bbox = inv.getbbox()
    if bbox:
        g = ImageOps.expand(g.crop(bbox), border=56, fill=255)
    size = 1400
    w, h = g.size
    scale = size / max(w, h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    g = g.resize((nw, nh), Image.Resampling.LANCZOS)
    # Hard threshold for stamp clarity
    g = g.point(lambda x: 0 if x < 200 else 255)
    canvas = Image.new("L", (size, size), 255)
    canvas.paste(g, ((size - nw) // 2, (size - nh) // 2))
    pos = canvas.convert("RGB")
    pos.save(f"{OUT}/option-{key}-stamp-positive.png", optimize=True)
    ImageOps.invert(canvas).convert("RGB").save(f"{OUT}/option-{key}-stamp-negative.png", optimize=True)
    ImageOps.mirror(pos).save(f"{OUT}/option-{key}-stamp-mirror.png", optimize=True)

    def colorize(mark_rgb, ink, paper):
        gl = mark_rgb.convert("L")
        out = Image.new("RGB", gl.size)
        px, op = gl.load(), out.load()
        for y in range(gl.size[1]):
            for x in range(gl.size[0]):
                t = px[x, y] / 255.0
                op[x, y] = tuple(int(ink[i] * (1 - t) + paper[i] * t) for i in range(3))
        return out

    colorize(pos, (192, 138, 62), (26, 15, 8)).save(f"{OUT}/option-{key}-sticker-brass.png", optimize=True)
    colorize(pos, (42, 24, 16), (250, 245, 236)).save(f"{OUT}/option-{key}-sticker-cream.png", optimize=True)
    thumb = pos.copy()
    thumb.thumbnail((520, 520))
    thumb.save(f"{OUT}/option-{key}-preview.png", optimize=True)
    meta[key] = label


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    # Reference silhouette so the shape is unmistakable
    size = 1000
    mask, *_ = head_knife_mask(size)
    ref = Image.new("RGB", (size, size), (255, 255, 255))
    ref.paste(Image.new("RGB", (size, size), (0, 0, 0)), mask=mask)
    ref.save(f"{OUT}/headknife-silhouette-ref.png")
    ref.save("/tmp/headknife-silhouette-ref.png")

    L = make_seal()
    M = make_monogram()
    N = make_knockout()
    L.save(f"{OUT}/logo-option-l-headknife-seal.png")
    M.save(f"{OUT}/logo-option-m-headknife-monogram.png")
    N.save(f"{OUT}/logo-option-n-headknife-knockout.png")

    meta: dict[str, str] = {}
    stamp_pack("l", L, "Head Knife Seal — true round-knife blade + Option A layout", meta)
    stamp_pack("m", M, "Head Knife Monogram — C&C in true round-knife silhouette", meta)
    stamp_pack("n", N, "Head Knife Knockout — filled blade, white C & C", meta)

    for key in "lmn":
        Image.open(f"{OUT}/option-{key}-preview.png").save(f"/tmp/option-{key}-preview.png")

    print("Wrote L/M/N head-knife logos")
    for k, v in meta.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
