#!/usr/bin/env python3
"""Generate ShareMint PWA icons (192 / 512). Requires Pillow (qrcode[pil])."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'static' / 'images'
BG = (2, 8, 23)
ACCENT = (0, 180, 255)
ACCENT2 = (0, 102, 255)


def draw_logo(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    s = (x1 - x0) * 0.22
    diamond = [
        (cx, cy - s * 1.35),
        (cx + s * 1.15, cy),
        (cx, cy + s * 1.35),
        (cx - s * 1.15, cy),
    ]
    draw.polygon(diamond, outline=ACCENT, width=max(2, int(s * 0.12)))
    draw.line([(cx, cy - s * 0.55), (cx, cy + s * 0.55)], fill=ACCENT, width=max(2, int(s * 0.1)))
    draw.line([(cx - s * 0.45, cy - s * 0.2), (cx, cy - s * 0.45), (cx + s * 0.45, cy - s * 0.2)], fill=ACCENT2, width=max(2, int(s * 0.08)))
    draw.line([(cx - s * 0.45, cy + s * 0.2), (cx, cy + s * 0.45), (cx + s * 0.45, cy + s * 0.2)], fill=ACCENT2, width=max(2, int(s * 0.08)))


def make_icon(size: int) -> Image.Image:
    img = Image.new('RGB', (size, size), BG)
    draw = ImageDraw.Draw(img)
    pad = int(size * 0.18)
    draw_logo(draw, (pad, pad, size - pad, size - pad))
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(192).save(OUT_DIR / 'logo192.png', 'PNG')
    make_icon(512).save(OUT_DIR / 'logo512.png', 'PNG')
    print(f'Wrote {OUT_DIR / "logo192.png"}')
    print(f'Wrote {OUT_DIR / "logo512.png"}')


if __name__ == '__main__':
    main()
