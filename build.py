#!/usr/bin/env python3
"""集めた補助金と要約から、静的なWebサイト（site/）を作る。標準ライブラリだけで動く。

作るページ:
  site/index.html        … 締切が近い順の一覧（目的で絞り込み可）
  site/s/<id>.html       … 補助金1件ごとの解説ページ
  site/p/<slug>.html     … 目的別ページ（例：設備・機器に使える補助金）
  site/sitemap.xml       … 環境変数 SITE_URL があるときだけ
"""
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
SITE_NAME = "わかりやすい補助金ナビ"
SITE_TAGLINE = "東京都の飲食店向け"
LINE_URL = "https://lin.ee/vPcjVOe"  # LINE公式アカウントの友だち追加URL
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
# Google Search Console の所有者確認用（HTMLタグの content の値）。GitHubの Variables で設定する
GSC_VERIFY = os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip()
JST = timezone(timedelta(hours=9))

PURPOSE_SLUGS = {
    "設備・機器": "setsubi",
    "省エネ・脱炭素": "shoene",
    "IT・キャッシュレス・DX": "it",
    "人材・採用・育成": "jinzai",
    "働き方・賃上げ": "hatarakikata",
    "開業・事業承継": "kaigyo",
    "販路・観光・インバウンド": "hanro",
    "その他": "other",
}
# AI要約が無いときに、jGrantsの「利用目的」から目的を推定する
FALLBACK_MAP = [
    ("設備整備", "設備・機器"), ("IT導入", "IT・キャッシュレス・DX"), ("エコ", "省エネ・脱炭素"),
    ("人材育成", "人材・採用・育成"), ("雇用・職場", "働き方・賃上げ"), ("引き継", "開業・事業承継"),
    ("新たな事業", "開業・事業承継"), ("販路", "販路・観光・インバウンド"),
]
FIT_RANK = {"高い": 0, "ふつう": 1, "不明": 2, "低い": 3}


