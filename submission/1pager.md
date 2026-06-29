# DeepFact Validator — 1 Pager（審査員向け 1 枚要約）

## プロダクト名

**DeepFact Validator** ─ 情報の Observability を社会に実装するマルチエージェント

- 🚀 Live: https://deepfact-validator-kjciocymea-an.a.run.app
- 📦 GitHub: https://github.com/liberaiz/deepfact-validator
- 🔄 CI/CD: [![validate-trust-sources](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml/badge.svg)](https://github.com/liberaiz/deepfact-validator/actions/workflows/validate-trust-sources.yml)

## 1行概要

**ユーザーがネットを見ている瞬間に、AIエージェントが情報の信頼度と利害関係をリアルタイム可視化する** ＝医師である創業者の「真偽判断は一次情報まで追う」習慣を、マルチエージェント AI で社会全体に拡張する。

## なぜ作るか（背景）

医師である創業者 Dr. 加藤（医師・医学博士・産業医・元院長・Anthropic Certified 三冠）は、診療判断の北極星として **「真偽判断は一次情報まで遡る」** を実践している。誤情報・誇張広告・陰謀論型フェイクが医療領域に流入する現状で、この医師の習慣を AI Agent で社会全体に拡張する＝**情報の Observability** を実装する。

## DevOps 文脈への接続

| DevOps 文脈 | 本プロダクトの実装 |
|---|---|
| **Observability** | Cloud Logging / Monitoring で「ユーザーが見た情報履歴」を SRE 的に蓄積・可視化・アラート |
| **CI/CD** | 信頼ソースホワイトリストを Git 管理・差分監視・ベクトル DB 自動再 deploy |
| **SRE** | 「真実の SRE エージェント」コンセプト・情報の障害（誤情報）を予兆検知 |
| **Postmortem** | 誤情報に騙された後の「警告履歴」を Postmortem 形式で記録・再発防止 |

## マルチエージェント構成

```
入力 (URL / テキスト / LINE / Chrome Extension)
       ↓
[Watcher Agent]      記事抽出・主張抽出・感情強度・出典 URL
       ↓
[Investigator Agent] 発信元辞書 × Vertex AI Gemini で論調バイアス／事実整合性／対立見解
       ↓
[Validator Agent]    数値統合 + 自然言語の構造観察レポート生成
       ↓
出力 (信頼度スコア + 構造観察 + 免責文)
```

全エージェント：**Vertex AI Gemini 2.5-flash** × **temperature=0.0 + seed=42 + top_k=1**（ベストエフォート）+ **Firestore キャッシュ二層により同一入力の出力を再現保証**（キャッシュ HIT 時は完全一致・コンテストデモ事故ゼロ）。

## 実機検証結果（v0.3・2026-06-20 09:00 確定）

| # | 入力パターン | 信頼度 | ラベル |
|---|---|---:|---|
| 1 | フェイク主張（証拠なくジェノサイド） | **20%** | 警告 |
| 2 | 厚労省一次情報 URL | **98%** | 高 |
| 3 | 中立報道風（賛否両論） | **59%** | 中 |
| 4 | 誇張広告（3日でガン消失） | **20%** | 警告 |
| 5 | ワクチンフェイク（陰謀論型） | **25%** | 警告 |
| 6 | 学術的論調（系統的レビュー言及） | **59%** | 中 |

→ **98% vs 20% = 78 ポイント振れ幅**（入力依存性 完全確認）
→ **同一入力×3回で完全一致**（コンテストデモ事故ゼロ・決定化検証 PASS）

## 既存サービスとの差別化

| 既存 | 何ができる | DeepFact Validator | 差分 |
|---|---|---|---|
| NewsGuard | 信頼度スコア（人手評価） | + AI Agent 能動介入 | 静的→動的 |
| Ground News | 複数視点並列表示 | + 利害関係グラフ可視化 | 並べる→関係性で診る |
| AllSides | 左右ラベル | + ユーザー文脈パーソナライズ | 一律→個別 |
| ChatGPT / Gemini | 質問→回答 | + 質問前に能動介入 | 受動→能動 |

## 技術スタック

| 役割 | 技術 |
|---|---|
| LLM | **Vertex AI Gemini 2.5-flash**（GCP billing 経由・Free Tier 制約解消・各 call 30s timeout） |
| SDK | `google-genai 1.x` の `vertexai=True` モード |
| 実行基盤 | Cloud Run（min-instances=1 + warmup）・asia-northeast1 |
| API | FastAPI（Python 3.12）+ CORS Middleware |
| **第三者ソース照合（v0.4）** | **Google Fact Check Tools API**（IFCN 加盟ファクトチェック団体・ja+en 並列叩き）+ **Wikipedia REST API**（無料・登録不要・ja+en 並列）+ **15s 全体 timeout** |
| **公的機関ソース 上位常時挿入（v0.4）** | PROPAGANDA 検出時、厚労省 / PMDA / WHO / CDC / 総務省 / JFC / Snopes / PolitiFact / FullFact / Reuters Fact Check / AFP Fact Check の **直接 URL** を上位表示・「Wikipedia オンリー」構造を完全排除 |
| **信頼ドメイン辞書** | **125 ドメイン**（医療/政府/学術/国際機関/ファクトチェック団体/プロパガンダ判定込み） |
| **煽動パターン辞書（v0.4）** | 5 カテゴリ × **143 キーワード**（high_alert / evidence_lack / urgency / medical_fraud / conspiracy）Gemini 不要 fallback。マイクロチップ/5G/ナノマシン/思想統制/極秘計画/ビッグファーマ/ビル・ゲイツ 等の陰謀論用語網羅 |
| **Wikipedia noise filter（v0.4）** | アニメ・ゲーム・芸能等 **47 キーワード**で TF-IDF 誤ヒット記事を自動除外（`fact_check.py` `WIKIPEDIA_NOISE_KEYWORDS`） |
| **同一入力決定化（v0.4）** | Firestore 入力ハッシュキャッシュ・コンテストデモ事故ゼロ |
| **LINE Bot 永続 event loop（v0.4）** | `asyncio.run()` を毎回呼ばず `run_coroutine_threadsafe` で schedule・接続プール持続化で cold start 時の Vertex AI 接続不安定を抑制 |
| Vector Search | Vertex AI text-embedding-005 + Firestore + cosine similarity による過去類似主張照合（v0.3 実装済・index 化は Phase 5） |
| データ | Firestore（信頼ソース辞書・警告履歴・response cache・記事 embedding） |
| Observability | Cloud Logging + Monitoring + Postmortem 自動生成 |
| フロント | LINE Bot（実装済・稼働中・**🚨/⚠️/〽️/✅ 信頼度アイコン + 📚 判定エビデンス URL 付き表示**・即時「⌛分析中」reply → push_message で結果送信）/ Chrome Extension（Manifest V3・Phase 2 実装済） |

## 法的リスク対策（Brand Soul「品格」継承）

- 「人を攻撃しない・構造を可視化する」原則を全レポートに常設
- 個人・組織への断定攻撃を禁則（「○○という構造」「○○の傾向」形式のみ）
- 政治的・宗教的に微妙な主張は「複数の立場が成り立つ構造」を contrarian_views で提示

## デプロイ済 URL

**`https://deepfact-validator-kjciocymea-an.a.run.app`** ─ Cloud Run 稼働中（`GET /health` で HTTP 200 確認済・rev 00008 以降）

## チーム

**株式会社 Liberaiz**（代表取締役 Dr. 加藤）
─ 医師・医学博士・産業医・元院長 ×
   Anthropic Certified 三冠（Claude 101 / AI Fluency / Cowork）
─ 「医師の習慣を AI Agent で社会全体に拡張する」をコアコンセプトに 1人法人で運営

## 哲学

> 個人・組織への断定攻撃を避け、情報構造を可視化する設計。

---

## 🎯 審査基準 5項目への対応度（DevOps × AI Agent Hackathon 2026）

| # | 審査基準 | DeepFact の対応 |
|---|---|---|
| 1 | **AIエージェントが価値の中心**（自律的振る舞い・必然性） | Watcher → Investigator → Validator の 3 エージェント自律連携 + **公的機関・FC団体 URL の能動取得**（厚労省/PMDA/WHO/CDC/JFC/Snopes/Reuters Fact Check 等）。素の Gemini で代替不可な 5 基準を充足 |
| 2 | **課題アプローチ力**（ストーリー一貫性・妥当性・新規性） | 医師の「真偽は一次情報まで辿る」北極星から AI Agent 設計まで一貫。既存サービスとの明確な差別化（静的→動的・並べる→関係性・受動→能動） |
| 3 | **ユーザビリティ** | LINE Bot（友達追加だけ・**🚨/⚠️/〽️/✅ 信頼度アイコン + 📚 判定エビデンス URL 付き返信**）+ Chrome Extension + HTTP API の 3 経路 |
| 4 | **実用性・体験価値**（突き抜けたら加点） | 6 パターン信頼度差 78pt + 同一入力完全一致（Firestore キャッシュ）+ **公的機関/FC団体 URL の自動取得・LINE 上位表示**（厚労省・PMDA・WHO・CDC 等） + リアルタイム能動介入 |
| 5 | **実装力** | Vertex AI 切替で本番運用適格 + **Firestore キャッシュで同一入力一致保証**（`temperature=0+seed=42+top_k=1` はベストエフォート + Gemini 各 call 30s timeout）+ **Wikipedia/Fact Check ja+en 並列叩き + 公的機関ソース常時上位挿入 + Wikipedia noise filter** + Cloud Logging Observability + SRE 流 Postmortem + **125 ドメイン信頼辞書 + 143 煽動キーワード辞書 + 永続 event loop 接続持続化** |
