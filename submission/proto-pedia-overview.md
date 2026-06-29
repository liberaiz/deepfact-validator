# Proto Pedia 概要欄 コピペ用ドラフト

**用途:** STEP② Proto Pedia 作品ページの「概要」欄に貼り付け（Markdown 対応有無未明記のため、装飾は最小限・改行とリストで読ませる）

**最終確認:** 社長 GO 後にコピペ → Proto Pedia 編集画面で実プレビュー → 必要なら微調整

---

## ↓ ここから下を Proto Pedia 概要欄にコピペ ↓

---

## 情報の Observability を社会に実装するマルチエージェント

ユーザーがネットを見ている瞬間に、AI エージェントが情報の信頼度と利害関係をリアルタイム可視化します。医師である創業者の「真偽判断は一次情報まで遡る」習慣を、マルチエージェント AI で社会全体に拡張するプロダクトです。

### なぜ作るか

誤情報・誇張広告・陰謀論型フェイクが医療領域に流入する現状で、ユーザーが疑問を持つ前に AI Agent が能動介入し、信頼度スコア・構造観察・公的機関ソース URL を提供します。

### DevOps × AI Agent ストーリー

- **Observability**: Cloud Logging / Monitoring で「ユーザーが見た情報履歴」を SRE 的に蓄積・可視化
- **CI/CD**: 信頼ソースホワイトリストを Git 管理・差分監視・ベクトル DB 自動再 deploy
- **SRE**: 「真実の SRE エージェント」コンセプト・情報の障害（誤情報）を予兆検知
- **Postmortem**: 誤情報に騙された後の「警告履歴」を Postmortem 形式で記録・再発防止

### マルチエージェント構成

```
入力（URL / テキスト / LINE / Chrome Extension）
   ↓
[Watcher Agent]      記事抽出・主張抽出・感情強度・出典 URL
   ↓
[Investigator Agent] 125 ドメイン信頼辞書 × Vertex AI Gemini で
                     論調バイアス／事実整合性／対立見解
   ↓
[Validator Agent]    数値統合 + 自然言語の構造観察レポート生成
   ↓
出力（信頼度スコア + 構造観察 + 公的機関ソース URL）
```

全エージェント: Vertex AI Gemini 2.5-flash × temperature=0.0 + seed=42 + top_k=1 で決定化。同一入力 × 3 回で完全一致を Firestore キャッシュで保証（コンテストデモ事故ゼロ）。

### 実機検証結果（v0.3）

| 入力パターン | 信頼度 | ラベル |
|---|---:|---|
| フェイク主張（証拠なき断定） | 20% | 警告 |
| 厚労省一次情報 URL | 98% | 高 |
| 中立報道風（賛否両論） | 59% | 中 |
| 誇張広告（3 日でガン消失） | 20% | 警告 |
| ワクチンフェイク（陰謀論型） | 25% | 警告 |
| 学術的論調（系統的レビュー言及） | 59% | 中 |

→ **98% vs 20% = 78 ポイント振れ幅**（入力依存性完全確認）

### 3 つの利用エントリ

1. **LINE Bot**: 友達追加だけで URL/テキスト送信 → 信頼度 + 判定エビデンス URL を 🚨/⚠️/〽️/✅ アイコン付きで即返信
2. **Chrome Extension（Manifest V3）**: 閲覧中のページに常時介入・DOM オーバーレイで信頼度メーターと構造観察を表示
3. **Web UI Workbench**: 3 エージェントの判定を一画面で精査するダッシュボード

### 既存サービスとの差別化

| 既存 | 何ができる | DeepFact Validator |
|---|---|---|
| NewsGuard | 信頼度スコア（人手評価） | + AI Agent 能動介入（静的→動的） |
| Ground News | 複数視点並列表示 | + 利害関係グラフ可視化（並べる→関係性） |
| AllSides | 左右ラベル | + ユーザー文脈パーソナライズ（一律→個別） |
| ChatGPT / Gemini | 質問→回答 | + 質問前に能動介入（受動→能動） |

### 技術スタック