def yen(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "募集要項で確認"
    if n <= 0:
        return "募集要項で確認"
    if n >= 100_000_000 and n % 10_000_000 == 0:
        return f"{n / 100_000_000:g}億円"
    if n >= 10_000 and n % 10_000 == 0:
        return f"{n // 10_000:,}万円"
    return f"{n:,}円"


def days_left(end, today):
    if not end:
        return None
    d = datetime.strptime(end[:10], "%Y-%m-%d").date()
    return (d - today).days


def deadline_badge(end, today):
    n = days_left(end, today)
    if n is None:
        return '<span class="badge">締切：要確認</span>'
    cls = "badge urgent" if n <= 14 else "badge"
    label = "本日締切" if n == 0 else f"あと{n}日"
    return f'<span class="{cls}">{label}</span>'


def fmt_date(s):
    if not s:
        return "募集要項で確認"
    d = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return f"{d.year}年{d.month}月{d.day}日 {d:%H:%M}"


def merge(rec):
    p = DATA / "summaries" / f"{rec['id']}.json"
    s = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    if s:
        rec["ai"] = True
        rec.update({k: s[k] for k in (
            "headline", "who", "amount", "uses", "restaurant_examples",
            "cautions", "restaurant_fit", "tokyo_eligible", "purposes")})
    else:
        rec["ai"] = False
        rec["headline"] = rec["catch"] or rec["title"]
        rec["who"] = "、".join(x for x in (rec["area"], rec["employees"]) if x)
        rec["amount"] = f"上限 {yen(rec['max_limit'])}" + (f"（補助率 {rec['rate']}）" if rec["rate"] else "")
        rec["uses"], rec["restaurant_examples"], rec["cautions"] = [], [], []
        rec["restaurant_fit"], rec["tokyo_eligible"] = "不明", "不明"
        rec["purposes"] = sorted({p for key, p in FALLBACK_MAP if key in rec["use_purpose"]}) or ["その他"]
    return rec


# ---------------- HTML部品 ----------------

def page(title, body, desc, depth=0, canonical=""):
    up = "../" * depth
    canon = f'<link rel="canonical" href="{escape(SITE_URL + canonical)}">' if SITE_URL else ""
    if GSC_VERIFY and depth == 0:
        canon += f'\n<meta name="google-site-verification" content="{escape(GSC_VERIFY)}">'
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
{canon}
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="site-header">
  <a class="logo" href="{up}index.html">{escape(SITE_NAME)}<span class="tagline">{escape(SITE_TAGLINE)}</span></a>
  <a class="cta" href="{LINE_URL}" target="_blank" rel="noopener">LINEで受け取る</a>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>情報の出典：<a href="https://www.jgrants-portal.go.jp/" rel="noopener">jGrants（デジタル庁）</a>。要約はAIで作成しています。
  申請できるかどうか・最新の条件は、必ず公式の募集要項で確認してください。当サイトは情報提供のみを行い、申請の代行は行いません。</p>
  <p>© {datetime.now(JST).year} {escape(SITE_NAME)}</p>
</footer>
</body>
</html>
"""


def card(r, today, up=""):
    chips = "".join(f'<span class="chip">{escape(p)}</span>' for p in r["purposes"])
    fit = f'<span class="fit fit-{FIT_RANK.get(r["restaurant_fit"], 2)}">飲食店との相性：{escape(r["restaurant_fit"])}</span>' \
        if r["restaurant_fit"] != "不明" else ""
    data_p = " ".join(PURPOSE_SLUGS.get(p, "other") for p in r["purposes"])
    return f"""<article class="card" data-p="{data_p}">
  <div class="card-top">{deadline_badge(r['end'], today)}{fit}</div>
  <h3><a href="{up}s/{escape(r['id'])}.html">{escape(r['title'])}</a></h3>
  <p class="headline">{escape(r['headline'])}</p>
  <dl class="facts">
    <div><dt>金額</dt><dd>{escape(r['amount'])}</dd></div>
    <div><dt>締切</dt><dd>{escape(fmt_date(r['end']))}</dd></div>
  </dl>
  <div class="chips">{chips}</div>
</article>"""


def line_box():
    return f"""<section class="line-box" id="line">
  <h2>新しい補助金の情報を、LINEでお届けします（無料）</h2>
  <p>締切が近い補助金や、飲食店に役立つ新着の補助金をお知らせします。友だち追加は無料で、いつでも解除できます。</p>
  <p><a class="line-button" href="{LINE_URL}" target="_blank" rel="noopener">LINEで友だち追加する</a></p>
</section>"""


def li(items):
    return "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in items) + "</ul>"


def detail_page(r, today):
    sections = []
    if r["uses"]:
        sections.append(f"<h2>何に使える？</h2>{li(r['uses'])}")
    if r["restaurant_examples"]:
        sections.append(f"<h2>飲食店ならこう使える</h2>{li(r['restaurant_examples'])}")
    if r["cautions"]:
        sections.append(f"<h2>申請前に確認したいこと</h2>{li(r['cautions'])}")
    attach = li(r["attachments"]) if r["attachments"] else "<p>公式ページで確認してください。</p>"
    chips = "".join(
        f'<a class="chip" href="../p/{PURPOSE_SLUGS.get(p, "other")}.html">{escape(p)}</a>' for p in r["purposes"])
    ai_note = '<p class="note">この要約はAIで作成しています。正確な内容は公式の募集要項で確認してください。</p>' \
        if r["ai"] else ""
    body = f"""<nav class="crumb"><a href="../index.html">一覧</a> › {escape(r['title'][:30])}</nav>
<article class="detail">
  <div class="card-top">{deadline_badge(r['end'], today)}</div>
  <h1>{escape(r['title'])}</h1>
  <p class="lead">{escape(r['headline'])}</p>
  <div class="chips">{chips}</div>
  <dl class="table">
    <div><dt>いくら</dt><dd>{escape(r['amount'])}</dd></div>
    <div><dt>誰が使える</dt><dd>{escape(r['who'] or '募集要項で確認')}</dd></div>
    <div><dt>受付開始</dt><dd>{escape(fmt_date(r['start']))}</dd></div>
    <div><dt>締切</dt><dd>{escape(fmt_date(r['end']))}</dd></div>
    <div><dt>対象地域</dt><dd>{escape(r['area'])}</dd></div>
    <div><dt>従業員数</dt><dd>{escape(r['employees'] or '募集要項で確認')}</dd></div>
  </dl>
  {''.join(sections)}
  {ai_note}
  <p><a class="button" href="{escape(r['url'])}" rel="noopener">公式ページ（jGrants）で詳しく見る</a></p>
  <section class="expert">
    <h2>申請を専門家に相談したい方へ</h2>
    <p>補助金の申請に詳しい行政書士・中小企業診断士をご紹介する窓口を準備中です。</p>
  </section>
  <h2>公式の資料</h2>
  {attach}
  <details><summary>公募情報の原文を読む</summary><div class="raw">{escape(r['detail_text']).replace(chr(10), '<br>')}</div></details>
</article>
{line_box()}"""
    desc = f"{r['headline']}｜{r['amount']}｜締切 {fmt_date(r['end'])}"
    return page(f"{r['title']}｜{SITE_NAME}", body, desc, depth=1, canonical=f"/s/{r['id']}.html")


# ---------------- 区ごとのページ ----------------

def load_wards():
    """data/wards（集めた本文）と data/ward_summaries（AI要約）を合わせて、区ごとの制度リストにする"""
    wards = []
    for p in sorted((DATA / "wards").glob("*.json")):
        w = json.loads(p.read_text(encoding="utf-8"))
        sp = DATA / "ward_summaries" / p.name
        sm = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {"items": {}, "pages": {}}
        programs = []
        for it in w["items"]:
            s = sm["items"].get(it["url"], {}).get("summary")
            if s:
                if s["is_business_subsidy"]:
                    programs.append(dict(s, url=it["url"], ai=True))
            else:
                programs.append({
                    "name": it["title"], "url": it["url"], "ai": False, "headline": "", "amount": "",
                    "status": "受付終了" if it["closed"] else "要確認", "deadline": "", "restaurant_fit": "不明",
                    "purposes": [],
                })
        for pg in w.get("pages", []):
            progs = sm["pages"].get(pg["url"], {}).get("programs")
            if progs:
                programs += [dict(s, url=pg["url"], ai=True) for s in progs if s["is_business_subsidy"]]
            else:  # AI要約がまだ無い一覧ページは、公式一覧へのリンクとして出す
                programs.append({
                    "name": f"{w['name']}の助成金一覧（公式ページ）", "url": pg["url"], "ai": False,
                    "headline": "1つのページに複数の制度が載っています。公式ページで確認してください。",
                    "amount": "", "status": "要確認", "deadline": "", "restaurant_fit": "不明", "purposes": [],
                })
        programs.sort(key=lambda x: FIT_RANK.get(x["restaurant_fit"], 2))
        w["programs"] = programs
        wards.append(w)
    return wards


def ward_card(x):
    st = x["status"]
    cls = "badge" if st in ("受付中", "通年・随時") else "badge muted"
    fit = f'<span class="fit fit-{FIT_RANK.get(x["restaurant_fit"], 2)}">飲食店との相性：{escape(x["restaurant_fit"])}</span>' \
        if x["restaurant_fit"] != "不明" else ""
    facts = ""
    if x["amount"]:
        facts += f"<div><dt>金額</dt><dd>{escape(x['amount'])}</dd></div>"
    if x["deadline"]:
        facts += f"<div><dt>締切</dt><dd>{escape(x['deadline'])}</dd></div>"
    chips = "".join(f'<span class="chip">{escape(p)}</span>' for p in x["purposes"])
    head = f'<p class="headline">{escape(x["headline"])}</p>' if x["headline"] else ""
    return f"""<article class="card">
  <div class="card-top"><span class="{cls}">{escape(st)}</span>{fit}</div>
  <h3><a href="{escape(x['url'])}" rel="noopener">{escape(x['name'])}</a></h3>
  {head}
  <dl class="facts">{facts}</dl>
  <div class="chips">{chips}</div>
</article>"""


def ward_page(w, main_items, today, updated):
    open_p = [x for x in w["programs"] if x["status"] != "受付終了"]
    closed_p = [x for x in w["programs"] if x["status"] == "受付終了"]
    closed = ""
    if closed_p:
        closed = f"""<details class="low"><summary>受付終了（次回の募集の参考に）{len(closed_p)}件</summary>
<div class="cards">{''.join(ward_card(x) for x in closed_p)}</div></details>"""
    own = "".join(ward_card(x) for x in open_p) or "<p>現在、確認できる区独自の制度はありません。</p>"
    srcs = "".join(f'<li><a href="{escape(u)}" rel="noopener">{escape(u)}</a></li>' for u in w["sources"])
    note = "区独自の制度の要約はAIで作成しています。" if any(x["ai"] for x in w["programs"]) else ""
    body = f"""<nav class="crumb"><a href="../index.html">一覧</a> › {escape(w['name'])}</nav>
<section class="hero"><h1>{escape(w['name'])}の飲食店が使える補助金・助成金</h1>
<p>{escape(w['name'])}独自の制度と、国・東京都の制度をまとめています（{escape(updated)}更新）。</p></section>
<h2 class="section-title">{escape(w['name'])}独自の制度</h2>
<div class="cards">{own}</div>
{closed}
<h2 class="section-title">国・東京都の制度（{escape(w['name'])}の事業者も使えます）</h2>
<div class="cards">{''.join(card(r, today, up="../") for r in main_items)}</div>
<section class="sources"><h2>{escape(w['name'])}の情報元</h2><ul>{srcs}</ul>
<p class="note">{note}最新の受付状況・条件は、必ず各公式ページで確認してください。</p></section>
{line_box()}"""
    return page(
        f"{w['name']}の飲食店が使える補助金・助成金（{today:%Y年%-m月}）｜{SITE_NAME}", body,
        f"{w['name']}の飲食店が使える補助金・助成金。区独自の制度と、国・東京都の募集中の制度をまとめています。",
        depth=1, canonical=f"/w/{w['slug']}.html")


def main():
    src = json.loads((DATA / "subsidies.json").read_text(encoding="utf-8"))
    today = datetime.now(JST).date()
    items = [merge(r) for r in src["items"]]
    items = [r for r in items if r["tokyo_eligible"] != "対象外"]
    main_items = [r for r in items if r["restaurant_fit"] != "低い"]
    low_items = [r for r in items if r["restaurant_fit"] == "低い"]

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "s").mkdir(parents=True)
    (SITE / "p").mkdir()
    (SITE / "w").mkdir()
    shutil.copy(ROOT / "style.css", SITE / "style.css")
    wards = load_wards()
    for w in wards:
        (SITE / "w" / f"{w['slug']}.html").write_text(
            ward_page(w, main_items, today, src["updated_at"]), encoding="utf-8")
    ward_nav = ""
    if wards:
        ward_nav = '<nav class="wards" aria-label="区で探す"><span>区で探す：</span>' + "".join(
            f'<a href="w/{escape(w["slug"])}.html">{escape(w["name"])}</a>' for w in wards) + "</nav>"

    # 一覧ページ
    filters = '<button class="filter on" data-f="all">すべて</button>' + "".join(
        f'<button class="filter" data-f="{s}">{escape(p)}</button>' for p, s in PURPOSE_SLUGS.items())
    low = ""
    if low_items:
        low = f"""<details class="low"><summary>飲食店との相性が低い補助金（{len(low_items)}件）</summary>
<div class="cards">{''.join(card(r, today) for r in low_items)}</div></details>"""
    body = f"""<section class="hero">
  <h1>東京都の飲食店が使える補助金・助成金</h1>
  <p>募集中の補助金を毎日更新。店主様向けに分かりやすくまとめています。
  <span class="updated">最終更新：{escape(src['updated_at'])}／掲載 {len(main_items)}件</span></p>
</section>
{ward_nav}
<div class="filters" role="group" aria-label="目的で絞り込む">{filters}</div>
<div class="cards" id="list">{''.join(card(r, today) for r in main_items)}</div>
{low}
{line_box()}
<script>
document.querySelectorAll('.filter').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('.filter').forEach(x => x.classList.toggle('on', x === b));
  const f = b.dataset.f;
  document.querySelectorAll('#list .card').forEach(c => {{
    c.hidden = f !== 'all' && !c.dataset.p.split(' ').includes(f);
  }});
}}));
</script>"""
    (SITE / "index.html").write_text(page(
        f"【東京都の飲食店向け】補助金・助成金一覧（{today:%Y年%-m月}更新）｜{SITE_NAME}", body,
        "東京都の飲食店が使える、募集中の補助金・助成金を締切が近い順にまとめています。毎日自動更新。",
        canonical="/index.html"), encoding="utf-8")

    # 補助金ごとのページ
    for r in items:
        (SITE / "s" / f"{r['id']}.html").write_text(detail_page(r, today), encoding="utf-8")

    # 目的別ページ
    for purpose, slug in PURPOSE_SLUGS.items():
        rs = [r for r in main_items if purpose in r["purposes"]]
        rs.sort(key=lambda r: (FIT_RANK.get(r["restaurant_fit"], 2), r.get("end") or "9999"))
        lst = "".join(card(r, today, up="../") for r in rs) or "<p>現在、募集中のものはありません。</p>"
        body = f"""<nav class="crumb"><a href="../index.html">一覧</a> › {escape(purpose)}</nav>
