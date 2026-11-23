"""LINEアイコン：シンプルなメモ帳と鉛筆（白多め）（サイトと同じピンク×コバルトブルー、赤系は使わない）640×640 PNG"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 1280
PINK = (251, 227, 236)        # 背景（サイトの #fbe3ec）
GRID = (255, 255, 255)
BLUE = (53, 66, 212)          # #3542d4
BLUE_SOFT = (229, 231, 255)   # #e5e7ff
BLUE_MID = (169, 176, 255)    # #a9b0ff
WHITE = (255, 255, 255)
MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"


def ctext(d, y, text, size, fill, stroke=0, shadow=None):
    f = ImageFont.truetype(MARU, size)
    x = (S - d.textlength(text, font=f)) / 2
    for dx, col in (shadow or []):
        d.text((x + dx, y + dx), text, font=f, fill=col, stroke_width=stroke, stroke_fill=col)
    d.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)


def notepad(d, x0, y0, x1, y1):
    """シンプルなメモ帳：白い紙＋細めの青い線、リング3つ、罫線3本だけ"""
    d.rounded_rectangle((x0, y0, x1, y1), radius=40, fill=WHITE, outline=BLUE, width=12)
    for i in range(3):  # リング
        cx = x0 + (x1 - x0) * (i + 1) / 4
        d.rounded_rectangle((cx - 12, y0 - 36, cx + 12, y0 + 40), radius=12, fill=WHITE, outline=BLUE, width=9)
    for i, w in enumerate((0.70, 0.52, 0.62)):  # 書き込みの線
        y = y0 + 150 + i * 95
        d.rounded_rectangle((x0 + 70, y, x0 + 70 + (x1 - x0 - 140) * w, y + 20), radius=10, fill=BLUE_MID)


def pencil(size_len=520, thick=96):
    """シンプルな鉛筆：白い軸に青い輪郭、先端の芯と消しゴムの区切りだけ"""
    L, T = size_len, thick
    im = Image.new("RGBA", (L + 40, T + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o, tip = 20, 130
    d.polygon([(o, o + T / 2), (o + tip, o), (o + L, o), (o + L, o + T), (o + tip, o + T)], fill=WHITE)
    d.line([(o + tip, o), (o + L - 20, o)], fill=BLUE, width=11)
    d.line([(o + tip, o + T), (o + L - 20, o + T)], fill=BLUE, width=11)
    d.rounded_rectangle((o + L - 90, o, o + L, o + T), radius=22, fill=WHITE, outline=BLUE, width=11)
    d.line([(o + tip, o), (o, o + T / 2), (o + tip, o + T), (o + tip, o)], fill=BLUE, width=11, joint="curve")
    d.polygon([(o, o + T / 2), (o + 44, o + T / 2 - 16), (o + 44, o + T / 2 + 16)], fill=BLUE)
    return im


img = Image.new("RGB", (S, S), PINK)
d = ImageDraw.Draw(img)
for i in range(0, S, 48):
    d.line((i, 0, i, S), fill=GRID, width=3)
    d.line((0, i, S, i), fill=GRID, width=3)

ctext(d, 170, "東京都・飲食店向け", 88, BLUE, stroke=3)
notepad(d, 330, 370, 830, 830)
p = pencil().rotate(40, expand=True, resample=Image.BICUBIC)  # ペン先を左下（3本目の線の先）に
img.paste(p, (560, 330), p)
d = ImageDraw.Draw(img)
ctext(d, 925, "補助金ナビ", 158, BLUE, stroke=7, shadow=[(14, BLUE_MID), (7, WHITE)])

img = img.resize((640, 640), Image.LANCZOS)
img.save(OUT / "line_icon_memo.png")
mask = Image.new("L", (640, 640), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 639, 639), fill=255)
prev = Image.new("RGB", (840, 640), (235, 235, 235))
prev.paste(img, (0, 0), mask)
prev.paste(img.resize((120, 120), Image.LANCZOS), (680, 260), mask.resize((120, 120)))
prev.save(OUT / "line_icon_memo_preview.png")
print("ok")
