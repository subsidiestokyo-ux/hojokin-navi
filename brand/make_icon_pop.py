"""LINEアイコン：サイトと同じシティーポップ調（パステルピンク×コバルトブルー）のお札デザイン（640×640 PNG）"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 1280
PINK = (251, 227, 236)      # サイトの背景 #fbe3ec
GRID = (255, 255, 255)
BLUE = (53, 66, 212)        # #3542d4
BLUE_SHADOW = (169, 176, 255)  # #a9b0ff
WHITE = (255, 255, 255)
BILL = (229, 231, 255)      # 淡いブルー #e5e7ff
HOTPINK = (255, 92, 147)    # #ff5c93
MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"


def ctext(d, y, text, size, fill, stroke=0, shadow=None):
    """中央ぞろえの文字。stroke で丸ゴシックを太らせ、shadow でサイトの見出しと同じずらし影を付ける"""
    f = ImageFont.truetype(MARU, size)
    w = d.textlength(text, font=f)
    x = (S - w) / 2
    if shadow:
        for dx, col in shadow:
            d.text((x + dx, y + dx), text, font=f, fill=col, stroke_width=stroke, stroke_fill=col)
    d.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)


def bill(d, x0, y0, x1, y1, fill, shadow=True):
    h = y1 - y0
    if shadow:  # カードと同じ「ずらし影」
        d.rounded_rectangle((x0 + 22, y0 + 22, x1 + 22, y1 + 22), radius=40, fill=BLUE)
    d.rounded_rectangle((x0, y0, x1, y1), radius=40, fill=fill, outline=BLUE, width=18)
    d.rounded_rectangle((x0 + 46, y0 + 42, x1 - 46, y1 - 42), radius=20, outline=BLUE, width=7)
    d.ellipse((x0 + 90, y0 + h * 0.24, x0 + 90 + h * 0.52, y0 + h * 0.76), outline=BLUE, width=14)
    cx = x1 - 150
    d.ellipse((cx - 52, y0 + h * 0.30 - 52, cx + 52, y0 + h * 0.30 + 52), fill=HOTPINK)
    for k in (0.58, 0.70):
        d.rounded_rectangle((x1 - 300, y0 + h * k, x1 - 100, y0 + h * k + 22), radius=11, fill=BLUE)


img = Image.new("RGB", (S, S), PINK)
d = ImageDraw.Draw(img)
for i in range(0, S, 48):  # 方眼の背景
    d.line((i, 0, i, S), fill=GRID, width=3)
    d.line((0, i, S, i), fill=GRID, width=3)

ctext(d, 200, "東京都・飲食店向け", 88, BLUE, stroke=3)
bill(d, 300, 380, 1020, 730, WHITE, shadow=False)
bill(d, 250, 440, 970, 790, BILL)
ctext(d, 880, "補助金ナビ", 158, BLUE, stroke=7, shadow=[(14, BLUE_SHADOW), (7, WHITE)])

img = img.resize((640, 640), Image.LANCZOS)
img.save(OUT / "line_icon_pop.png")

mask = Image.new("L", (640, 640), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 639, 639), fill=255)
prev = Image.new("RGB", (640 + 200, 640), (235, 235, 235))
prev.paste(img, (0, 0), mask)
sm = img.resize((120, 120), Image.LANCZOS)
prev.paste(sm, (680, 260), mask.resize((120, 120)))
prev.save(OUT / "line_icon_pop_preview.png")
print("ok")
