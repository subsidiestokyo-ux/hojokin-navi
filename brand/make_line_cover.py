"""LINE公式アカウントのプロフィール背景画像（推奨比率 1000×635 に合わせた 2000×1270）。
サイト・アイコンと同じ、パステルピンクの方眼 × コバルトブルー。下の中央はアイコンが重なるので空けておく。"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 2000, 1270
PINK = (251, 227, 236)
GRID = (255, 255, 255)
BLUE = (53, 66, 212)
BLUE_MID = (169, 176, 255)
BLUE_SOFT = (229, 231, 255)
WHITE = (255, 255, 255)
MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"


def font(size):
    return ImageFont.truetype(MARU, size)


def ctext(d, cx, y, text, size, fill, stroke=0, shadow=None):
    f = font(size)
    x = cx - d.textlength(text, font=f) / 2
    for dx, col in (shadow or []):
        d.text((x + dx, y + dx), text, font=f, fill=col, stroke_width=stroke, stroke_fill=col)
    d.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)


def pill(d, cx, cy, text, size=58):
    f = font(size)
    w = d.textlength(text, font=f) + 90
    h = size + 50
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle((x0 + 10, y0 + 10, x0 + w + 10, y0 + h + 10), radius=h / 2, fill=BLUE)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h / 2, fill=WHITE, outline=BLUE, width=8)
    d.text((cx - (w - 90) / 2, y0 + 18), text, font=f, fill=BLUE, stroke_width=2, stroke_fill=BLUE)


def sparkle(d, cx, cy, r, color):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)


def dots(d, x0, y0, cols, rows, gap, r, color):
    for i in range(cols):
        for j in range(rows):
            x, y = x0 + i * gap, y0 + j * gap
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)


img = Image.new("RGB", (W, H), PINK)
d = ImageDraw.Draw(img)
for i in range(0, max(W, H), 50):
    d.line((i, 0, i, H), fill=GRID, width=3)
    d.line((0, i, W, i), fill=GRID, width=3)

# 飾り（四隅の水玉とキラキラ）
dots(d, 90, 90, 5, 4, 44, 9, BLUE_MID)
dots(d, W - 270, H - 260, 5, 4, 44, 9, BLUE_MID)
sparkle(d, 360, 330, 56, BLUE)
sparkle(d, 1690, 210, 44, BLUE_MID)
sparkle(d, 1760, 560, 64, BLUE)
sparkle(d, 220, 760, 40, BLUE_MID)

# 見出し
ctext(d, W / 2, 140, "東京都の飲食店のための", 84, BLUE, stroke=3)
ctext(d, W / 2, 280, "わかりやすい", 120, BLUE, stroke=5, shadow=[(12, BLUE_MID), (6, WHITE)])
ctext(d, W / 2, 430, "補助金ナビ", 190, BLUE, stroke=8, shadow=[(16, BLUE_MID), (8, WHITE)])

# 特長のバッジ
labels = ["毎日更新", "23区の制度も", "LINEで無料通知"]
widths = [d.textlength(t, font=font(58)) + 90 for t in labels]
gap = 70
x = W / 2 - (sum(widths) + gap * (len(labels) - 1)) / 2
for t, w in zip(labels, widths):  # 3つを等間隔に並べる
    pill(d, x + w / 2, 760, t)
    x += w + gap
# 下の中央（アイコンが重なる場所）は空けておく

img.save(OUT / "line_cover.png")
small = img.resize((1000, 635), Image.LANCZOS)
small.save(OUT / "line_cover_1000x635.png")
# アイコンが重なったときの見え方の確認用（実際の表示位置は目安）
prev = small.copy()
icon = Image.open(OUT / "line_icon_memo.png").resize((220, 220), Image.LANCZOS)
mask = Image.new("L", (220, 220), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 219, 219), fill=255)
ring = Image.new("RGB", (232, 232), WHITE)
rmask = Image.new("L", (232, 232), 0)
ImageDraw.Draw(rmask).ellipse((0, 0, 231, 231), fill=255)
prev.paste(ring, (500 - 116, 635 - 150), rmask)
prev.paste(icon, (500 - 110, 635 - 144), mask)
prev.save(OUT / "line_cover_preview.png")
print("ok")
