# DeepFact Validator — Observability 仕様書

メティス指摘「装飾でなく構造」への直接対応として、信頼度スコアを **Cloud Logging（構造化ログ）→ Cloud Monitoring（ログベースメトリクス）→ アラート** という SRE 標準の流れに乗せている。Logs Explorer / Metrics Explorer / Alerting の画面がそのまま「動くスクショ」になる。

---

## 1. 構造化ログのフィールド仕様

### 1.1 共通フィールド (全イベント)

| フィールド | 型 | 例 | 説明 |
| --- | --- | --- | --- |
| `severity` | string | `INFO` / `WARNING` / `ERROR` | Cloud Logging LogSeverity 標準 |
| `message` | string | `analyze_request` | 人間向け 1 行サマリ |
| `timestamp` | string (ISO 8601 UTC) | `2026-06-29T08:42:01.123456+00:00` | イベント発生時刻 |
| `service` | string | `deepfact-validator` | サービス名 (固定) |
| `version` | string | `1.1.4` | アプリバージョン |
| `event` | string | `analyze_request` 他 | イベント種別 (絞り込みキー) |
| `request_id` | string (UUID) | `b1f6...` | 1 リクエスト内の処理を時系列で繋ぐ |

### 1.2 イベント別の固有フィールド

#### `analyze_request`
`/api/analyze` のリクエスト受領時に出力。

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `input_type` | string | `url` / `text` / `dom` |
| `payload_length` | int | リクエスト本文の文字数 |
| `has_user_context` | bool | `user_context` を含むか |

#### `watcher_result`
Watcher エージェントが本文 / 元配信元抽出を終えた時。
**`unknown_rate` メトリクスの土台。**

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `extraction_success` | bool | 元配信元抽出に成功したか |
| `extraction_method` | string | `direct` / `relay_html` / `relay_dict` / `none` |
| `original_publisher` | string | 朝日新聞 / 共同通信 / 空 |
| `source_domain` | string | `asahi.com` 等 |
| `elapsed_ms` | int | Watcher 単体の処理時間 |
| `input_type` | string | url / text / dom |

#### `investigator_result`
Investigator エージェントが信頼度 / カテゴリを返した時。

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `source_credibility` | float (0-1) | 発信元信頼度 (`source_credibility_score`) |
| `position_bias` | float (0-1) | 中立性 (`position_bias_score`) |
| `fact_consistency` | float (0-1) | 事実整合性 (`fact_consistency_score`) |
| `source_label` | string | 朝日新聞 / 共同通信 / `未登録` 等 |
| `elapsed_ms` | int | Investigator 単体の処理時間 |

#### `validator_result`
Validator エージェントが最終スコアを確定した時。
**`low_credibility_rate` / `pipeline_latency_ms` メトリクスの土台。**

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `overall_score` | float (0-1) | 総合信頼度 |
| `overall_label` | string | `高` / `中` / `低` / `警告` |
| `source_credibility` | float | 出所 |
| `position_bias` | float | 中立性 |
| `fact_consistency` | float | 事実整合性 |
| `elapsed_ms` | int | パイプライン全体の処理時間 |
| `input_type` | string | url / text / dom |

#### `cache_hit` / `cache_miss`
Firestore 入力ハッシュキャッシュ参照時。**`cache_hit_rate` メトリクスの土台。**

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `input_type` | string | url / text / dom |

#### `error`
例外発生時。`severity=ERROR`、スタックトレース付き。**`error_rate` メトリクスの土台。**

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `stage` | string | `cache_lookup` / `record_warning` / `save_article` / `save_cached_response` |
| `exception` | string | スタックトレース全文 |

---

## 2. メトリクス定義一覧

`config/log-based-metrics.yaml` で管理。`scripts/deploy-monitoring.sh` でデプロイ。

| メトリクス名 | 型 | 説明 | フィルタ条件 |
| --- | --- | --- | --- |
| `deepfact_unknown_rate` | DELTA / INT64 | 元配信元抽出失敗件数 | `event=watcher_result extraction_success=false` |
| `deepfact_watcher_result_count` | DELTA / INT64 | watcher 総数 (上記の分母) | `event=watcher_result` |
| `deepfact_low_credibility_rate` | DELTA / INT64 | 信頼度低 (<0.5) 件数 | `event=validator_result overall_score<0.5` |
| `deepfact_cache_hit_count` | DELTA / INT64 | キャッシュ HIT 件数 | `event=cache_hit` |
| `deepfact_cache_miss_count` | DELTA / INT64 | キャッシュ MISS 件数 | `event=cache_miss` |
| `deepfact_pipeline_latency_ms` | DELTA / DISTRIBUTION | パイプライン経過時間 | `event=validator_result` (`elapsed_ms` 抽出) |
| `deepfact_error_count` | DELTA / INT64 | ERROR severity 件数 | `severity=ERROR` |
| `deepfact_analyze_request_count` | DELTA / INT64 | リクエスト総数 (分母) | `event=analyze_request` |

### 2.1 「率」の計算方法

Cloud Monitoring 側のチャート / アラートで以下の式を組む:

- **unknown_rate**: `deepfact_unknown_rate` / `deepfact_watcher_result_count`
- **cache_hit_rate**: `deepfact_cache_hit_count` / (`deepfact_cache_hit_count` + `deepfact_cache_miss_count`)
- **error_rate**: `deepfact_error_count` / `deepfact_analyze_request_count`
- **p95_latency**: `deepfact_pipeline_latency_ms` の `ALIGN_PERCENTILE_95`

