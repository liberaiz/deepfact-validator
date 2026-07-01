# DeepFact Validator

**ユーザーがネットを見ている瞬間に、AIエージェントが情報の信頼度と利害関係をリアルタイム可視化する**
＝**「情報のObservability」を社会に実装する**マルチエージェント・ブラウザ拡張

**DevOps × AI Agent Hackathon 2026 応募プロダクト**（Findy／Google Cloud Japan協賛・締切 2026-07-10）

- 📦 **GitHub**: https://github.com/liberaiz/deepfact-validator
- 🚀 **Live**: https://deepfact-validator-kjciocymea-an.a.run.app
- 🔄 **CI/CD**: [![validate-trust-sources](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml/badge.svg)](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml)

---

## なぜ作るか

医師である社長（Dr.加藤）は「**真偽判断は一次情報まで追う**」を北極星とする ([[feedback_primary_source_mandatory]])。
この医師の習慣を、AIエージェントで社会全体に拡張する＝ **情報のObservability** を実装する。

### 「素のGemini で代替不可」5基準
1. **状態継続**：発信源の過去ポジショントーク蓄積
2. **外部連携**：複数ニュースAPI／SNS／論文DB／利害関係DB
3. **専門深さ**：一次情報追跡＋利害関係分析
4. **HITL**：ユーザーが警告を見て判断
5. **業務自動化**：常時監視→診断→アラート→警告履歴蓄積

## DevOps文脈接続（フレーム🅰）

| DevOps文脈 | 実装 |
|---|---|
| **Observability** | Cloud Logging/Monitoring で「ユーザーが見た情報履歴」を SRE的に蓄積・可視化・アラート |
| **CI/CD** | 信頼ソース ホワイトリストを Git管理・差分監視・ベクトルDB自動再 deploy |
| **SRE** | 「真実のSREエージェント」コンセプト・情報の障害（誤情報）を予兆検知 |
| **Postmortem** | 誤情報に騙された後の「警告履歴」を Postmortem 形式で記録・再発防止 |

## 既存サービスとの差別化

| 既存 | 何ができる | DeepFact Validator | 差分 |
|---|---|---|---|
| NewsGuard | 信頼度スコア（人手評価） | ✅+ AI Agent能動介入 | 静的→動的 |
| Ground News | 複数視点並列表示 | ✅+ 利害関係グラフ可視化 | 並べる→関係性で診る |
| AllSides | 左右ラベル | ✅+ ユーザー文脈パーソナライズ | 一律→個別 |
| ChatGPT/Gemini | 質問→回答 | ✅+ 質問前に介入 | 受動→能動 |

## 技術スタック

| 役割 | 技術 | 既存社内プロダクト流用 |
|---|---|:---:|
| 実行基盤 | Cloud Run（min-instances=1 + warmup） | ✅ |
| API | FastAPI（Python 3.12） | ✅ |
| AI Core | **Gemini 2.5 Flash**（google-genai SDK 1.x・AQ.Ab～新auth key対応） | ✅ |
| 過去類似主張照合 | Vertex AI text-embedding-005 + Firestore + cosine similarity（v0.3 実装済・Vertex AI Vector Search index は Phase 3 で移行） | ✅ |
| データ | Firestore（module cache） | ✅ |
| Observability | Cloud Logging + Monitoring | 🆕 |
| フロント | Chrome Extension（React+TypeScript・Manifest V3） | 🆕 |
| リアルタイム | Server-Sent Events | 🆕 |

## マルチエージェント構成（ハイブリッド入口）

```
入口① [Chrome Extension]            [Cloud Run (FastAPI)]
React + TypeScript                   ├ POST /api/analyze (URL/テキスト/DOM)
├ Manifest V3                       ├ POST /api/postmortem (警告履歴 Blameless 振り返り)
├ MutationObserver                  ├ POST /webhook/line ← LINE Bot
├ DOMオーバーレイ UI                 ├ GET  /api/articles/count
├ サイドパネル                       ├ GET  /health
└ Server-Sent Events 受信            │  ← 既存社内プロダクト 構造完全流用
                                     │
                                     [マルチエージェント (Vertex AI Gemini 2.5 Flash)]
入口② [LINE Bot @公式アカウント]      ├ Watcher Agent (記事抽出・URL/画像/テキスト)
URL/スクショ送信→分析結果返信       ├ Investigator Agent (複数ソース調査・矛盾検出)
✅ 既存社内プロダクト構造完全流用       └ Validator Agent (統合・結論・根拠提示)
QRで友達追加→誰でも使える           
                                     [Firestore]
[Firestore + Vertex AI Embedding] ←→ ├ 信頼ソース ホワイトリスト (Git管理)
├ 一次情報DB                          ├ 警告履歴 (Observability)
├ メディア×スポンサー関係            ├ ユーザー関心事
└ ジャーナリスト発言履歴             └ LINE userId×設定
                                     
[Cloud Logging/Monitoring]           
└ 「情報のObservability」基盤         
```

