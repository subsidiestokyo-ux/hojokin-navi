#!/usr/bin/env python3
"""APIキーがまだ使えるかを確認する（費用はかからない：モデル情報を1回取得するだけ）。

使えないときは終了コード1で終わる。GitHub Actionsではその実行が「失敗」になり、
GitHubから登録メールアドレスに通知が届くので、キーの期限切れや無効化に気づける。
"""
import sys

from summarize import MODEL, load_dotenv


def main():
    import anthropic

    load_dotenv()
    try:
        client = anthropic.Anthropic()
        client.models.retrieve(MODEL)
    except anthropic.AuthenticationError:
        print("❌ APIキーが無効です（期限切れ・削除・入力ミスの可能性）。新しいキーを登録してください。")
        sys.exit(1)
    except anthropic.PermissionDeniedError:
        print("❌ APIキーに権限がありません。キーの設定を確認してください。")
        sys.exit(1)
    except anthropic.AnthropicError as e:
        # キー未設定（AnthropicError）や一時的な通信エラーなど
        print(f"❌ APIキーを確認できませんでした: {e}")
        sys.exit(1)
    print("✅ APIキーは有効です")


if __name__ == "__main__":
    main()
