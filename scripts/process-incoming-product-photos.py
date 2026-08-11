#!/usr/bin/env python3
"""Crop, compress, and emit WebP/JPG for new Corbett product photos.

Expects files in assets/incoming/ named per NAMES.txt.
Writes web-ready assets to assets/ and prints recommended HTML placement.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "assets" / "incoming"
OUT = ROOT / "assets"

# name -> (max_long_edge, crop_focus as fraction of center, contrast, color)
SPECS = {
    "binder-open": {
        "out": "corbett-leather-binder-open",
        "max": 1600,
        "crop": 0.88,
        "contrast": 1.08,
        "color": 1.05,
        "role": "Lily Binder gallery — open 6-ring interior",
    },
    "lily-binder-held": {
        "out": "corbett-leather-lily-binder-held",
        "max": 1400,
        "crop": 0.82,
        "contrast": 1.1,
        "color": 1.06,
        "role": "Lily Binder gallery — tooling detail",
    },
    "lily-binder-flat": {
        "out": "corbett-leather-lily-binder-flat",
        "max": 1600,
        "crop": 0.78,
        "contrast": 1.1,
        "color": 1.08,
        "role": "Lily Binder feature hero + collection card",
    },
    # Legacy incoming names (pre-rename)
    "lily-clutch-held": {
        "out": "corbett-leather-lily-binder-held",
        "max": 1400,
        "crop": 0.82,
        "contrast": 1.1,
        "color": 1.06,
        "role": "Lily Binder gallery — tooling detail",
    },
    "lily-clutch-flat": {
        "out": "corbett-leather-lily-binder-flat",
        "max": 1600,
        "crop": 0.78,
        "contrast": 1.1,
        "color": 1.08,
        "role": "Lily Binder feature hero + collection card",
    },
    "envelope-wallet-closed": {
        "out": "corbett-leather-envelope-wallet-closed",
        "max": 1400,
        "crop": 0.72,
        "contrast": 1.12,
        "color": 1.04,
        "role": "Wallets feature — The Envelope (closed)",
    },
    "envelope-wallet-closed-alt": {
        "out": "corbett-leather-envelope-wallet-closed-alt",
        "max": 1200,
        "crop": 0.7,
        "contrast": 1.12,
        "color": 1.04,
        "role": "Wallets gallery tile (skip if weaker than primary closed)",
    },
    "envelope-wallet-open-card": {
        "out": "corbett-leather-envelope-wallet-open-card",
        "max": 1400,
        "crop": 0.75,
        "contrast": 1.1,
        "color": 1.05,
        "role": "Wallets gallery — brand moment (card in pocket)",
    },
    "envelope-wallet-open": {
        "out": "corbett-leather-envelope-wallet-open",
        "max": 1400,
        "crop": 0.75,
        "contrast": 1.08,
        "color": 1.04,
        "role": "Wallets gallery — construction / interior (secondary)",
    },
}


def find_source(stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"):
        p = INCOMING / f"{stem}{ext}"
        if p.exists():
            return p
    # loose match: any file starting with stem
    matches = sorted(INCOMING.glob(f"{stem}.*"))
    return matches[0] if matches else None


def center_crop(img: Image.Image, keep: float) -> Image.Image:
    keep = max(0.5, min(1.0, keep))
    w, h = img.size
    nw, nh = int(w * keep), int(h * keep)
    left = (w - nw) // 2
    top = (h - nh) // 2
    return img.crop((left, top, left + nw, top + nh))


def process_one(stem: str, spec: dict) -> list[Path]:
    src = find_source(stem)
    if not src:
        print(f"  SKIP {stem} (not found in {INCOMING})")
        return []

    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    img = center_crop(img, spec["crop"])
    img = ImageEnhance.Contrast(img).enhance(spec["contrast"])
    img = ImageEnhance.Color(img).enhance(spec["color"])

    # resize so longest edge <= max
    w, h = img.size
    m = spec["max"]
    if max(w, h) > m:
        if w >= h:
            nh = int(h * m / w)
            img = img.resize((m, nh), Image.Resampling.LANCZOS)
        else:
            nw = int(w * m / h)
            img = img.resize((nw, m), Image.Resampling.LANCZOS)

    out_stem = spec["out"]
    jpg_path = OUT / f"{out_stem}.jpg"
    webp_path = OUT / f"{out_stem}.webp"
    img.save(jpg_path, "JPEG", quality=82, optimize=True, progressive=True)
    img.save(webp_path, "WEBP", quality=80, method=6)

    print(f"  OK  {src.name} → {jpg_path.name} ({jpg_path.stat().st_size // 1024}KB) + webp")
    print(f"      role: {spec['role']}")
    return [jpg_path, webp_path]


def main() -> None:
    INCOMING.mkdir(parents=True, exist_ok=True)
    print(f"Incoming: {INCOMING}")
    written: list[Path] = []
    for stem, spec in SPECS.items():
        written.extend(process_one(stem, spec))

    if not written:
        print("\nNo images processed. Rename files per assets/incoming/NAMES.txt and re-run.")
        return

    print(f"\nWrote {len(written)} files. Next: wire Bags + The Envelope wallet on the site.")


if __name__ == "__main__":
    main()