<section class="hero"><h1>{escape(purpose)}に使える補助金・助成金</h1>
<p>東京都の飲食店向け／募集中 {len(rs)}件（{escape(src['updated_at'])}更新）</p></section>
<div class="cards">{lst}</div>
{line_box()}"""
        (SITE / "p" / f"{slug}.html").write_text(page(
            f"【東京都の飲食店向け】{purpose}に使える補助金・助成金（{today:%Y年%-m月}）｜{SITE_NAME}", body,
            f"東京都の飲食店が{purpose}に使える、募集中の補助金・助成金の一覧です。", depth=1,
            canonical=f"/p/{slug}.html"), encoding="utf-8")

    if SITE_URL:
        urls = ["/index.html"] + [f"/p/{s}.html" for s in PURPOSE_SLUGS.values()] + \
               [f"/w/{w['slug']}.html" for w in wards] + \
               [f"/s/{r['id']}.html" for r in items]
        xml = "".join(f"<url><loc>{escape(SITE_URL + u)}</loc></url>" for u in urls)
        (SITE / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{xml}</urlset>',
            encoding="utf-8")

    n_ai = sum(r["ai"] for r in items)
    for w in wards:
        print(f"  {w['name']}: 区独自の制度 {len(w['programs'])}件（AI要約あり {sum(x['ai'] for x in w['programs'])}件）")
    print(f"サイトを作りました: 補助金ページ {len(items)}件（AI要約あり {n_ai}件）、目的別ページ {len(PURPOSE_SLUGS)}件 → site/")


if __name__ == "__main__":
    main()
