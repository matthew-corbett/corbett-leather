# Corbett & Co. — PLA leather stamp STLs

Generated with **[STLBuilder](https://github.com/matthew-corbett/STLBuilder)** (contour → CadQuery extrusion), after crisping the brand PNGs.
Not voxel/pixel extrusion — curves are polygonal contours from OpenCV.

All files are **mirrored** so leather imprints read correctly.

## Files

| Pattern | Mark |
|---------|------|
| `stl/corbett-seal-*-raised-mirror.stl` | Circular seal |
| `stl/corbett-headknife-*-raised-mirror.stl` | Head knife |

## Sizes (width)

| Label | Size |
|-------|------|
| `0p75in` | 0.75" (~19 mm) |
| `1in` | 1.00" (~25 mm) |
| `1p25in` | 1.25" (~32 mm) |
| `1p5in` | 1.50" (~38 mm) |
| `2in` | 2.00" (~51 mm) |

## Print

- PLA · 0.12–0.16 mm layers · relief up · no supports
- Base 3 mm · imprint depth 2 mm · margin 2 mm

## Regenerate

```bash
pip install -r /path/to/STLBuilder/requirements.txt
python3 scripts/make_stamp_stls.py
```
