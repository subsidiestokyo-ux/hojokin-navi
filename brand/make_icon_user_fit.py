"""ユーザーがCanvaで作ったアイコン（手とコイン）を、LINEで丸く切り抜いても文字が切れない配置に組み直す"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 2000
BG = (254, 235, 237)
BLUE = (34, 58, 191)
MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"

src = Image.open(OUT / "user_icon_original.webp").convert("RGB")
# 元画像の青い丸（イラスト部分）をそのまま切り出す
circle = src.crop((488, 488, 1512, 1512))
cmask = Image.new("L", circle.size, 0)
ImageDraw.Draw(cmask).ellipse((0, 0, circle.size[0] - 1, circle.size[1] - 1), fill=255)

img = Image.new("RGB", (S, S), BG)
d = ImageDraw.Draw(img)
for i in range(88, S, 135):  # 元と同じ白い方眼
    d.line((i, 0, i, S), fill=(255, 255, 255), width=6)
    d.line((0, i, S, i), fill=(255, 255, 255), width=6)

D = 820  # イラストの丸を少し小さくして、上下の文字の場所をつくる
c2 = circle.resize((D, D), Image.LANCZOS)
m2 = cmask.resize((D, D), Image.LANCZOS)
img.paste(c2, ((S - D) // 2, 590), m2)


def fit_text(y_center, text, max_w, stroke):
    size = 300
    while True:
        f = ImageFont.truetype(MARU, size)
        l, t, r, b = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
        if r - l <= max_w:
            break
        size -= 4
    x = (S - (r - l)) / 2 - l
    y = y_center - (b - t) / 2 - t
    d.text((x, y), text, font=f, fill=BLUE, stroke_width=stroke, stroke_fill=BLUE)
    return (x + l, y + t, x + r, y + b)


# 丸の中に収まる幅に自動で合わせる（上下の文字は円の内側、余白つき）
box1 = fit_text(430, "東京都の飲食店向け", 1180, 5)
box2 = fit_text(1580, "補助金ナビ", 1100, 8)

img.save(OUT / "line_icon_user_fit.png")
img.resize((640, 640), Image.LANCZOS).save(OUT / "line_icon_user_fit_640.png")

# 文字の四隅が円の内側にあるか確認
import math
for name, (x0, y0, x1, y1) in (("上の文字", box1), ("下の文字", box2)):
    worst = max(math.hypot(x - S / 2, y - S / 2) for x in (x0, x1) for y in (y0, y1))
    print(f"{name}: 中心からいちばん遠い角まで {worst:.0f}px（円の半径 {S/2:.0f}px）→ {'OK' if worst < S/2 - 40 else '切れる'}")

small = img.resize((640, 640), Image.LANCZOS)
mask = Image.new("L", (640, 640), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 639, 639), fill=255)
prev = Image.new("RGB", (840, 640), (235, 235, 235))
prev.paste(small, (0, 0), mask)
prev.paste(small.resize((120, 120), Image.LANCZOS), (680, 260), mask.resize((120, 120)))
prev.save(OUT / "line_icon_user_fit_preview.png")
