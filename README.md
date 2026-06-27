# welu-threads-poster（放課後等デイ特化）

放課後等デイサービス（放デイ）専門のキャリア相談「Welu」のThreads投稿文を、
**自動生成してDiscordに届ける**運用。届いた本文をコピペしてThreadsに貼るだけ。Meta APIは不要。

## 仕組み
GitHub Actions（cron・無料）→ Claude APIで生成 → Discord Webhookへ配信。
**1日1回 07:00 JST**に、5タイプの投稿文がまとめて届く。

## バズの型（NIGUN準拠）
バイラルの核は **データ × 比較 × 具体数字（数倍差）× 強い断言 × 1行詰め**。
全タイプ共通で「1投稿に必ず具体的な数字を1つ以上／120〜180字／前置きなし」をルール化。
（NIGUNで2万インプを取った「業界別データ型」の構造を放デイに移植）

## 投稿タイプ（5種＝NIGUN構成の放デイ版）
| key | ラベル | 役割 |
|---|---|---|
| viral | 🔥 データ・比較 | 運営母体別/地域別の年収・条件差を数字で（最強バイラル） |
| ranking | 📊 まとめ・見抜き方 | いい放デイ/危ない放デイの見抜き方（保存される） |
| insider | 💢 内部・タブー | 給料・送迎・加算・質のばらつきを本音で |
| career | 🚀 キャリア・逆張り | 転職は前向き・児発管・事業所を変えれば変わる |
| episode | 🤝 共感・エピソード | 現場のあるある・子どもの成長（ファン化／数字なし可） |

## 重複防止
- 各タイプに切り口プールを用意。`history.json` で使った切り口を記録し、一周するまで再登場させない。
- 直近の投稿文をAIに渡し、言い回し・数字の見せ方も被らせない。
- GitHub Actionsが毎回 `history.json` を更新コミット（`permissions: contents: write`）。

## ファイル
deliver.py（生成＋配信）／discord_sender.py（Discord送信）／history.py（重複防止）／
history.json（履歴）／.github/workflows/welu-discord-deliver.yml（07:00配信＋手動＋履歴コミット）

---

## セットアップ手順

### Step 0. Welu の Threads アカウントを作る（まだ無い）
1. Instagramアプリ → プロフィール → 左上の名前 → 「アカウントを追加」→「新しいアカウントを作成」
   - NIGUN（@suguru_0909）とは**完全に別アカウント**。
2. Threadsアプリで、作ったInstagramアカウントで「Threadsに参加」
3. プロフィール設定：
   - 名前：`Welu｜放課後等デイ専門の転職・キャリア相談`
   - ユーザーネーム候補：`welu_houday` / `welu_career` / `welu_hds`
   - bio：
     ```
     放課後等デイで働くあなたへ。
     やりがいも、ちゃんとした待遇も、両方あきらめなくていい。
     自社でも障害福祉事業所を運営。放デイ現場のリアルを本音で。
     ▼無料のキャリア相談はこちら👇
     ```
   - リンク：Jicoo予約URL（LP公開後はLPでも可）

### Step 1. Discord Webhook を作る
Welu専用チャンネル（例 `#welu投稿`）→ 設定 → 連携サービス → ウェブフック → 新規作成 → URLをコピー

### Step 2. GitHubに登録してpush
Private リポジトリ `welu-threads-poster` を作成しファイル一式をpush →
Settings → Secrets and variables → Actions で `ANTHROPIC_API_KEY` と `DISCORD_WEBHOOK_URL` を登録

### Step 3. テスト
Actions → welu-discord-deliver → Run workflow → `dry_run=true`（生成のみ）→ `dry_run=false`（実配信）

## 補足
- モデルは `deliver.py` 内で `claude-sonnet-4-6` に固定（`MODEL` 環境変数の空文字事故を回避）。
- 個別タイプだけ出す場合は Run workflow の `post_type` で `viral` 等を指定。
