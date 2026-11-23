"""シティーポップ版（ピンク×ブルー）のお札アイコンを、Canvaなどで文字・図形を編集できるベクターPDFにする（640×640）"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUT = Path(__file__).resolve().parent / "line_icon_pop_editable.pdf"
# 日本語の標準フォント（文字は「文字」のまま入るので、Canva側で好きなフォントに変更できる）
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

S = 640
ORANGE = (53 / 255, 66 / 255, 212 / 255)  # コバルトブルー
CREAM = (251 / 255, 227 / 255, 236 / 255)  # パステルピンク
BILL = (229 / 255, 231 / 255, 255 / 255)
BILL_BACK = (1, 1, 1)

c = canvas.Canvas(str(OUT), pagesize=(S, S))
c.setTitle("わかりやすい補助金ナビ LINEアイコン")


def Y(y):  # 上からの座標に変換
    return S - y


c.setFillColorRGB(*CREAM)
c.rect(0, 0, S, S, stroke=0, fill=1)
c.setStrokeColorRGB(1, 1, 1)
c.setLineWidth(1.5)
for i in range(0, S + 1, 24):
    c.line(i, 0, i, S)
    c.line(0, i, S, i)


def text_center(y_top, txt, font, size):
    c.setFont(font, size)
    w = pdfmetrics.stringWidth(txt, font, size)
    c.setFillColorRGB(*ORANGE)
    c.drawString((S - w) / 2, Y(y_top) - size * 0.88, txt)


def bill(x0, y0, x1, y1, fill):
    h = y1 - y0
    c.setStrokeColorRGB(*ORANGE)
    c.setFillColorRGB(*fill)
    c.setLineWidth(11)
    c.roundRect(x0, Y(y1), x1 - x0, h, 18, stroke=1, fill=1)
    c.setLineWidth(4)
    c.roundRect(x0 + 24, Y(y1 - 22), x1 - x0 - 48, h - 44, 9, stroke=1, fill=0)
    c.setLineWidth(7)
    r = h * 0.13
    c.circle(x0 + 45 + r, Y(y0 + h / 2), r, stroke=1, fill=0)
    c.setFillColorRGB(255 / 255, 92 / 255, 147 / 255)
    c.circle(x1 - 75, Y(y0 + h * 0.30), 26, stroke=0, fill=1)
    c.setFillColorRGB(*ORANGE)
    for k in (0.58, 0.70):
        c.roundRect(x1 - 150, Y(y0 + h * k + 11), 100, 11, 5.5, stroke=0, fill=1)


text_center(110, "東京都・飲食店向け", "HeiseiKakuGo-W5", 46)
bill(150, 200, 520, 380, BILL_BACK)
bill(120, 230, 490, 410, BILL)
text_center(450, "補助金ナビ", "HeiseiKakuGo-W5", 75)
c.showPage()
c.save()
print(OUT.name)
