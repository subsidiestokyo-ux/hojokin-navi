"""シンプルなメモ帳と鉛筆（白多め）のアイコンを、Canvaなどで文字・図形を編集できるベクターPDFにする（640×640）"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUT = Path(__file__).resolve().parent / "line_icon_memo_editable.pdf"
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
FONT = "HeiseiKakuGo-W5"

S = 640
PINK = (251 / 255, 227 / 255, 236 / 255)
BLUE = (53 / 255, 66 / 255, 212 / 255)
BLUE_SOFT = (229 / 255, 231 / 255, 255 / 255)
BLUE_MID = (169 / 255, 176 / 255, 255 / 255)
WHITE = (1, 1, 1)

c = canvas.Canvas(str(OUT), pagesize=(S, S))
c.setTitle("わかりやすい補助金ナビ LINEアイコン（メモ帳と鉛筆）")


def Y(y):
    return S - y


def fill(rgb):
    c.setFillColorRGB(*rgb)


def stroke(rgb, w):
    c.setStrokeColorRGB(*rgb)
    c.setLineWidth(w)


def text_center(y_top, txt, size):
    w = pdfmetrics.stringWidth(txt, FONT, size)
    c.setFont(FONT, size)
    fill(BLUE)
    c.drawString((S - w) / 2, Y(y_top) - size * 0.88, txt)


# 背景と方眼
fill(PINK)
c.rect(0, 0, S, S, stroke=0, fill=1)
stroke(WHITE, 1.5)
for i in range(0, S + 1, 24):
    c.line(i, 0, i, S)
    c.line(0, i, S, i)

text_center(85, "東京都・飲食店向け", 44)

# メモ帳（座標は上から測った値）：白い紙＋青い輪郭、リング3つ、書き込みの線3本
x0, y0, x1, y1 = 165, 185, 415, 415
fill(WHITE)
stroke(BLUE, 6)
c.roundRect(x0, Y(y1), x1 - x0, y1 - y0, 20, stroke=1, fill=1)
for i in range(3):
    cx = x0 + (x1 - x0) * (i + 1) / 4
    stroke(BLUE, 4.5)
    c.roundRect(cx - 6, Y(y0 + 20), 12, 38, 6, stroke=1, fill=1)
for i, w in enumerate((0.70, 0.52, 0.62)):
    y = y0 + 75 + i * 47.5
    fill(BLUE_MID)
    c.roundRect(x0 + 35, Y(y + 10), (x1 - x0 - 70) * w, 10, 5, stroke=0, fill=1)

# 鉛筆：白い軸に青い輪郭。ペン先が3本目の線の先（左下）
c.saveState()
c.translate(298, Y(337))
c.rotate(40)
L, T, tip = 260, 48, 65
fill(WHITE)
stroke(BLUE, 5.5)
p = c.beginPath()
p.moveTo(0, 0); p.lineTo(tip, T / 2); p.lineTo(L - 45, T / 2); p.lineTo(L - 45, -T / 2); p.lineTo(tip, -T / 2); p.close()
c.drawPath(p, stroke=1, fill=1)                       # 軸と削った部分
c.line(tip, T / 2, tip, -T / 2)
c.roundRect(L - 45, -T / 2, 45, T, 11, stroke=1, fill=1)  # 消しゴム
fill(BLUE)
p = c.beginPath()
p.moveTo(0, 0); p.lineTo(22, 8); p.lineTo(22, -8); p.close()
c.drawPath(p, stroke=0, fill=1)                       # 芯
c.restoreState()

text_center(455, "補助金ナビ", 76)
c.showPage()
c.save()
print(OUT.name)
