from pathlib import Path
from PIL import Image, ImageEnhance

repo = Path(__file__).resolve().parents[1]
emblem = Image.open(repo / "assets" / "corbett-leather-emblem.png").convert("RGBA")
w, h = emblem.size
crop = emblem.crop((int(w * 0.18), int(h * 0.28), int(w * 0.82), int(h * 0.78)))
cw, ch = crop.size
side = max(cw, ch)
sq = Image.new("RGBA", (side, side), (42, 24, 16, 255))
sq.paste(crop, ((side - cw) // 2, (side - ch) // 2), crop)
sq = ImageEnhance.Contrast(sq).enhance(1.15)
sq = ImageEnhance.Sharpness(sq).enhance(1.4)

for px, name in [(16, "favicon-16x16.png"), (32, "favicon-32x32.png"), (180, "apple-touch-icon.png")]:
    sq.resize((px, px), Image.LANCZOS).save(repo / name, optimize=True)

icos = [sq.resize((s, s), Image.LANCZOS) for s in (16, 32, 48)]
icos[0].save(
    repo / "favicon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48)],
    append_images=icos[1:],
)

(repo / "favicon.svg").write_text(
    """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="Corbett and Co. Leather Works">
  <rect width="32" height="32" rx="5" fill="#2a1810"/>
  <rect x="2.5" y="2.5" width="27" height="27" rx="3.5" fill="none" stroke="#c08a3e" stroke-width="1.2"/>
  <text x="16" y="21.5" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="13" font-weight="700" fill="#c08a3e">C&amp;Co</text>
</svg>""",
    encoding="utf-8",
)
print("favicons built")
