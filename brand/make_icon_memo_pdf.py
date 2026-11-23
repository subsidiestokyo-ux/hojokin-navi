"""メモ帳と鉛筆のアイコンを、Canvaなどで文字・図形を編集できるベクターPDFにする（640×640）"""
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

# メモ帳（座標は上から測った値）
x0, y0, x1, y1 = 145, 170, 420, 425
fill(BLUE)
c.roundRect(x0 + 12, Y(y1 + 12), x1 - x0, y1 - y0, 22, stroke=0, fill=1)   # ずらし影
fill(WHITE)
stroke(BLUE, 9)
c.roundRect(x0, Y(y1), x1 - x0, y1 - y0, 22, stroke=1, fill=1)            # 紙
fill(BLUE)
c.roundRect(x0, Y(y0 + 60), x1 - x0, 60, 22, stroke=0, fill=1)             # 上の帯
c.rect(x0, Y(y0 + 60), x1 - x0, 25, stroke=0, fill=1)
for i in range(5):                                                         # リング
    cx = x0 + 45 + i * (x1 - x0 - 90) / 4
    fill(WHITE)
    stroke(BLUE, 4)
    c.roundRect(cx - 5.5, Y(y0 + 30), 11, 40, 5.5, stroke=1, fill=1)
for i in range(4):                                                         # 罫線・チェック・書き込み
    y = y0 + 95 + i * 46
    stroke(BLUE_SOFT, 4)
    c.line(x0 + 30, Y(y + 20), x1 - 30, Y(y + 20))
    stroke(BLUE, 4)
    c.roundRect(x0 + 35, Y(y + 18), 24, 24, 5, stroke=1, fill=0)
    if i < 3:
        c.setLineWidth(6)
        p = c.beginPath()
        p.moveTo(x0 + 40, Y(y + 5))
        p.lineTo(x0 + 47, Y(y + 13))
        p.lineTo(x0 + 60, Y(y - 7))
        c.drawPath(p, stroke=1, fill=0)
    fill(BLUE_MID)
    c.roundRect(x0 + 75, Y(y + 11), (x1 - x0 - 115) * [0.55, 0.40, 0.50, 0.30][i], 12, 6, stroke=0, fill=1)

# 鉛筆（横向きに描いて回転。ペン先が左下）
c.saveState()
c.translate(300, Y(345))      # ペン先の位置
c.rotate(40)
L, T, tip = 280, 55, 75
fill(BLUE)
c.rect(tip + 9, -T / 2 - 9, L - tip, T, stroke=0, fill=1)                  # 影
fill(WHITE)
stroke(BLUE, 6)
p = c.beginPath()
p.moveTo(0, 0); p.lineTo(tip, T / 2); p.lineTo(tip, -T / 2); p.close()
c.drawPath(p, stroke=1, fill=1)                                            # 削った部分
fill(BLUE)
p = c.beginPath()
p.moveTo(0, 0); p.lineTo(26, 9.5); p.lineTo(26, -9.5); p.close()
c.drawPath(p, stroke=0, fill=1)                                            # 芯
fill(BLUE_SOFT)
c.rect(tip, -T / 2, L - tip - 65, T, stroke=1, fill=1)                     # 軸
stroke(BLUE_MID, 5)
c.line(tip, T / 6, L - 65, T / 6)
c.line(tip, -T / 6, L - 65, -T / 6)
fill(WHITE)
stroke(BLUE, 6)
c.rect(L - 65, -T / 2, 30, T, stroke=1, fill=1)                            # 金具
fill(BLUE_MID)
c.roundRect(L - 38, -T / 2, 38, T, 12, stroke=1, fill=1)                   # 消しゴム
c.restoreState()

text_center(455, "補助金ナビ", 76)
c.showPage()
c.save()
print(OUT.name)
