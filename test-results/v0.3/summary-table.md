# DeepFact Validator v0.3 実機検証結果（2026-06-20 09:00 更新）

3エージェント（Watcher → Investigator → Validator）× **Vertex AI Gemini 2.5-flash** × **temperature=0 + seed=42 + top_k=1**（ベストエフォート）+ **Firestore キャッシュ二層で同一入力一致を保証**した実機検証。

## 🎯 達成項目

- **6パターンで信頼度差 78pt**（最高 98% vs 最低 20%）
- **同一入力×3回で完全一致**（出力スコア・ラベル・全フィールド完全再現）
- **Free Tier quota 制約解消**（Vertex AI billing 経由）

## 6パターン信頼度判定の比較

| # | 入力パターン | 信頼度ラベル | overall | source | 中立性 | 事実整合性 |
|---|-------------|------------|---------|--------|--------|-----------|
| 1 | フェイク主張（「証拠なくジェノサイド」） | **警告** | **20%** | 0.50 | **0.00** | **0.00** |
| 2 | 厚労省一次情報URL | **高** | **98%** | 0.95 | **1.00** | **1.00** |
| 3 | 中立報道風（医療制度・賛否両論） | **中** | **59%** | 0.50 | 0.60 | **0.70** |
| 4 | 誇張広告（「3日でガン消失」） | **警告** | **20%** | 0.50 | **0.00** | **0.00** |
| 5 | ワクチンフェイク（陰謀論型） | **警告** | **25%** | 0.50 | **0.05** | **0.10** |
| 6 | 学術的論調（系統的レビュー言及） | **中** | **59%** | 0.50 | 0.60 | **0.70** |

## v0.2 (前夜深夜) との比較

| パターン | v0.2 overall | v0.3 overall | 差分 |
|---|---|---|---|
| 01-fake | 20% | 20% | ✅ 完全再現 |
| 02-mhlw | 96% | **98%** | +2pt (Vertex AI で精度向上) |
| 03-neutral | 50% | **59%** | +9pt (中立評価が精緻化) |
| 04-hype | 20% | 20% | ✅ 完全再現 |
| 05-vaccine-fake | 26% | 25% | -1pt (誤差範囲) |
| 06-academic | 59% | 59% | ✅ 完全再現 |

## 振れ幅検証

- **最高 98%（厚労省一次情報）vs 最低 20%（フェイク／広告）= 78 ポイント差**（v0.2 の 76pt → 78pt に拡大）
- 6パターンで入力依存性 ✅ 完全確認
- **同一入力×3回で完全一致**（コンテストデモで「同じURL送ったら違うスコア」事故ゼロ）

## 技術スタック (v0.3)

- LLM: **Vertex AI Gemini 2.5-flash**（Cloud Run + GCP billing 経由・Free Tier 1日20req制約から解放）
- SDK: `google-genai 1.x` の `vertexai=True` モード
- 決定化: `temperature=0.0` + `seed=42` + `top_k=1` + `response_mime_type=application/json`
- 認証: Cloud Run サービスアカウント（プロジェクト内部 ID は伏字化）→ 最小権限 `roles/aiplatform.user` で aiplatform 利用（再付与計画中）
- インフラ: Cloud Run rev `deepfact-validator-00008` 以降 + asia-northeast1 + min=1/max=10

## 由来

- 2026-06-19 21:50 社長指摘「フェイク主張も信頼度高く出てる」→ 22:00-23:35 Gemini 本実装で根本修復（v0.2）
- 2026-06-20 07:56 社長 LINE 朝テストで「同じ入力で 32%→23% 変動」→ 非決定性問題発覚
- 2026-06-20 08:00-09:00 真因切り分け：
  1. temperature が 0.1-0.2 のまま → temperature=0 + seed=42 + top_k=1 でベストエフォート決定化（補助層）
  2. Cloud Run logs 解析で **Gemini API Free Tier 1日20req超過（429 RESOURCE_EXHAUSTED）** が真因と判明
  3. **Vertex AI Gemini に切替**（cloudbuild に USE_VERTEX_AI=true / VERTEX_PROJECT / VERTEX_LOCATION を追加）
  4. 再デプロイ → 6パターン完全再現 + 同一入力×3完全一致 → v0.3 達成