- **LLM**: Vertex AI Gemini 2.5-flash（GCP billing 経由・Free Tier 制約解消・各 call 30s timeout）
- **実行基盤**: Cloud Run（min-instances=1 + warmup）・asia-northeast1
- **API**: FastAPI（Python 3.12）+ CORS Middleware
- **第三者ソース照合**: Google Fact Check Tools API（IFCN 加盟団体・ja+en 並列）+ Wikipedia REST API（ja+en 並列）+ 15s timeout + httpx 5s + retry 1 回
- **公的機関ソース上位常時挿入**: 厚労省 / PMDA / WHO / CDC / 総務省 + JFC / Snopes / PolitiFact / FullFact / Reuters Fact Check / AFP Fact Check
- **信頼ドメイン辞書**: 125 ドメイン（医療/政府/学術/国際機関/ファクトチェック団体）
- **煽動パターン辞書**: 5 カテゴリ × 143 キーワード（陰謀論用語網羅）
- **Wikipedia noise filter**: アニメ・ゲーム・芸能等 47 キーワードで TF-IDF 誤ヒット除外
- **同一入力決定化**: Firestore 入力ハッシュキャッシュ
- **LINE Bot 永続 event loop**: `run_coroutine_threadsafe` で接続プール持続化
- **Vector Search**: Vertex AI text-embedding-005 + Firestore + cosine similarity（過去類似主張照合・v0.3 実装済）
- **データ**: Firestore（信頼ソース辞書・警告履歴・response cache・記事 embedding）
- **Observability**: Cloud Logging + Monitoring + Postmortem 自動生成
- **フロント**: LINE Bot（実装済・稼働中）/ Chrome Extension（Manifest V3・Phase 2 実装済）/ Web UI Workbench

### 法的リスク対策

「人を攻撃しない・構造を可視化する」原則を全レポートに常設。個人・組織への断定攻撃を禁則とし、「○○という構造」「○○の傾向」形式のみで提示。政治的・宗教的に微妙な主張は「複数の立場が成り立つ構造」を contrarian_views で提示。

### デプロイ済 URL

**`https://deepfact-validator-kjciocymea-an.a.run.app`** — Cloud Run 稼働中（`GET /health` で HTTP 200 確認済・rev 00043-4gj 以降）

### チーム

**株式会社 Liberaiz**（代表取締役 Dr. 加藤）
医師・医学博士・産業医・元院長 × Anthropic Certified 三冠（Claude 101 / AI Fluency / Cowork）
「医師の習慣を AI Agent で社会全体に拡張する」をコアコンセプトに 1 人法人で運営

---

## ↑ ここまでをコピペ ↑

---

## 📋 STEP② 作業手順（社長向け）

1. https://protopedia.net/ にアクセス → アカウント作成（メアド + パスワード）
2. ログイン後「作品を投稿する」ボタン
3. **作品ステータス**: 「完成」を選択
4. **作品タイトル**: `DeepFact Validator`
5. **概要**: 上記ドラフトを丸ごとコピペ
6. **動画**: 60 秒 MP4 を YouTube アップロード後の URL を入力（限定公開で OK）
7. **画像** (5 枚まで): `marketing/hackathon-2026/deepfact-validator/video/out/` から精選
   - 02-hook-full-v7.png（フック）
   - 03-line-v4.png（LINE エビデンス）
   - 04-chrome-v4.png（Chrome 分析）
   - 05-webui-v5.png（Web UI Workbench）
   - + ピッチHTML スクショ or demo-evidence v0.3 スクショ
8. **URL**: `https://deepfact-validator-kjciocymea-an.a.run.app`
9. **タグ**: `DevOps × AI Agent Hackathon 2026`（ハッカソン紐付け推奨）
10. **公開設定**: 一般公開（応募時必須）
11. 投稿 → 作品 URL を STEP③ で使用

## 🎬 YouTube アップロード手順（任意・社長向け）

🟡 **任意です**：Proto Pedia 必須は3項目（ステータス・タイトル・概要）のみ。動画は補強要素です。社長判断 2026-06-23「マストじゃない」確定。アップする場合の手順：

1. https://studio.youtube.com にアクセス（社長 Google アカウント）
2. 右上「作成」→「動画をアップロード」
3. ファイル: `marketing/hackathon-2026/deepfact-validator/video/out/deepfact-demo-v0.2.mp4`（4MB 程度）
4. **タイトル**: `DeepFact Validator — DevOps × AI Agent Hackathon 2026 demo`
5. **説明**: 「マルチエージェント AI で情報の Observability を実装するプロダクトです。」
6. **公開設定**: **限定公開**（URL を知っている人だけ視聴可・コンテスト用に適切）
7. アップロード完了 → 動画 URL を取得（`https://youtu.be/xxxxxxxxxxx`）
8. Proto Pedia 概要欄の「動画」入力欄に URL 貼り付け

---

## 🛡 提出前 アルゴス L2 final QA

Proto Pedia 公開 + STEP③ 送信前に、レンが `Agent(subagent_type:"argus-reviewer")` で本ファイル + 1pager.md + README.md + SUBMISSION-CHECKLIST.md + Proto Pedia 投稿内容を独立目チェック。誇張表現・数値整合性・公的番号・URL 実在・固有名詞を全部突合。
