#!/usr/bin/env python3
"""集めた補助金を、Claudeで「飲食店の店主向けの分かりやすい要約」にする。

- 必要なもの: Python 3.10以上、`pip install anthropic`、環境変数 ANTHROPIC_API_KEY
- 要約は data/summaries/<id>.json に保存。内容が変わっていない補助金は作り直さない（費用の節約）
- APIキーが無い・エラーのときは何もせず終了する（サイトは要約なしでも作れる）
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "subsidies.json"
OUT_DIR = ROOT / "data" / "summaries"
MODEL = "claude-opus-5-5"
MAX_PER_RUN = 40  # 1回の実行で要約する上限（費用の上限の目安）

PURPOSES = [
    "設備・機器",
    "省エネ・脱炭素",
    "IT・キャッシュレス・DX",
    "人材・採用・育成",
    "働き方・賃上げ",
    "開業・事業承継",
    "販路・観光・インバウンド",
    "その他",
]

SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "飲食店の店主が一目で分かる一言（40字以内）"},
        "who": {"type": "string", "description": "誰が使えるか（業種・規模・地域などの条件）"},
        "amount": {"type": "string", "description": "いくらもらえるか（上限額と補助率）"},
        "uses": {"type": "array", "items": {"type": "string"}, "description": "何に使えるか（対象経費）"},
        "restaurant_examples": {
            "type": "array", "items": {"type": "string"},
            "description": "飲食店での具体的な使い方の例。公募情報から妥当と言えるものだけ。無ければ空",
        },
        "cautions": {"type": "array", "items": {"type": "string"}, "description": "申請前に知っておくべき条件・注意点"},
        "restaurant_fit": {"type": "string", "enum": ["高い", "ふつう", "低い"]},
        "tokyo_eligible": {"type": "string", "enum": ["対象", "対象外", "不明"]},
        "purposes": {"type": "array", "items": {"type": "string", "enum": PURPOSES}},
    },
    "required": [
        "headline", "who", "amount", "uses", "restaurant_examples",
        "cautions", "restaurant_fit", "tokyo_eligible", "purposes",
    ],
    "additionalProperties": False,
}

SYSTEM = """あなたは、補助金の公募情報を飲食店の店主向けに分かりやすく書き直す編集者です。
- 渡された公募情報に書かれていることだけを使い、書かれていない金額・条件・期限は作らないこと。
  分からない項目は「募集要項で確認が必要」と書くこと。
- 専門用語は言い換え、短い文で書くこと。
- restaurant_fit は、東京都内の小さな飲食店（個人店〜数店舗）が使える見込み。
- tokyo_eligible は、東京都内の事業者が申請できるか。
- 申請の可否を断定せず、法的な助言はしないこと。"""


def load_items():
    return json.loads(SRC.read_text(encoding="utf-8"))["items"]


def needs_update(rec):
    p = OUT_DIR / f"{rec['id']}.json"
    if not p.exists():
        return True
    return json.loads(p.read_text(encoding="utf-8")).get("src_hash") != rec["src_hash"]


def build_prompt(rec):
    fields = {
        "名称": rec["title"],
        "キャッチコピー": rec["catch"],
        "対象地域": rec["area"] + (" / " + rec["area_detail"] if rec["area_detail"] else ""),
        "対象業種": rec["industry"],
        "従業員数の条件": rec["employees"],
        "利用目的": rec["use_purpose"],
        "補助率": rec["rate"],
        "補助上限額（円）": rec["max_limit"] or "記載なし",
        "受付期間（日本時間）": f"{rec['start']} 〜 {rec['end']}",
        "実施機関": rec["institution"],
        "添付資料": "、".join(rec["attachments"]),
        "詳細": rec["detail_text"],
    }
    body = "\n".join(f"【{k}】{v}" for k, v in fields.items())
    return f"次の公募情報を要約してください。\n\n{body}"


def load_dotenv():
    """手元で試すとき用：hojokin/.env の「ANTHROPIC_API_KEY=...」を読み込む（GitHubではSecretsを使う）"""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:  # 空欄のままなら読み込まない
                os.environ.setdefault(k.strip(), v)


def main():
    # 例：python summarize.py --limit 3  → 3件だけ試す
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=MAX_PER_RUN, help="要約する最大件数")
    args = ap.parse_args()

    try:
        import anthropic
    except ImportError:
        print("anthropic が入っていないため、要約をスキップします（pip install anthropic）")
        return
    load_dotenv()

    todo = [r for r in load_items() if needs_update(r)][: args.limit]
    if not todo:
        print("新しく要約するものはありません")
        return

    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError:
        print("APIキーが設定されていないため、要約をスキップします")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    for rec in todo:
        try:
            resp = client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # 安全上の理由で断られたとき、自動で別モデルが引き継ぐ
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
                system=SYSTEM,
                messages=[{"role": "user", "content": build_prompt(rec)}],
            )
        except anthropic.AuthenticationError:
            print("APIキーが無効または未設定のため、要約をスキップします")
            return
        except anthropic.RateLimitError:
            print("利用上限に達したため、残りは次回に回します")
            break
        except anthropic.APIStatusError as e:
            print(f"  失敗 {rec['title'][:30]}: {e.status_code} {e.message}", file=sys.stderr)
            continue
        except anthropic.APIConnectionError:
            print("ネットワークエラーのため、残りは次回に回します", file=sys.stderr)
            break

        if resp.stop_reason != "end_turn":
            print(f"  スキップ {rec['title'][:30]}: stop_reason={resp.stop_reason}", file=sys.stderr)
            continue
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if not text:
            continue
        summary = json.loads(text)
        summary["src_hash"] = rec["src_hash"]
        summary["model"] = resp.model
        (OUT_DIR / f"{rec['id']}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        done += 1
        print(f"  要約 {done}/{len(todo)}: {rec['title'][:40]}")
    print(f"完了: {done}件を要約しました")


if __name__ == "__main__":
    main()