---

## 3. アラートポリシー一覧

`config/alert-policies.yaml` で管理。

| ポリシー名 | severity | 条件 | 持続 |
| --- | --- | --- | --- |
| `deepfact-unknown-rate-high` | WARNING | unknown_rate > 30% | 5 分 |
| `deepfact-error-rate-high` | ERROR | error_rate > 5% | 1 分 |
| `deepfact-p95-latency-high` | WARNING | p95 latency > 10s | 5 分 |
| `deepfact-low-credibility-spike` | INFO | low_credibility_rate > 60% | 10 分 |

通知チャネルは `NOTIFICATION_CHANNEL` 環境変数で渡す (Slack / Email など)。

---

## 4. Cloud Console での確認手順 (スクショ撮影手順)

### 4.1 Logs Explorer (構造化ログを見る)

1. Cloud Console → **Logging → Logs Explorer**
2. クエリ欄に下記を貼る。
3. 直近 1 時間に絞り → トラフィックを軽く流す (`curl https://<service-url>/api/analyze` 等)。
4. 各 JSON ログを開くと `jsonPayload.event` / `jsonPayload.request_id` / `jsonPayload.overall_score` が見える → **スクショ①**

**全イベントを時系列で見る**
```
resource.type="cloud_run_revision"
resource.labels.service_name="deepfact-validator"
jsonPayload.event=~".+"
```

**特定リクエストの一連を追う (request_id 絞り込み)**
```
resource.type="cloud_run_revision"
resource.labels.service_name="deepfact-validator"
jsonPayload.request_id="b1f6xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**信頼度低だけ拾う**
```
resource.type="cloud_run_revision"
resource.labels.service_name="deepfact-validator"
jsonPayload.event="validator_result"
jsonPayload.overall_score<0.5
```

**元配信元抽出失敗だけ拾う**
```
resource.type="cloud_run_revision"
resource.labels.service_name="deepfact-validator"
jsonPayload.event="watcher_result"
jsonPayload.extraction_success=false
```

### 4.2 Logs-based Metrics (メトリクス一覧)

1. Cloud Console → **Logging → Logs-based Metrics**
2. User-defined セクションに `deepfact_*` が並んでいることを確認 → **スクショ②**

### 4.3 Metrics Explorer (チャート化)

1. Cloud Console → **Monitoring → Metrics Explorer**
2. Metric 検索欄に `deepfact_pipeline_latency_ms` を入力。
3. Aggregator を `95th percentile` に設定 → P95 グラフ表示 → **スクショ③**
4. 同様に `deepfact_unknown_rate` / `deepfact_low_credibility_rate` をチャート化 → **スクショ④⑤**

### 4.4 Alerting (アラートポリシー)

1. Cloud Console → **Monitoring → Alerting → Policies**
2. `deepfact-*` ポリシーが一覧表示 → **スクショ⑥**
3. 各ポリシーを開き、Documentation / Conditions が表示されることを確認 → **スクショ⑦**

### 4.5 ローカル確認

```bash
# JSON 1 行で stdout に出ることを確認
python -c "
from src.observability import log_event, EVENT_ANALYZE_REQUEST
log_event(EVENT_ANALYZE_REQUEST, input_type='url', payload_length=42, has_user_context=False)
"
```

---

## 5. デプロイ手順

### 5.1 ログベースメトリクス + アラート登録

```bash
# 1. 通知チャネル (Email) を事前に作成しておく
gcloud alpha monitoring channels create \
  --display-name="DeepFact alerts" \
  --type=email \
  --channel-labels=email_address=liberaiz.ceo@gmail.com

# 2. 上記の作成結果 (projects/.../notificationChannels/xxx) を環境変数に入れて deploy
export GCP_PROJECT=deepfact-prod
export NOTIFICATION_CHANNEL=projects/deepfact-prod/notificationChannels/123456789
./scripts/deploy-monitoring.sh

# 3. (任意) dry-run でペイロードを目視確認
DRY_RUN=1 GCP_PROJECT=deepfact-prod ./scripts/deploy-monitoring.sh
```

### 5.2 デプロイ後の検証

```bash
# 登録済みメトリクス一覧
gcloud logging metrics list --project=$GCP_PROJECT --filter="name:deepfact_"

# 登録済みポリシー一覧
gcloud alpha monitoring policies list --project=$GCP_PROJECT --filter="displayName:deepfact-"
```

---

## 6. 設計上の注意点

- **構造化ログは `src/observability.py` の `log_event()` だけを通す**: 自由文字列 `logger.info("foo %s", x)` は jsonPayload に展開されず、メトリクス化できない。
- **既存 `src/tools/observability.py` は責任分離**: あちらは Firestore 永続化 + Postmortem 生成専用。本ファイルは Cloud Logging 構造化送出専用。
- **request_id は ContextVar 伝搬**: FastAPI 非同期環境でも 1 リクエストの全イベントを `jsonPayload.request_id` で一発検索できる。
- **メトリクス比率は Monitoring 側で算出**: Cloud Logging は単一イベントの集計しかできないため、分子/分母を別メトリクスとして登録し、Cloud Monitoring の Ratio 計算で比率化する。