### なぜ2入口か
- **Chrome Extension**＝**「審査基準4 突き抜けた体験価値」直撃**（リアルタイム能動介入のピッチデモ）
- **LINE Bot**＝**既存社内プロダクト構造の完全流用で実装コスト最小**＋一般ユーザーの利用障壁ゼロ（友達追加だけ）＋社長日常使い
- 共通バックエンドで両方の入力に対応＝**新規開発を Chrome Extension に集中**できる

## ディレクトリ

```
deepfact-validator/
├── docs/                          # デモシナリオ・アーキテクチャ
├── src/                           # Cloud Run FastAPI バックエンド
│   ├── main.py
│   ├── config.py
│   ├── orchestrator.py
│   ├── agents/                    # Watcher / Investigator / Validator
│   └── tools/                     # vertex_vector_search / source_credibility 等
├── extension/                     # Chrome Extension (React+TS)
│   ├── manifest.json
│   ├── popup/
│   ├── content/
│   └── background/
├── tests/
├── scripts/                       # deploy.sh / seed
├── Dockerfile
├── cloudbuild.yaml
└── requirements.txt
```

## 法的リスク対策（[[feedback_brand_posture_premium]] Brand Soul①「品格」継承）

### 禁則表現
- ❌ 「このジャーナリストは○○から金もらってる」
- ❌ 「この記事は嘘」
- ❌ 発信者個人を断定的に指摘

### 推奨表現（構造分析）
- ✅ 「この記事の出所と過去発言には XX という構造的関係がある」
- ✅ 「一次情報と比較すると○○の点で論調が異なる」

## 補強プラン10日

| 日 | 作業 | 完了基準 |
|---|---|---|
| 1-2 | プロジェクト基盤・既存社内プロダクト流用骨格 | health endpoint動作 |
| 3-4 | マルチエージェント設計・3 agents実装 | ローカルで3軸分析動作 |
| 5-7 | Chrome Extension（React/TS）・DOM抽出・オーバーレイUI | 任意のニュースサイトで分析実行 |
| 8-9 | Vertex Vector Search + 一次情報DB seed・利害関係グラフ初期 | seed投入完了 |
| 10-14 | Cloud Logging Observability・警告履歴 | DevOpsフレーム完成 |
| 15-17 | デモシナリオ確定・「仕込みなしライブデモ」リハ | ピッチ動画録画可能 |
| 18-21 | ピッチHTML（hallmark経由）・最終調整・提出 | 7/10 提出完了 |

