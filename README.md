# わかりやすい補助金ナビ（東京都の飲食店向け・自動収集の仕組み）

毎朝、次の流れを自動で行います。Macの電源が切れていても、GitHub上で動きます。

```
collect.py       jGrants（デジタル庁）の公開APIから、東京都の飲食店が使える募集中の補助金を集める
ward_collect.py  wards.json に登録した区の公式サイトから、区独自の補助金を集める
   ↓
summarize.py     Claudeで「店主向けの分かりやすい要約」を作る（内容が変わったものだけ）
ward_extract.py  区のページから制度を抜き出して要約する（同上）
   ↓
build.py         補助金ごとのページ・目的別ページ・区ごとのページ・一覧ページを作る
   ↓
GitHub Pages で公開
```

## 手元のMacで試す（AI要約なし）

```bash
cd hojokin
python3 collect.py   # 初回は3分ほど（2回目からは差分だけなので速い）
python3 build.py
python3 -m http.server 8765 --directory site
```

ブラウザで http://localhost:8765 を開きます。

## GitHubで毎日自動で動かす（無料）

1. GitHubで新しいリポジトリを作り、この `hojokin` フォルダの中身を置く（push する）
2. リポジトリの **Settings → Pages** で、Source を **「GitHub Actions」** にする
3. **Settings → Secrets and variables → Actions** で次を登録する
   - Secrets：`ANTHROPIC_API_KEY`（Claude APIのキー。console.anthropic.com で発行）
   - Variables：`SITE_URL`（公開URL。例 `https://<ユーザー名>.github.io/<リポジトリ名>`）
4. **Actions → daily-update → Run workflow** で1回手動実行する。以後は毎朝6時に自動で動く

APIキーを登録しなくても動きます（その場合は要約なしの簡易表示になります）。

## 費用の目安
- GitHub Actions・GitHub Pages：公開リポジトリなら無料
- Claude API：要約は「新しい補助金・内容が変わった補助金」だけに行うので、初回60件前後、その後は1日数件程度。
  1回の実行で要約するのは最大40件（`summarize.py` の `MAX_PER_RUN`）。

## 調整できるところ
| やりたいこと | 場所 |
|---|---|
| 地域を変える・増やす | `collect.py` の `AREAS` |
| 区を増やす | `wards.json` に区名と補助金一覧ページのURLを追加。制度ごとのリンクが無く1ページに並んでいるサイトは `"inline": true` |
| 業種を変える | `collect.py` の `INDUSTRY`（jGrantsの業種名） |
| 除外する手続き | `collect.py` の `EXCLUDE_TITLE` |
| 目的の分類 | `summarize.py` の `PURPOSES` と `build.py` の `PURPOSE_SLUGS` |
| 見た目 | `style.css` |

## 注意
- 情報の出典（jGrants）と「最新情報は公式で確認」の表示は消さないでください。
- 要約はAIが作るため、誤りがありえます。公開前に数件は目で確認してください。
- 申請書類の作成代行は行政書士の独占業務です。このサイトは情報提供と専門家の紹介までにとどめます。
