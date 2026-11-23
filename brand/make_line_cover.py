"""LINE公式アカウントのプロフィール背景画像（推奨比率 1000×635 に合わせた 2000×1270）。
サイト・アイコンと同じ、パステルピンクの方眼 × コバルトブルー。LINEのプロフィールでは上下が切れて横長（約2:1）で表示されるため、文字は中央の帯に収める。"""
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
dots(d, 90, 230, 5, 4, 44, 9, BLUE_MID)
dots(d, W - 270, 900, 5, 4, 44, 9, BLUE_MID)
sparkle(d, 330, 470, 56, BLUE)
sparkle(d, 1700, 300, 44, BLUE_MID)
sparkle(d, 1720, 640, 64, BLUE)
sparkle(d, 200, 860, 40, BLUE_MID)

# 見出し
ctext(d, W / 2, 270, "東京都の飲食店のための", 84, BLUE, stroke=3)
ctext(d, W / 2, 400, "わかりやすい", 120, BLUE, stroke=5, shadow=[(12, BLUE_MID), (6, WHITE)])
ctext(d, W / 2, 540, "補助金ナビ", 190, BLUE, stroke=8, shadow=[(16, BLUE_MID), (8, WHITE)])

# 特長のバッジ
labels = ["毎日更新", "23区の制度も", "LINEで無料通知"]
widths = [d.textlength(t, font=font(58)) + 90 for t in labels]
gap = 70
x = W / 2 - (sum(widths) + gap * (len(labels) - 1)) / 2
for t, w in zip(labels, widths):  # 3つを等間隔に並べる
    pill(d, x + w / 2, 890, t)
    x += w + gap

img.save(OUT / "line_cover.png")
small = img.resize((1000, 635), Image.LANCZOS)
small.save(OUT / "line_cover_1000x635.png")
# 確認用プレビュー：LINEで見える範囲（中央の約2:1の帯）以外を暗くする。※LINEにはこのプレビューではなく line_cover_1000x635.png を設定する
prev = small.convert("RGBA")
shade = Image.new("RGBA", prev.size, (0, 0, 0, 0))
sd = ImageDraw.Draw(shade)
vis_h = int(1000 / 2.03)
top = (635 - vis_h) // 2
sd.rectangle((0, 0, 1000, top), fill=(0, 0, 0, 110))
sd.rectangle((0, top + vis_h, 1000, 635), fill=(0, 0, 0, 110))
Image.alpha_composite(prev, shade).convert("RGB").save(OUT / "line_cover_check_visible_area.png")
print("ok")
