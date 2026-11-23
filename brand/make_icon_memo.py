"""LINEアイコン：メモ帳と鉛筆（サイトと同じピンク×コバルトブルー、赤系は使わない）640×640 PNG"""
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
    # ずらし影 → 紙 → 上の帯 → リング → 罫線 → チェック
    d.rounded_rectangle((x0 + 24, y0 + 24, x1 + 24, y1 + 24), radius=44, fill=BLUE)
    d.rounded_rectangle((x0, y0, x1, y1), radius=44, fill=WHITE, outline=BLUE, width=18)
    d.rounded_rectangle((x0, y0, x1, y0 + 120), radius=44, fill=BLUE)
    d.rectangle((x0, y0 + 70, x1, y0 + 120), fill=BLUE)
    n = 5
    for i in range(n):  # リング（綴じ穴）
        cx = x0 + 90 + i * (x1 - x0 - 180) / (n - 1)
        d.ellipse((cx - 22, y0 - 40, cx + 22, y0 + 4), fill=WHITE, outline=BLUE, width=10)
        d.rounded_rectangle((cx - 11, y0 - 20, cx + 11, y0 + 60), radius=11, fill=WHITE, outline=BLUE, width=8)
    top = y0 + 190
    for i in range(4):  # 罫線と、書き込みを表す線＋チェック
        y = top + i * 92
        d.line((x0 + 60, y + 40, x1 - 60, y + 40), fill=BLUE_SOFT, width=8)
        d.rounded_rectangle((x0 + 70, y - 12, x0 + 118, y + 36), radius=10, outline=BLUE, width=8)
        if i < 3:  # チェック済み
            d.line((x0 + 80, y + 10, x0 + 94, y + 26, x0 + 120, y - 14), fill=BLUE, width=12, joint="curve")
        w = [0.55, 0.40, 0.50, 0.30][i]
        d.rounded_rectangle((x0 + 150, y - 2, x0 + 150 + (x1 - x0 - 230) * w, y + 22), radius=12, fill=BLUE_MID)


def pencil(size_len=640, thick=120):
    """横向きの鉛筆を描いて返す（あとで回転させる）。赤やピンクは使わない"""
    L, T = size_len, thick
    im = Image.new("RGBA", (L + 60, T + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 30
    tip = 150
    # 影
    d.polygon([(o + 18, o + 18 + T / 2), (o + 18 + tip, o + 18), (o + 18 + L, o + 18), (o + 18 + L, o + 18 + T), (o + 18 + tip, o + 18 + T)], fill=BLUE)
    # 削った木の部分（白）と芯（青）
    d.polygon([(o, o + T / 2), (o + tip, o), (o + tip, o + T)], fill=WHITE, outline=BLUE, width=12)
    d.polygon([(o, o + T / 2), (o + 52, o + T / 2 - 19), (o + 52, o + T / 2 + 19)], fill=BLUE)
    # 軸（淡いブルー）＋ストライプ
    d.rectangle((o + tip, o, o + L - 130, o + T), fill=BLUE_SOFT, outline=BLUE, width=12)
    d.line((o + tip, o + T / 3, o + L - 130, o + T / 3), fill=BLUE_MID, width=10)
    d.line((o + tip, o + 2 * T / 3, o + L - 130, o + 2 * T / 3), fill=BLUE_MID, width=10)
    # 金具（白）と消しゴム（中間のブルー）
    d.rectangle((o + L - 130, o, o + L - 70, o + T), fill=WHITE, outline=BLUE, width=12)
    d.line((o + L - 110, o, o + L - 110, o + T), fill=BLUE, width=6)
    d.line((o + L - 90, o, o + L - 90, o + T), fill=BLUE, width=6)
    d.rounded_rectangle((o + L - 76, o, o + L, o + T), radius=24, fill=BLUE_MID, outline=BLUE, width=12)
    return im


img = Image.new("RGB", (S, S), PINK)
d = ImageDraw.Draw(img)
for i in range(0, S, 48):
    d.line((i, 0, i, S), fill=GRID, width=3)
    d.line((0, i, S, i), fill=GRID, width=3)

ctext(d, 170, "東京都・飲食店向け", 88, BLUE, stroke=3)
notepad(d, 290, 340, 840, 850)
p = pencil(560, 110).rotate(40, expand=True, resample=Image.BICUBIC)  # ペン先を左下（未チェックの行）に
img.paste(p, (520, 300), p)
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
