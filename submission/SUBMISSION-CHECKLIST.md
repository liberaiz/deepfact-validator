# 提出チェックリスト — DeepFact Validator × DevOps × AI Agent Hackathon 2026

**提出締切：** 2026-07-10（金）23:59 JST
**応募方法：** 3 STEP（参加申込 → Proto Pedia 登録 → 作品提出フォーム）
**一次情報：** https://findy.notion.site/devops-ai-agent-hackathon-2026

---

## ✅ 必須要件 — Google Cloud 技術スタック（Notion 一次情報）

### 必須①：Google Cloud アプリケーション実行プロダクト（1つ以上）

- [x] **Cloud Run** 採用（rev `deepfact-validator-00008` 以降・asia-northeast1）
- [x] HTTP 200 動作確認済（`GET /health` エンドポイント・117ms 応答）

### 必須②：Google Cloud AI 技術（1つ以上）

- [x] **Gemini Enterprise Agent Platform（旧 Vertex AI）** 採用
  - Gemini 2.5-flash via `genai.Client(vertexai=True, project=..., location=...)`
  - 3 エージェント全てに `temperature=0.0` + `seed=42` + `top_k=1` 統一適用
- [x] Free Tier 制約解消（billing 経由・本番運用適格）

---

## 📤 応募 3 STEP

### STEP① ハッカソンへの参加申し込み

- [ ] **🚨 社長確認**：参加申込済みか？
- [ ] 未申込なら Notion 内「参加申込フォーム」から申込
- [ ] 申込完了スクショ取得

### STEP② 作品をつくって Proto Pedia に登録

**📋 Proto Pedia 仕様（公式 helpcenter 一次情報・2026-06-23 確認）:**
- **必須項目は3つのみ**：作品ステータス（"完成"を選択）／作品タイトル／概要
- 動画は **YouTube URL のみ対応**（MP4 直接アップロード不可）→ 🟡 **任意**（Proto Pedia 必須は3項目のみ・YouTube 化は補強要素）。社長判断 2026-06-23「マストじゃない」確定。アップする場合は限定公開 OK
- 画像は **5 枚まで**（推奨サイズ未明記・still 6 枚から精選）
- 公開ステータス：下書き保存 / 限定共有 / 一般公開（応募時は一般公開）
- ハッカソン応募の紐付け：イベント名タグ付け推奨（専用フォームなし）

**作業手順:**
- [ ] Proto Pedia アカウント作成（社長アカウント）
- [ ] **YouTube に 60秒 MP4 アップロード**（限定公開推奨・URL 取得）
- [ ] 作品ページ作成
  - [ ] プロダクト名: DeepFact Validator
  - [ ] 作品ステータス: 完成
  - [ ] 概要（1pager.md の内容を整形）
  - [ ] スクリーンショット（5 枚精選）: ピッチ HTML v0.3 / demo-evidence v0.3 / Chrome Ext mock / Web UI mockup v0.3 / 6 パターン信頼度判定表
  - [ ] 動画: 60秒 Remotion MP4（YouTube URL）
  - [ ] 動作確認 URL: `https://deepfact-validator-kjciocymea-an.a.run.app`
  - [ ] 技術スタック: Cloud Run + Vertex AI Gemini 2.5-flash + FastAPI + LINE Messaging API + Chrome Extension（Manifest V3）
  - [ ] タグ: 「DevOps × AI Agent Hackathon 2026」等（ハッカソン紐付け）
- [ ] アイキャッチ画像作成（Liberaiz ブランド調和・紙地+紺文字+ゴールド minimal[[feedback_design_skills_and_sense]] 準拠・紺金ベタ手癖回避）
- [ ] **🚨 社長 GO 必須**（外部公開プラットフォーム掲載）

### STEP③ 作品提出フォームから最終応募

- [ ] Notion 内「作品提出フォーム」URL を取得
- [ ] 必要情報入力
  - [ ] Proto Pedia URL
  - [ ] デプロイ済プロジェクト URL: `https://deepfact-validator-kjciocymea-an.a.run.app`
  - [ ] 採用技術スタック（Cloud Run + Vertex AI Gemini）
  - [ ] その他必要項目（フォーム確認後）
- [ ] **🚨 社長最終確認**後に送信
- [ ] 受領メール保管

---

## 🎯 審査基準 5項目への対応度（自己評価）

### 1. AIエージェントが価値の中心になっているか

- [x] **3 エージェント自律連携**：Watcher → Investigator → Validator
- [x] **必然性の根拠**：素の Gemini で代替不可な 5 基準（状態継続・外部連携・専門深さ・HITL・業務自動化）を README に明記
- [x] **自律的振る舞い**：入力→構造抽出→ソース照合→判定統合を全自動で実行
- [x] **🆕 第三者ソース能動取得**：Google Fact Check Tools API + Wikipedia API を並列で叩き、判定エビデンスを URL 付きで取得

### 2. 設定した課題へのアプローチ力

