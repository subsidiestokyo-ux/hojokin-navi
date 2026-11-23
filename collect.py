#!/usr/bin/env python3
"""jGrants公開APIから「東京都の飲食店が使える、募集中の補助金」を集める。

標準ライブラリだけで動く（Macに最初から入っているPythonでも可）。
結果は data/subsidies.json に保存する。前回から変わっていない補助金は詳細を取り直さない。
"""
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.jgrants-portal.go.jp/exp/v1/public/subsidies"
# jGrantsの検索はキーワード必須（2文字以上）なので、よく使われる語で何回か検索してまとめる
KEYWORDS = ["補助金", "助成金", "支援", "事業", "奨励金", "給付金"]
AREAS = ["東京都", "全国"]
INDUSTRY = "宿泊業、飲食サービス業"
# 新規の申請ではない手続き（報告・届出・請求・採択後の申請）は除外する
EXCLUDE_TITLE = re.compile(
    r"状況報告|完了後|実績報告|変更申請|変更届|撤回届|中止届|奨励金請求|交付申請等|共同申請|各種申請"
)
# 「全国」扱いでも、実際は東京以外の自治体向けのもの（例：【倉敷市】、京都市〜）は除外する
OTHER_LOCAL = re.compile(r"【(?!東京)[^】]*[都道府県市町村]】|^(?!東京)[^\s【]{1,6}市(?!場)|京都|成田")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "subsidies.json"
UA = "hojokin-collector/0.1"
JST = timezone(timedelta(hours=9))
SLEEP = 1.0  # APIへの負荷を抑えるため、1秒あける


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:  # ネットワークの一時的な失敗は少し待って再試行
            if i == retries - 1:
                raise
            print(f"  再試行 ({e})", file=sys.stderr)
            time.sleep(5 * (i + 1))


def search(keyword, area):
    q = urllib.parse.urlencode({
        "keyword": keyword,
        "sort": "acceptance_end_datetime",
        "order": "ASC",
        "acceptance": "1",  # 募集中のみ
        "industry": INDUSTRY,
        "target_area_search": area,
    })
    return get_json(f"{API}?{q}").get("result", [])


def html_to_text(s):
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</tr>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "・", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace(" ", " ")
    lines = [ln.strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def to_jst(s):
    """'2026-11-30T14:59:00.000Z' → '2026-11-30 23:59'（日本時間）"""
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)", s)
    if not m:
        return None
    dt = datetime(*map(int, m.groups()), tzinfo=timezone.utc).astimezone(JST)
    return dt.strftime("%Y-%m-%d %H:%M")


def fetch_detail(sid):
    res = get_json(f"{API}/id/{sid}").get("result") or []
    if not res:
        return None
    d = res[0]
    attach = []
    for key in ("application_guidelines", "outline_of_grant", "application_form"):
        for f in d.get(key) or []:  # PDF本体（base64）は大きいので名前だけ残す
            if f.get("name"):
                attach.append(f["name"])
    detail_text = html_to_text(d.get("detail"))
    rec = {
        "id": d["id"],
        "title": (d.get("title") or "").strip(),
        "catch": (d.get("subsidy_catch_phrase") or "").strip(),
        "detail_text": detail_text[:8000],
        "use_purpose": d.get("use_purpose") or "",
        "industry": d.get("industry") or "",
        "area": d.get("target_area_search") or "",
        "area_detail": d.get("target_area_detail") or "",
        "employees": d.get("target_number_of_employees") or "",
        "rate": d.get("subsidy_rate") or "",
        "max_limit": d.get("subsidy_max_limit") or 0,
        "start": to_jst(d.get("acceptance_start_datetime")),
        "end": to_jst(d.get("acceptance_end_datetime")),
        "project_end": to_jst(d.get("project_end_deadline")),
        "institution": d.get("institution_name") or "",
        "url": d.get("front_subsidy_detail_page_url") or f"https://www.jgrants-portal.go.jp/subsidy/{sid}",
        "attachments": attach,
    }
    # 要約を作り直すかどうかの判定に使う（内容が変わったら作り直す）
    rec["src_hash"] = hashlib.sha256(
        json.dumps({k: rec[k] for k in rec if k != "attachments"}, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]
    return rec


def main():
    old = {}
    if OUT.exists():
        old = {r["id"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))["items"]}

    found = {}
    for area in AREAS:
        for kw in KEYWORDS:
            items = search(kw, area)
            print(f"検索 {area} / {kw}: {len(items)}件")
            for it in items:
                found[it["id"]] = it
            time.sleep(SLEEP)

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    items, fetched = [], 0
    for sid, it in found.items():
        title = it.get("title") or ""
        if EXCLUDE_TITLE.search(title):
            continue
        if it.get("target_area_search") == "全国" and OTHER_LOCAL.search(title):
            continue
        end = to_jst(it.get("acceptance_end_datetime"))
        if end and end < now:  # 締切を過ぎているのに「募集中」で返るものがあるため
            continue
        sig = hashlib.sha256(json.dumps(it, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        if sid in old and old[sid].get("list_sig") == sig:
            items.append(old[sid])
            continue
        rec = fetch_detail(sid)
        fetched += 1
        time.sleep(SLEEP)
        if rec:
            rec["list_sig"] = sig
            items.append(rec)

    # 一覧に締切が載っていないものもあるので、詳細の締切でもう一度ふるいにかける
    items = [r for r in items if not (r.get("end") and r["end"] < now)]
    items.sort(key=lambda r: r.get("end") or "9999")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source": "jGrants（デジタル庁）公開API",
        "items": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    closed = len(set(old) - {r["id"] for r in items})
    print(f"完了: 募集中 {len(items)}件（詳細を新たに取得 {fetched}件、募集終了で外れた {closed}件）")


if __name__ == "__main__":
    main()
