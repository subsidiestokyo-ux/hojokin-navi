#!/usr/bin/env python3
"""区のページから集めた本文を、Claudeで「制度ごとの要約」にする。

- 制度ごとのページ → 1制度の要約
- 1ページに複数の制度が並ぶ一覧ページ（制度リンクが拾えなかったもの） → 複数の制度を抜き出す
- 結果は data/ward_summaries/<slug>.json。本文が変わっていなければ作り直さない
- 必要なもの：summarize.py と同じ（Python 3.10以上、anthropic、APIキー）
"""
import argparse
import json
import sys
from pathlib import Path

from summarize import MODEL, PURPOSES, load_dotenv

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "data" / "wards"
OUT_DIR = ROOT / "data" / "ward_summaries"

PROGRAM = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "制度の正式名称"},
        "headline": {"type": "string", "description": "飲食店の店主が一目で分かる一言（40字以内）"},
        "who": {"type": "string", "description": "誰が使えるか"},
        "amount": {"type": "string", "description": "いくらもらえるか（上限額・補助率）"},
        "uses": {"type": "array", "items": {"type": "string"}},
        "restaurant_examples": {"type": "array", "items": {"type": "string"}},
        "cautions": {"type": "array", "items": {"type": "string"}},
        "status": {"type": "string", "enum": ["受付中", "受付前", "受付終了", "通年・随時", "不明"]},
        "deadline": {"type": "string", "description": "締切や受付期間。書かれていなければ「要確認」"},
        "restaurant_fit": {"type": "string", "enum": ["高い", "ふつう", "低い"]},
        "is_business_subsidy": {"type": "boolean", "description": "事業者向けの補助金・助成金・奨励金なら true"},
        "purposes": {"type": "array", "items": {"type": "string", "enum": PURPOSES}},
    },
    "required": [
        "name", "headline", "who", "amount", "uses", "restaurant_examples", "cautions",
        "status", "deadline", "restaurant_fit", "is_business_subsidy", "purposes",
    ],
    "additionalProperties": False,
}
MULTI = {
    "type": "object",
    "properties": {"programs": {"type": "array", "items": PROGRAM}},
    "required": ["programs"],
    "additionalProperties": False,
}

SYSTEM = """あなたは、区の補助金・助成金の案内ページを、飲食店の店主向けに分かりやすく書き直す編集者です。
- ページに書かれていることだけを使い、金額・条件・期限を作らないこと。不明なら「募集要項で確認が必要」と書く。
- status は、ページの記載から判断する（「受付終了」「募集終了」の表示があれば受付終了）。判断できなければ「不明」。
- restaurant_fit は、その区にある小さな飲食店が使える見込み。
- 住宅向け・個人向け・商店街団体のみ向けなど、個々の事業者が申請できないものは is_business_subsidy を false にする。
- 申請の可否を断定せず、法的な助言はしないこと。今日の日付は {today} です。"""


def call(client, anthropic, schema, prompt, today):
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        system=SYSTEM.format(today=today),
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason != "end_turn":
        print(f"  スキップ: stop_reason={resp.stop_reason}", file=sys.stderr)
        return None
    text = next((b.text for b in resp.content if b.type == "text"), None)
    return json.loads(text) if text else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60, help="AIに送る最大回数")
    ap.add_argument("--ward", help="特定の区だけ（例：minato）")
    ap.add_argument("--only", help="制度名にこの文字を含むものだけ（試すとき用）")
    args = ap.parse_args()

    try:
        import anthropic
    except ImportError:
        print("anthropic が入っていないため、区の要約をスキップします")
        return
    load_dotenv()
    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError:
        print("APIキーが設定されていないため、区の要約をスキップします")
        return

    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y年%m月%d日")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    calls = 0
    for src_path in sorted(SRC_DIR.glob("*.json")):
        ward = json.loads(src_path.read_text(encoding="utf-8"))
        if args.ward and ward["slug"] != args.ward:
            continue
        out_path = OUT_DIR / f"{ward['slug']}.json"
        out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"items": {}, "pages": {}}

        jobs = []
        for it in ward["items"]:
            if it["text"] and out["items"].get(it["url"], {}).get("src_hash") != it["src_hash"]:
                jobs.append(("item", it))
        for pg in ward.get("pages", []):
            if out["pages"].get(pg["url"], {}).get("src_hash") != pg["src_hash"]:
                jobs.append(("page", pg))

        for kind, x in jobs:
            if calls >= args.limit:
                break
            if args.only and args.only not in x.get("title", ""):
                continue
            if kind == "item":
                prompt = f"{ward['name']}の制度ページです。この制度を要約してください。\n\n【リンク名】{x['title']}\n【本文】\n{x['text']}"
                schema = PROGRAM
            else:
                prompt = (f"{ward['name']}の補助金・助成金の一覧ページです。載っている制度をすべて抜き出し、"
                          f"それぞれ要約してください。\n\n【本文】\n{x['text']}")
                schema = MULTI
            try:
                result = call(client, anthropic, schema, prompt, today)
            except anthropic.AuthenticationError:
                print("APIキーが無効のため、区の要約をスキップします")
                return
            except anthropic.RateLimitError:
                print("利用上限に達したため、残りは次回に回します")
                calls = args.limit
                break
            except anthropic.BadRequestError as e:
                if "credit balance" in str(e.message):
                    print("⚠ APIのクレジット残高が不足しています。チャージ後、次回の実行で残りを要約します")
                    calls = args.limit
                    break
                print(f"  失敗 {x['url']}: {e.status_code} {e.message}", file=sys.stderr)
                continue
            except anthropic.APIStatusError as e:
                print(f"  失敗 {x['url']}: {e.status_code} {e.message}", file=sys.stderr)
                continue
            except anthropic.APIConnectionError:
                print("ネットワークエラーのため、残りは次回に回します", file=sys.stderr)
                calls = args.limit
                break
            calls += 1
            if result is None:
                continue
            if kind == "item":
                out["items"][x["url"]] = {"src_hash": x["src_hash"], "summary": result}
                print(f"  {ward['name']}: {result['name'][:40]}")
            else:
                out["pages"][x["url"]] = {"src_hash": x["src_hash"], "programs": result["programs"]}
                print(f"  {ward['name']}: 一覧ページから {len(result['programs'])}件を抽出")
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"完了: AIに {calls}回 送りました")


if __name__ == "__main__":
    main()
