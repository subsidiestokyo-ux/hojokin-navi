"""B案の修正版：お札のイラスト＋「東京都・飲食店向け」＋「補助金ナビ」（640×640 PNG）"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 1280
ORANGE = (194, 65, 12)
CREAM = (250, 248, 245)
BILL = (254, 240, 196)      # お札の地色（淡い金色）
BILL_BACK = (246, 214, 150)  # 後ろのお札
F8 = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
F6 = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"


def center_text(d, y, text, size, path, fill):
    f = ImageFont.truetype(path, size)
    w = d.textlength(text, font=f)
    d.text(((S - w) / 2, y), text, font=f, fill=fill)


def bill(d, x0, y0, x1, y1, fill, line):
    d.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=fill, outline=line, width=22)
    # 内側の飾り枠
    d.rounded_rectangle((x0 + 48, y0 + 44, x1 - 48, y1 - 44), radius=18, outline=line, width=8)
    h = y1 - y0
    # 左に楕円の透かし模様、右に飾りの丸と横線
    d.ellipse((x0 + 90, y0 + h * 0.24, x0 + 90 + h * 0.52, y0 + h * 0.76), outline=line, width=14)
    cx = x1 - 150
    d.ellipse((cx - 52, y0 + h * 0.30 - 52, cx + 52, y0 + h * 0.30 + 52), fill=line)
    for i, k in enumerate((0.58, 0.70)):
        d.rounded_rectangle((x1 - 300, y0 + h * k, x1 - 100, y0 + h * k + 22), radius=11, fill=line)


img = Image.new("RGB", (S, S), CREAM)
d = ImageDraw.Draw(img)
center_text(d, 220, "東京都・飲食店向け", 92, F6, ORANGE)
# 2枚重ねのお札
bill(d, 300, 400, 1040, 760, BILL_BACK, ORANGE)
bill(d, 240, 460, 980, 820, BILL, ORANGE)
center_text(d, 900, "補助金ナビ", 150, F8, ORANGE)
img = img.resize((640, 640), Image.LANCZOS)
img.save(OUT / "line_icon_B2.png")

mask = Image.new("L", (640, 640), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 639, 639), fill=255)
prev = Image.new("RGB", (640 + 200, 640), (230, 230, 230))
prev.paste(img, (0, 0), mask)
small = Image.new("RGB", (120, 120), (230, 230, 230))
sm = img.resize((120, 120), Image.LANCZOS)
small.paste(sm, (0, 0), mask.resize((120, 120)))
prev.paste(small, (680, 260))
prev.save(OUT / "line_icon_B2_preview.png")
print("ok")
