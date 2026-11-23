#!/usr/bin/env python3
"""区の公式サイトから、区独自の補助金・助成金を集める（標準ライブラリのみ）。

1. wards.json に登録した「補助金の一覧ページ」を1日1回だけ読む
2. 一覧ページから「補助・助成・奨励」を含むリンクを拾い、各制度のページを読む
3. 結果を data/wards/<slug>.json に保存する（本文が変わったかどうかを src_hash で判定）

各サイトの robots.txt を確認し、禁止されているページは読まない。
"""
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "wards"
UA = "Mozilla/5.0 (compatible; hojokin-collector/0.1)"
JST = timezone(timedelta(hours=9))
SLEEP = 1.5           # 同じサイトへの連続アクセスの間隔（秒）
MAX_ITEMS = 30        # 1区あたりに読む制度ページの上限

PICK = re.compile(r"補助|助成|奨励|支援金|利子補給")
# 制度そのものではないリンク（総合案内・相談・外部の判定サイトなど）
SKIP = re.compile(r"^(補助金|助成金|補助金・助成金|助成金・補助金|助成事業|補助事業)$|相談|自動判定|国や都|関係団体|申請する前に|一覧|ガイド|よくある")
CLOSED = re.compile(r"受付終了|募集終了|申込受付終了|受付は終了|終了しました|【終了】")

_robots = {}


def allowed(url):
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(UA, url)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "")
        raw = r.read()
    if "html" not in ctype:
        return None
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:2000])
    enc = (m.group(1).decode() if m else "utf-8").lower()
    return raw.decode("shift_jis" if enc in ("shift_jis", "sjis", "x-sjis") else enc, "ignore")


def main_html(s):
    """ヘッダー・メニュー・フッターを除いた本文部分をできるだけ取り出す"""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "", s)
    for pat in (r"(?is)<main[^>]*>(.*?)</main>", r'(?is)<div[^>]+id="(?:main|contents|content|tmp_contents)"[^>]*>(.*)',
                r"(?is)<article[^>]*>(.*?)</article>"):
        m = re.search(pat, s)
        if m:
            s = m.group(1)
            break
    s = re.sub(r"(?is)<(header|nav|footer|aside)[^>]*>.*?</\1>", "", s)
    return s


def to_text(s):
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</tr>|</div>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace(" ", " ")
    lines = [ln.strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def pick_links(page_html, base):
    out = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', page_html):
        text = re.sub(r"\s+", " ", to_text(m.group(2))).strip()
        if not text or len(text) > 80 or not PICK.search(text) or SKIP.search(text):
            continue
        url = urllib.parse.urljoin(base, m.group(1))
        if url.startswith("http"):
            out.append({"title": text, "url": url})
    return out


def collect_ward(ward, old):
    old_items = {it["url"]: it for it in (old or {}).get("items", [])}
    links, seen, pages = [], set(), []
    src_urls = [s["url"] for s in ward["sources"]]
    for s in ward["sources"]:
        src = s["url"]
        if not allowed(src):
            print(f"  robots.txt で禁止のためスキップ: {src}")
            continue
        try:
            page = fetch(src)
        except Exception as e:
            print(f"  取得失敗 {src}: {e}", file=sys.stderr)
            continue
        time.sleep(SLEEP)
        if not page:
            continue
        picked = 0
        for ln in pick_links(main_html(page), src):
            if ln["url"] not in seen and ln["url"] not in src_urls:
                seen.add(ln["url"])
                links.append(ln)
                picked += 1
        # 制度ごとのリンクが無く、1ページに複数の制度が並んでいるサイト（例：台東区）は
        # wards.json で "inline": true にしておき、一覧ページの本文をAIで制度ごとに抜き出す
        if not s.get("inline"):
            continue
        text = to_text(main_html(page))[:15000]
        pages.append({
            "url": src, "picked": picked, "text": text,
            "src_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        })

    items = []
    for ln in links[:MAX_ITEMS]:
        url = ln["url"]
        text = ""
        if url.lower().endswith(".pdf") or not allowed(url):
            text = ""
        else:
            try:
                page = fetch(url)
                text = to_text(main_html(page))[:8000] if page else ""
            except Exception as e:
                print(f"  取得失敗 {url}: {e}", file=sys.stderr)
                if url in old_items:  # 一時的な失敗なら前回の内容を使う
                    items.append(old_items[url])
                continue
            time.sleep(SLEEP)
        head = text[:300]
        items.append({
            "title": ln["title"],
            "url": url,
            "closed": bool(CLOSED.search(ln["title"]) or CLOSED.search(head)),
            "text": text,
            "src_hash": hashlib.sha256((ln["title"] + text).encode()).hexdigest()[:16],
        })
    return items, pages


def main():
    wards = json.loads((ROOT / "wards.json").read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for w in wards:
        p = OUT_DIR / f"{w['slug']}.json"
        old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        print(f"{w['name']} …")
        items, pages = collect_ward(w, old)
        p.write_text(json.dumps({
            "slug": w["slug"], "name": w["name"], "sources": [s["url"] for s in w["sources"]],
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
            "items": items,
            "pages": pages,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        n_open = sum(not it["closed"] for it in items)
        print(f"  {len(items)}件（受付終了の表示なし {n_open}件）")


if __name__ == "__main__":
    main()
