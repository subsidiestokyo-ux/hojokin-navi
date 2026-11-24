#!/usr/bin/env python3
"""LINE公式アカウントの友だち全員に「今週の新着補助金」を送る（週1回）。

- 送った補助金は data/line_sent.json に記録し、同じものは二度と送らない（締切間近でも再送しない）
- 新着のうち締切まで DEADLINE_DAYS 日以内のものには「⏰締切間近」の印をつけて先頭に並べる
- 新着が無い週は送らない
- 載せるのは MAX_NEW 件まで。残りは「ほか○件はサイトで」と案内する（残りも送信済みとして記録）
- 初回（記録が無いとき）は、今ある補助金を「送信済み」として記録するだけで送らない
  （開始直後に大量の補助金が一度に届くのを防ぐため）
- 無料プランは月の送信数に上限があるため、残りが足りないときは送らない
- 必要なもの：環境変数 LINE_CHANNEL_ACCESS_TOKEN（Messaging API のチャネルアクセストークン）
  SITE_URL（サイトのURL。リンクに使う）

使い方:
  python line_notify.py --dry-run   … 送らずに、送る予定の文面だけ表示する（記録も変えない）
  python line_notify.py             … 送信する
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SENT = DATA / "line_sent.json"
JST = timezone(timedelta(hours=9))
API = "https://api.line.me/v2/bot"
SITE_NAME = "わかりやすい補助金ナビ"
MAX_NEW = 5        # 1回に載せる新着の上限
DEADLINE_DAYS = 14  # 何日以内の締切に「⏰締切間近」の印をつけるか
GOOD_FIT = ("高い", "ふつう")


def site_url():
    return os.environ.get("SITE_URL", "").rstrip("/")


def load_candidates():
    """サイトに載せている補助金のうち、飲食店との相性が高い・ふつうのものを集める"""
    out = []
    src = json.loads((DATA / "subsidies.json").read_text(encoding="utf-8"))
    for r in src["items"]:
        p = DATA / "summaries" / f"{r['id']}.json"
        if not p.exists():
            continue
        s = json.loads(p.read_text(encoding="utf-8"))
        if s.get("restaurant_fit") not in GOOD_FIT or s.get("tokyo_eligible") == "対象外":
            continue
        out.append({
            "key": "jg:" + r["id"], "name": r["title"], "amount": s["amount"],
            "end": r.get("end"), "deadline": (r.get("end") or "")[:10],
            "path": f"/s/{r['id']}.html", "fit": s["restaurant_fit"],
        })
    for wp in sorted((DATA / "wards").glob("*.json")):
        w = json.loads(wp.read_text(encoding="utf-8"))
        sp = DATA / "ward_summaries" / wp.name
        if not sp.exists():
            continue
        sm = json.loads(sp.read_text(encoding="utf-8"))
        progs = [v["summary"] for v in sm.get("items", {}).values()]
        progs += [p for v in sm.get("pages", {}).values() for p in v["programs"]]
        for s in progs:
            if not s.get("is_business_subsidy") or s.get("restaurant_fit") not in GOOD_FIT:
                continue
            if s.get("status") not in ("受付中", "通年・随時"):
                continue
            out.append({
                "key": f"w:{w['slug']}:{s['name']}", "name": f"【{w['name']}】{s['name']}",
                "amount": s["amount"], "end": None, "deadline": s.get("deadline", ""),
                "path": f"/w/{w['slug']}.html", "fit": s["restaurant_fit"],
            })
    return out


def short(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def fmt_end(end):
    if not end:
        return ""
    d = datetime.strptime(end[:10], "%Y-%m-%d")
    return f"{d.month}/{d.day}締切"


def is_soon(x, today):
    """締切まで DEADLINE_DAYS 日以内か"""
    if not x["end"]:
        return False
    limit = (today + timedelta(days=DEADLINE_DAYS)).isoformat()
    return today.isoformat() <= x["end"][:10] <= limit


def build_message(new_items, today):
    base = site_url()
    lines = [f"【{SITE_NAME}】{today.month}/{today.day} の補助金情報",
             "", f"■ 今週の新着（{len(new_items)}件）"]
    for x in new_items[:MAX_NEW]:
        mark = "⏰締切間近 " if is_soon(x, today) else ""
        lines.append(f"・{mark}{short(x['name'], 40)}")
        info = "／".join(v for v in (short(x["amount"], 40), fmt_end(x["end"])) if v)
        if info:
            lines.append(f"　{info}")
        if base:
            lines.append(f"　{base}{x['path']}")
    if len(new_items) > MAX_NEW:
        lines.append(f"　ほか{len(new_items) - MAX_NEW}件はサイトで")
    lines += ["", "最新の条件は、必ず公式の募集要項でご確認ください。"]
    if base:
        lines.append(f"一覧はこちら：{base}/")
    return "\n".join(lines)[:4900]  # LINEのテキストは5000文字まで


def api(method, path, token, body=None, retry_key=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if retry_key:
        req.add_header("X-Line-Retry-Key", retry_key)  # 通信の再試行で二重送信しないため
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def enough_quota(token):
    """今月の残り送信数が、友だちの人数より多いか確認する（分からなければ送る）"""
    try:
        quota = api("GET", "/message/quota", token)
        used = api("GET", "/message/quota/consumption", token).get("totalUsage", 0)
    except urllib.error.HTTPError as e:
        print(f"  送信上限を確認できませんでした（{e.code}）。そのまま続けます")
        return True
    if quota.get("type") != "limited":
        return True
    remaining = quota.get("value", 0) - used
    friends = None
    try:
        day = (datetime.now(JST) - timedelta(days=2)).strftime("%Y%m%d")
        f = api("GET", f"/insight/followers?date={day}", token)
        friends = f.get("targetedReaches")
    except urllib.error.HTTPError:
        pass
    print(f"  今月の残り送信数: {remaining}（友だち数の目安: {friends if friends is not None else '不明'}）")
    if friends is not None and remaining < friends:
        print("  ⚠ 残り送信数が友だち数より少ないため、今回は送りません（全員に届かず中途半端になるため）")
        return False
    return remaining > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="送らずに文面だけ表示する")
    args = ap.parse_args()

    today = datetime.now(JST).date()
    cands = load_candidates()
    sent = json.loads(SENT.read_text(encoding="utf-8")) if SENT.exists() else None

    if sent is None:
        print(f"初回のため、今ある {len(cands)}件を送信済みとして記録します（今回は送りません）")
        token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
        if token:  # トークンが正しいかだけ確認する（メッセージは送らない）
            try:
                info = api("GET", "/info", token)
                print(f"  LINEとの接続OK：{info.get('displayName')}（{info.get('basicId')}）")
            except urllib.error.HTTPError as e:
                print(f"❌ LINEのトークンが正しくないようです（{e.code}）。登録し直してください")
                sys.exit(1)
        if not args.dry_run:
            SENT.write_text(json.dumps({"sent": sorted(c["key"] for c in cands), "history": []},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
            return
        sent = {"sent": [], "history": []}

    done = set(sent["sent"])
    new_items = [c for c in cands if c["key"] not in done]
    # 締切間近 → 相性「高い」 → 締切が早い順
    new_items.sort(key=lambda c: (not is_soon(c, today), c["fit"] != "高い", c["end"] or "9999"))
    soon = sum(is_soon(c, today) for c in new_items)

    if not new_items:
        print("新着がないため、今週は送りません")
        return

    text = build_message(new_items, today)
    print("----- 送る文面 -----")
    print(text)
    print("--------------------")
    if args.dry_run:
        print("（--dry-run のため送信しません）")
        return

    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        print("LINE_CHANNEL_ACCESS_TOKEN が未設定のため、送信をスキップします")
        return
    if not enough_quota(token):
        return
    try:
        api("POST", "/message/broadcast", token,
            body={"messages": [{"type": "text", "text": text}]}, retry_key=str(uuid.uuid4()))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        print(f"❌ 送信に失敗しました（{e.code}）: {detail}")
        sys.exit(1)

    sent["sent"] = sorted(done | {c["key"] for c in new_items})
    sent["history"] = (sent.get("history", []) + [{
        "date": today.isoformat(), "new": len(new_items), "deadline": soon}])[-52:]
    SENT.write_text(json.dumps(sent, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 送信しました（新着 {len(new_items)}件、うち締切間近 {soon}件）")


if __name__ == "__main__":
    main()
