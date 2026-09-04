"""
Regenerates the colored ASCII-art block (with typing-reveal animation delays)
embedded in dark_mode.svg / light_mode.svg, from avatar.png.

Run this after replacing avatar.png, or to change the grid size / animation
duration, then re-run the splice step manually (see README comment below).
"""
import re
from xml.sax.saxutils import escape

from PIL import Image

COLS, ROWS = 55, 33
DURATION = 9.0  # seconds for the full "typing" reveal
ART_WIDTH, ART_HEIGHT = 300, 450
ART_X, ART_Y = 30, 30
RAMP = " .`,:;-~+=*/(%#&@"  # sparse/light -> dense/dark


def luminance(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


def is_background(r, g, b):
    """Matches the mint-green background so it can be blanked out."""
    return g > r + 20 and g > b + 20 and g > 150


def build_fragment(avatar_path):
    im = Image.open(avatar_path).convert("RGB")
    small = im.resize((COLS, ROWS), Image.Resampling.BOX)
    px = small.load()

    row_h = ART_HEIGHT / ROWS
    col_w = ART_WIDTH / COLS
    total = COLS * ROWS
    lines = []
    idx = 0
    for r in range(ROWS):
        y = ART_Y + (r + 1) * row_h - 2
        spans = []
        for c in range(COLS):
            rr, gg, bb = px[c, r]
            if is_background(rr, gg, bb):
                idx += 1
                continue
            x = ART_X + c * col_w
            l = luminance(rr, gg, bb)
            ramp_idx = max(0, min(len(RAMP) - 1, int((255 - l) / 255 * (len(RAMP) - 1))))
            ch = RAMP[ramp_idx]
            hexcol = "#{:02x}{:02x}{:02x}".format(rr, gg, bb)
            delay = idx / total * DURATION
            spans.append(
                f'<tspan x="{x:.1f}" class="cell" fill="{hexcol}" style="animation-delay:{delay:.3f}s">{escape(ch)}</tspan>'
            )
            idx += 1
        lines.append(
            f'<text x="{ART_X}" y="{y:.1f}" font-size="{row_h * 0.72:.2f}" '
            f'font-family="Consolas,\'Courier New\',monospace">' + "".join(spans) + "</text>"
        )
    return "\n".join(lines)


def replace_art(svg_path, fragment):
    with open(svg_path, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'<text x="30".*?</text>(\n<text x="30".*?</text>)*',
        fragment,
        content,
        flags=re.DOTALL,
    )
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    fragment = build_fragment("avatar.png")
    replace_art("dark_mode.svg", fragment)
    replace_art("light_mode.svg", fragment)
    print("Regenerated ASCII art in dark_mode.svg and light_mode.svg")