- [x] **課題設定**：誤情報・誇張広告・陰謀論型フェイクの医療領域流入
- [x] **対象ユーザ**：一般ユーザ（LINE Bot）+ Web 閲覧者（Chrome Extension）
- [x] **提供価値**：医師の「真偽は一次情報まで辿る」習慣を AI Agent で社会拡張
- [x] **新規性**：既存サービス（NewsGuard / Ground News / AllSides）との明確な差別化（静的→動的・並べる→関係性で診る・受動→能動）
- [x] **ストーリー一貫性**：北極星（[[feedback_primary_source_mandatory]]）から課題定義→アーキテクチャ→ピッチまで貫通

### 3. ユーザビリティ

- [x] **LINE Bot**：友達追加だけで誰でも利用可能（URL/テキスト送信→分析結果返信）
- [x] **🆕 LINE Bot 判定エビデンス・ソース表示**：📚 セクションで Wikipedia / Fact Check 団体の検証 URL を提示（ユーザーが自分で確認可能）
- [x] **Chrome Extension**：DOM オーバーレイ常駐 + MutationObserver + SPA URL hook（v0.3 Phase 2 実装済）・SSE は Phase 3
- [x] **HTTP API**：直接利用可能（外部システム連携用）

### 4. 実用性・体験価値の魅力（突き抜けたら加点）

- [x] **実機検証**：6 パターンで信頼度差 78pt（98% vs 20%）
- [x] **同一入力一致保証**：Firestore キャッシュで完全一致保証（`temperature=0+seed=42+top_k=1` はベストエフォート併用・コンテストデモ事故ゼロ）
- [x] **🆕 公的機関ソース上位常時挿入**：厚労省/PMDA/WHO/CDC/総務省 + JFC/Snopes/PolitiFact/Reuters Fact Check/FullFact/AFP Fact Check 等の URL を LINE / API レスポンスに同梱・Wikipedia オンリー構造を排除
- [x] **🆕 煽動パターン辞書**：143 キーワード × 5 カテゴリで Gemini 落ちても警告判定（high_alert / evidence_lack / urgency / medical_fraud / conspiracy・マイクロチップ/5G/ナノマシン/思想統制/極秘計画/ビル・ゲイツ/ビッグファーマ 等網羅）
- [x] **🆕 信頼度アイコン**：🚨警告 / ⚠️低 / 〽️中 / ✅高 で LINE 表示の即時判別性向上
- [x] **🆕 Wikipedia noise filter**：アニメ・ゲーム・芸能等の TF-IDF 誤ヒット（仮面ライダー/デジモン/メタルギア/平成 等）を自動除外
- [x] **リアルタイム能動介入**：Chrome Extension が「質問前に介入」（受動→能動）
- [x] **「Hello World と同じスコア問題」完全解消**：v0.1 ヒューリスティック → v0.2 Gemini → v0.3 Vertex AI → v0.4 公的機関ソース上位挿入 で完全克服

### 5. 実装力

- [x] **技術選定の納得度**：Cloud Run + Vertex AI（Free Tier 制約解消・本番運用適格）
- [x] **拡張性**：Watcher / Investigator / Validator の独立エージェント設計・新規エージェント追加容易
- [x] **実運用配慮**：
  - min-instances=1（cold start 回避）
  - Cloud Logging + Monitoring（Observability）
  - Secret Manager 連携（GEMINI_API_KEY/LINE/GOOGLE_FACT_CHECK_API_KEY）
  - Firestore 入力ハッシュキャッシュ（同一入力完全一致保証）
  - **🆕 永続 event loop**（`asyncio.run` でなく `run_coroutine_threadsafe`・接続プール持続化）
  - **🆕 Timeout 制御**：Gemini 各 call 30s + gather_evidence 15s + httpx 5s + retry 1 回
- [x] **🆕 多層エビデンス基盤**：
  - **125 ドメイン信頼辞書**（医療/政府/学術/国際機関/ファクトチェック団体）
  - **143 煽動キーワード辞書**（5 カテゴリ・マイクロチップ/5G/ナノマシン/思想統制/極秘計画/ビル・ゲイツ 等）
  - **公的機関 URL 上位常時挿入**（厚労省/PMDA/WHO/CDC/総務省 + JFC/Snopes/Reuters Fact Check 等）
  - **Google Fact Check Tools API** ja+en 両言語並列
  - **Wikipedia REST API** ja+en + noise filter（アニメ・芸能等除外）
- [x] **🆕 信頼度アイコン**（🚨警告/⚠️低/〽️中/✅高）：LINE Bot の判別性向上
- [x] **Buy→Remix→Resell 原則**：既存社内プロダクト 構造の流用で実装コスト最小化（[[feedback_buy_remix_resell]]）

---

## 🛡 提出前 アルゴス L2 独立目チェック項目

提出 24 時間前までに 🛡️ アルゴス（argus-reviewer）で全提出物を独立目チェック：

