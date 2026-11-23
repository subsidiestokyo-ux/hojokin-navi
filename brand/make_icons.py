"""LINE公式アカウント用のアイコン案（640×640 PNG）を作る。LINEでは丸く切り抜かれて表示される。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 1280  # 2倍で描いて縮小（なめらかにするため）
ORANGE = (194, 65, 12)
ORANGE_L = (234, 88, 12)
CREAM = (250, 248, 245)
WHITE = (255, 255, 255)
F = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
F6 = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"


def font(path, size):
    return ImageFont.truetype(path, size)


def center_text(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((S - w) / 2, y), text, font=f, fill=fill)


def save(img, name):
    img = img.resize((640, 640), Image.LANCZOS)
    img.save(OUT / f"{name}.png")
    # 丸く切り抜いたときの見え方の確認用
    mask = Image.new("L", (640, 640), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 639, 639), fill=255)
    prev = Image.new("RGB", (640, 640), (230, 230, 230))
    prev.paste(img, (0, 0), mask)
    return prev


def icon_a():
    """A：オレンジ地に白抜きの文字。小さく表示されても読みやすい"""
    img = Image.new("RGB", (S, S), ORANGE)
    d = ImageDraw.Draw(img)
    center_text(d, 330, "補助金", font(F, 340), WHITE)
    center_text(d, 730, "ナビ", font(F6, 190), (255, 228, 205))
    # 下に小さく「東京・飲食店」
    center_text(d, 975, "東京・飲食店", font(F6, 84), (255, 214, 186))
    return img


def bowl(d, cx, cy, r, color, coin_color, coin_text_color):
    # どんぶり（半円）と台
    d.pieslice((cx - r, cy - r, cx + r, cy + r), 0, 180, fill=color)
    d.rectangle((cx - r - 40, cy - 30, cx + r + 40, cy + 10), fill=color)
    d.rounded_rectangle((cx - r * 0.42, cy + r * 0.92, cx + r * 0.42, cy + r * 1.08), radius=20, fill=color)
    # 湯気の代わりに「¥」コイン
    cr = r * 0.42
    ccy = cy - r * 0.78
    d.ellipse((cx - cr, ccy - cr, cx + cr, ccy + cr), fill=coin_color)
    f = font(F, int(cr * 1.3))
    w = d.textlength("¥", font=f)
    d.text((cx - w / 2, ccy - cr * 0.78), "¥", font=f, fill=coin_text_color)


def icon_b():
    """B：どんぶり＋円マークのイラスト。飲食店向けだと一目で伝わる"""
    img = Image.new("RGB", (S, S), CREAM)
    d = ImageDraw.Draw(img)
    bowl(d, S // 2, 560, 300, ORANGE, (250, 204, 21), ORANGE)
    center_text(d, 930, "補助金ナビ", font(F, 150), ORANGE)
    return img


def icon_c():
    """C：吹き出しの中に「補助金」。LINEで届くお知らせらしさを出す"""
    img = Image.new("RGB", (S, S), WHITE)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((230, 360, S - 230, 860), radius=150, fill=ORANGE_L)
    d.polygon([(430, 840), (570, 840), (400, 990)], fill=ORANGE_L)
    center_text(d, 215, "わかりやすい", font(F6, 96), ORANGE)
    center_text(d, 470, "補助金", font(F, 250), WHITE)
    center_text(d, 900, "ナビ", font(F, 130), ORANGE)
    return img


previews = [save(icon_a(), "line_icon_A"), save(icon_b(), "line_icon_B"), save(icon_c(), "line_icon_C")]
# 3案を並べた比較画像（丸く切り抜いた状態＋小さく表示した状態）
sheet = Image.new("RGB", (640 * 3 + 80, 640 + 260), WHITE)
d = ImageDraw.Draw(sheet)
for i, p in enumerate(previews):
    x = 20 + i * 660
    sheet.paste(p, (x, 20))
    small = p.resize((120, 120), Image.LANCZOS)
    sheet.paste(small, (x + 260, 690))
    d.text((x + 10, 690), "ABC"[i], font=font(F, 90), fill=ORANGE)
sheet.save(OUT / "line_icon_compare.png")
print("ok")