## ローカル実行

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
uvicorn src.main:app --reload --port 8080
```

## デプロイ

```bash
gcloud builds submit --config cloudbuild.yaml
```

## CI/CD パイプライン（信頼ソース辞書の Git 管理 → 自動 deploy）

[![validate-trust-sources](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml/badge.svg)](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml)

> 🔧 **deploy job の現状**: `main` push で validate ジョブが自動実行（all-green）。Cloud Build → Cloud Run の **deploy job は `workflow_dispatch` 限定**（GCP Workload Identity Federation の secrets 設定後に push trigger へ昇格予定）。実機 deploy は `gcloud builds submit` を `scripts/` 経由で実行している。

メティス指摘「DevOps接続を装飾でなく構造に」への直接回答。
**信頼ソース125ドメイン**と**煽動パターン143語**を Python dict 直書きから外し、
`config/*.yaml` を真実源として GitHub Actions で検証 → Cloud Build で auto-deploy するパイプラインに移行した。

```
config/trusted-domains.yaml  ─┐                                        ┌→ Cloud Build
config/propaganda-patterns.yaml ┤                                       │
                                ├→ PR open ─→ GitHub Actions ─→ validate┤
                                │            (yamllint + schema/range/  │
                                │             enum/duplicate/smoke load)│
                                └→ merge main ────────────────────────→ └→ Cloud Run
                                                                          (asia-northeast1)
```

| ステージ | 何をするか | ゲート |
|---|---|---|
| **PR open** | `.github/workflows/validate-trust-sources.yml` の `validate` job が起動 | yamllint / 必須キー / `credibility ∈ [0,1]` / category enum / domain unique / 起動時 YAML ロード smoke test |
| **merge main** | 同 workflow の `deploy` job が `gcloud builds submit --config cloudbuild.yaml` | Workload Identity Federation（service account key 不要） |
| **Cloud Build** | 既存 `cloudbuild.yaml` を変更せず再利用（Docker build → Artifact Registry push → Cloud Run deploy） | min-instances=1 で warmup 維持 |

### 検証ロジック

`scripts/validate-trust-sources.py` が下記をチェック（CI 内で実行・stderr に file:line 付きで報告）：

- 必須トップキー：`version` / `last_updated` / `categories` / `domains`（trusted）と `weights` / `patterns`（propaganda）
- credibility / weight が `[0.0, 1.0]`
- domain の重複なし
- 各 domain の category が `categories` enum に存在
- propaganda の `weights` キーと `patterns` キーが完全一致（カテゴリ drift 防止）
- 各 propaganda category が非空・term 重複検出

### 起動時 YAML ロード（agents 側）

`src/agents/investigator_agent.py` と `src/agents/watcher_agent.py` は import 時に YAML を読み、失敗時は同ファイル内の `_*_FALLBACK` dict に確実に落ちる（マイグレーション期間の安全網）。
ローカル smoke test：

```bash
python scripts/test-yaml-load.py
# => TRUSTED_DOMAINS: 125 entries
# => PROPAGANDA_PATTERNS: 5 categories, 143 terms
# => OK: dicts loaded.
```

### 必要な GitHub Secrets（deploy job のみ）

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`

PR の validate job はシークレット不要。Workflow は `paths:` filter を絞っているため、`config/` か `scripts/validate-trust-sources.py` を触った PR でしか起動しない。

## ライセンス

Liberaiz, Inc. プロプライエタリ（OSS ライセンス要件は Findy 提出フォーム入力時にハッカソン規約を最終確認・要件があれば Apache-2.0 切替予定）

## 監修

医師監修（医師・医学博士・産業医・元院長・Anthropic Certified 三冠）

## 関連 memory

- [[feedback_primary_source_mandatory]] ⭐⭐⭐ 本プロジェクトの北極星
- [[project_hackathon_deepfact_validator]] プロジェクトmemory
- [[feedback_brand_posture_premium]] Brand Soul（法的リスク対策の根拠）
- [[feedback_buy_remix_resell]] 既存社内プロダクト 流用は本原則の正統実践

## 哲学

本プロダクトは「発信者個人・組織への断定的指摘を避け、情報構造を可視化する」設計。
（[[feedback_brand_posture_premium]] Brand Soul①「品格」継承・DDA-Cの「人ではなく構造を見る」哲学を発展）

---

## 🆕 v0.2 実機検証結果（2026-06-19 23:35）

Gemini 2.5-flash 本実装後の入力差テスト4パターン：

| 入力 | 信頼度 | 出所 | 中立性 | 事実整合性 |
|------|--------|------|--------|-----------|
| フェイク主張（「証拠なくジェノサイド」） | **警告 20%** | 0.50 | 0.00 | 0.00 |
| 厚労省 一次情報URL | **高 96%** | 0.95 | 0.95 | 0.98 |
| 中立報道風（両論併記） | **中 50%** | 0.50 | 0.50 | 0.50 |
| 誇張広告（「3日でガン消失」） | **警告 20%** | 0.50 | 0.00 | 0.00 |

→ **96% vs 20% = 76ポイント振れ幅**。入力依存判定を機械検証で確認。

詳細：`test-results/summary-table.md` ／ ピッチ補足HTML：`pitch/demo-evidence-v0.2.html`

### 技術的修正履歴（v0.1 → v0.2）

- ⚠️ google-generativeai 0.8.3 → **google-genai 1.x**（新auth key AQ.Ab～ 対応・旧SDKは `Illegal header value` エラー）
- ⚠️ gemini-2.5-pro → **gemini-2.5-flash**（pro はタイムアウト多発で flash 採用）
- ⚠️ Phase 1 ヒューリスティック（入力非依存固定値）→ **Gemini 本実装**（入力依存判定）
- ⚠️ Cloud Run timeout 120s → **300s**（Gemini API レイテンシ余裕）
- ⚠️ footer ③ 削除（社長指摘・①と重複＋分かりにくい）

### Cloud Run エンドポイント

- 本番URL: `https://deepfact-validator-kjciocymea-an.a.run.app`
- 経路: LINE Bot (`/webhook/line`) / HTTP API (`/api/analyze`) / Chrome Extension（同 API）
- リビジョン: deepfact-validator-00005 以降（環境変数 GEMINI_MODEL=gemini-2.5-flash）

### ローカル開発（v0.2 対応）

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=AQ.Ab...  # Google AI Studio 新形式 auth key
export GEMINI_MODEL=gemini-2.5-flash
uvicorn src.main:app --reload --port 8080
```

### デプロイ

```bash
# <YOUR_GCP_PROJECT_ID> は意図的プレースホルダ — 実行者が自分のプロジェクトIDに置換
# （事前に `gcloud config set project <YOUR_GCP_PROJECT_ID>` 済みなら --project は省略可）
gcloud builds submit --config cloudbuild.yaml --project=<YOUR_GCP_PROJECT_ID>
```

---

## 🆕 v0.3 実機検証結果（2026-06-20 09:00）— Vertex AI 切替＋Firestore 同一入力一致保証

v0.2 朝の iPhone 実機テストで「同じ入力で 32% → 23% に変動」する非決定性問題が発覚。Cloud Run logs 解析で **Gemini API Free Tier 1日20リクエスト制限超過（429 RESOURCE_EXHAUSTED）** が真因と判明。**Vertex AI（GCP billing 経由）** に切替し、`temperature=0.0` + `seed=42` + `top_k=1` を3エージェント統一適用（公式仕様＝ベストエフォート）。**Firestore キャッシュ二層で同一入力一致を完全保証**（コンテストデモ事故ゼロ）。

### 🎯 達成項目

- **6パターンで信頼度差 78pt**（最高 98% vs 最低 20%／v0.2 の 76pt から拡大）
- **同一入力×3回で完全一致**（出力スコア・ラベル・全フィールド完全再現／コンテストデモ事故ゼロ）
- **Free Tier quota 制約解消**（Vertex AI billing 経由・本番運用に適格）

### 6パターン信頼度判定（v0.2 → v0.3 比較）

| # | 入力パターン | v0.2 overall | **v0.3 overall** | 差分 |
|---|---|---|---|---|
| 1 | フェイク主張（証拠なくジェノサイド） | 20% | **20%** | ✅ 完全再現 |
| 2 | 厚労省一次情報URL | 96% | **98%** | +2pt（Vertex AI で精度向上） |
| 3 | 中立報道風（医療制度・賛否両論） | 50% | **59%** | +9pt（中立評価が精緻化） |
| 4 | 誇張広告（3日でガン消失） | 20% | **20%** | ✅ 完全再現 |
| 5 | ワクチンフェイク（陰謀論型） | 26% | **25%** | -1pt（誤差範囲） |
| 6 | 学術的論調（系統的レビュー言及） | 59% | **59%** | ✅ 完全再現 |

→ **98% vs 20% = 78ポイント振れ幅**。入力依存判定と同一入力反復一致を両立。

### 技術スタック更新（v0.3）

- LLM: **Vertex AI Gemini 2.5-flash**（Cloud Run + GCP billing 経由・Free Tier 制約から解放）
- SDK: `google-genai 1.x` の `vertexai=True` モード
- 決定化: `temperature=0.0` + `seed=42` + `top_k=1` + `response_mime_type=application/json`
- 認証: Cloud Run サービスアカウント（プロジェクト内部 ID は伏字化）→ 最小権限 `roles/aiplatform.user` で aiplatform 利用（再付与計画中）
- インフラ: Cloud Run rev `deepfact-validator-00008` 以降 + asia-northeast1 + min=1/max=10
- Cloud Run env: `USE_VERTEX_AI=true`, `VERTEX_PROJECT=$PROJECT_ID`, `VERTEX_LOCATION=asia-northeast1`, `GEMINI_MODEL=gemini-2.5-flash`（cloudbuild.yaml の `$PROJECT_ID` 組み込み変数で実プロジェクトIDに展開）

### v0.2 → v0.3 修正履歴

- ⚠️ `temperature=0.1〜0.2` + seed なし → **`temperature=0.0` + `seed=42` + `top_k=1`**（3エージェント統一適用）
- ⚠️ Gemini API key（Free Tier 1日20req） → **Vertex AI（billing経由・本番運用適格）**
- ⚠️ `genai.Client(api_key=...)` → **`genai.Client(vertexai=True, project=..., location=...)`**

詳細: `test-results/v0.3/summary-table.md`
ピッチ補足HTML: `pitch/demo-evidence-v0.3.html`
ピッチ本体: `pitch/deepfact-validator-pitch-v0.3.html`

### Cloud Run エンドポイント（v0.3 稼働中）

- 本番URL: `https://deepfact-validator-kjciocymea-an.a.run.app`
- 経路: LINE Bot (`/webhook/line`) / HTTP API (`/api/analyze`) / Chrome Extension（同 API）
- リビジョン: deepfact-validator-00008 以降（環境変数 USE_VERTEX_AI=true）

---

## 🆕 v0.4 拡張機能（2026-06-22 朝の自走）

社長 LINE Bot 実機テストで「同じフェイク主張に対し信頼度が 32%→23%→50% と変動・フェイクを 50%（中）判定」事故が顕在化。同日朝の連続デプロイで完全修復＋エビデンス強化を達成。

### v0.4 で追加した機能

| # | 機能 | 実装 |
|---|---|---|
| 1 | **同一入力完全一致保証** | Firestore 入力ハッシュキャッシュ（`src/tools/response_cache.py`）。Vertex AI Gemini serving 側非決定性をユーザー視点で吸収・「同じ入力で違うスコア」事故ゼロ |
| 2 | **煽動パターン辞書 143 キーワード** | 5 カテゴリ × 計 **143 語**（high_alert 18 / evidence_lack 12 / urgency 18 / medical_fraud 53 / conspiracy 42）。Gemini 不要でフェイクをテキスト直接検出（`watcher_agent.py` `PROPAGANDA_PATTERNS`） |
| 3 | **Investigator fallback 強化** | Gemini 失敗時に emotional_intensity ベースで position_bias / fact_consistency を安全側に推定（フェイクを「中 50%」に倒さない） |
| 4 | **信頼ドメイン辞書 39 → 125 件** | IFCN 加盟ファクトチェック団体 / 医療系（CDC/FDA/EMA/PMDA/NIH） / 国際機関（UNICEF/UNHCR/OECD等） / 学術 DB（arXiv/JSTOR/Cochrane等） / 各国政府 / プロパガンダ判定追加 |
| 5 | **第三者ソース能動取得 + URL 付き表示** | Google Fact Check Tools API + Wikipedia REST API を並列叩き、判定エビデンスを EvidenceSource 構造で取得（`src/tools/fact_check.py`） |
| 6 | **LINE Bot 判定エビデンス表示** | レスポンスに「📚【判定エビデンス・ソース】」セクション追加・publisher / rating / title / URL を明示 |

### Cloud Run env vars（v0.4 追加）

- `GOOGLE_FACT_CHECK_API_KEY`（Secret: DEEPFACT_GOOGLE_FACT_CHECK_API_KEY・オプション・未設定でも Wikipedia は動作）

### v0.4 実機検証結果

```
RUN: POST /api/analyze with COVID マイクロチップフェイク主張
→ overall 0.20 / 警告 ✅
→ evidence_sources 3 件:
  - Wikipedia「COVID-19ワクチン」
  - Wikipedia「日本におけるCOVID-19ワクチンの接種」
  - Wikipedia「ワクチン忌避」← 「ビル・ゲイツがマイクロチップを入れている」陰謀論を名指し反証

社長 LINE 実機テスト: ジェノサイドフェイク → 低 31% + 📚 判定エビデンス 3 件表示確認済み
社長フィードバック: 「ソースついて一層良くなった」（2026-06-22 朝）
```

### v0.4 アーキテクチャ追加層

```
[Watcher Agent]
  ├ Vertex AI Gemini で構造抽出
  └ PROPAGANDA_PATTERNS 直接検出（fallback 強化）
        ↓
[Investigator Agent]
  ├ TRUSTED_DOMAINS 125 ドメイン照合
  ├ Vertex AI Gemini で論調バイアス・事実整合性判定
  └ 🆕 gather_evidence() で第三者ソース能動取得
        ├ Google Fact Check Tools API（IFCN 加盟団体）
        └ Wikipedia REST API（無料・登録不要・並列）
        ↓
[Validator Agent] → 統合 → evidence_sources を構造化レスポンスに同梱
        ↓
[Firestore Response Cache] ← 同一入力完全一致保証
        ↓
[LINE Bot / Chrome Extension / HTTP API] ← 📚 判定エビデンス URL を表示