- [ ] README.md（v0.3 セクション 数値・URL・技術スタック）
- [ ] ピッチ HTML v0.3（誇張表現・出典・固有名詞・数値整合性）
- [ ] demo-evidence v0.3（6 パターン スコア整合性・スクショと数値の一致）
- [ ] 1pager.md（差別化主張・実機検証結果・連絡先）
- [ ] Proto Pedia 作品ページ（プロダクト概要・URL・スクショ・連絡先）
- [ ] 作品提出フォーム 入力前 最終目視確認

---

## 🚨 提出前 ゼロタイポゲート（[[feedback_official_number_zero_typo]]）

- [ ] Cloud Run URL 完全一致確認（`https://deepfact-validator-kjciocymea-an.a.run.app`）
- [ ] Proto Pedia URL 完全一致確認
- [ ] 連絡先メール 使い分け確認（`info@liberaiz.co.jp` / `liberaiz.ceo@gmail.com`）
- [ ] `node automation/identifier-guard/check.mjs submission/` で機械検証 PASS

---

## ❓ 追加情報確認要（Notion 一次情報・スクショ範囲外）

社長 Notion スクショ範囲では下記が未確認。「ルール」「スケジュール」タブを追加スクショ要：

- [ ] GitHub 公開リポジトリの提出有無
- [ ] デモ動画の提出有無・仕様（時間・形式・言語）
- [ ] ピッチ資料の提出有無・仕様（PDF/HTML・枚数・言語）
- [ ] アーキテクチャ図 の提出有無・形式
- [ ] STEP③ 作品提出フォームの正確な URL

---

## 📅 公式スケジュール（Notion 一次情報・2026-06-22 確定）

| 日程 | イベント | 備考 |
|---|---|---|
| 2026/6/7（日）13:00 | チームビルディング | 個人参加可・終了済 |
| 2026/6月 上旬〜下旬 | Boot Camp | 開催中（社長参加状況要確認） |
| **2026/7/10（金）23:59** | **プロジェクト提出〆切** | Proto Pedia 経由 |
| 2026/7/13（月）〜 | 一次審査（運営事務局） | |
| 2026/7/21〜 | 二次審査（外部有識者） | |
| 2026/7/30（木） | **二次審査通過 10 チーム告知** | Google Cloud Japan ブログ |
| **2026/8/19（水）** | **最終発表（10 チーム現地登壇）** | **渋谷 Google オフィス（渋谷ストリーム）** |
| 2026/9月予定 | アフターイベント | 優秀賞外でも審査員注目チーム登壇可 |

## 📁 質担保スケジュール（社長指示「急がない・質を担保」）

| 日 | アクション | 担当 |
|---|---|:---:|
| 6/22-6/30 | 🛡️ アルゴス L2 × 1 周目 + Chrome Extension 実装推進 + 質担保 | レン |
| 6/22-6/30 | Boot Camp 録画/資料 確認 + Proto Pedia アカウント作成 | 社長 |
| 7/1-7/5 | 🛡️ アルゴス L2 × 2 周目 + デモ動画作成（必要なら） | レン + 社長 |
| 7/6-7/8 | Proto Pedia 登録（STEP②）+ 社長最終味見 | 社長 + レン |
| 7/9 | STEP① 参加申込（未済の場合）+ STEP③ 作品提出フォーム入力 | 社長 + レン |
| **7/10 23:59** | **提出締切** | — |

## 🎯 二次審査通過を狙う質ライン

二次審査通過 = 10 チームのみ登壇。質担保の北極星：

- [ ] 🛡️ アルゴス L2 を最低 2 周（提出 1 週前と前日）
- [ ] ピッチ HTML v0.3 を PC + iPhone Safari 両方で社長味見済
- [ ] 6 パターン信頼度判定 + 同一入力×3 完全一致 を Proto Pedia 上で再現可能な形で記述
- [ ] アーキテクチャ図を Proto Pedia 用にスタンドアロン化（demo-evidence v0.3 から切出）
- [ ] 「素の Gemini で代替不可」5 基準を Proto Pedia 概要で明示
- [ ] 既存サービスとの差別化表（NewsGuard / Ground News / AllSides / ChatGPT 比較）を Proto Pedia に組込
- [x] Chrome Extension Phase 2 実装完了（DOM オーバーレイ常駐 + MutationObserver + SPA URL hook + popup 経由単発分析）— 「突き抜けた体験価値」加点狙い・要デプロイ稼働確認
- [ ] 二次審査通過時の **8/19 渋谷登壇プレゼン資料** 雛形を提出時点で着手済

---

## 関連 memory

- [[project_hackathon_deepfact_validator]] プロジェクト memory
- [[feedback_primary_source_mandatory]] 一次情報マスト（V29 朝の Notion スクショで正式要件確定）
- [[feedback_distribution_autonomy]] 配布物・公開作業はアップ前完全自律化
- [[feedback_argus_double_check]] 🛡️ アルゴス ダブルチェック体制
- [[feedback_dont_call_skeleton_working]] 機械検証必須原則
- [[feedback_official_number_zero_typo]] 公的番号ゼロタイポゲート
