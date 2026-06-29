#!/usr/bin/env bash
# DeepFact Validator — Cloud Logging / Monitoring デプロイスクリプト.
#
# やること:
#   1. config/log-based-metrics.yaml から各メトリクスを `gcloud logging metrics create`
#   2. config/alert-policies.yaml から各ポリシーを `gcloud alpha monitoring policies create`
#   3. 冪等: 既存ならスキップ (describe で存在確認 → 無ければ create)
#
# 前提:
#   - gcloud CLI 認証済み (gcloud auth application-default login)
#   - python3 + PyYAML 利用可 (set -e のため事前にチェック)
#   - 環境変数 GCP_PROJECT を必須 / NOTIFICATION_CHANNEL は任意
#
# 使い方:
#   GCP_PROJECT=my-project ./scripts/deploy-monitoring.sh
#   GCP_PROJECT=my-project NOTIFICATION_CHANNEL=projects/.../notificationChannels/xxx \
#       ./scripts/deploy-monitoring.sh
#
# 動作確認 (dry-run):
#   DRY_RUN=1 GCP_PROJECT=my-project ./scripts/deploy-monitoring.sh

set -euo pipefail

# ===========================================================
# 前提チェック
# ===========================================================

: "${GCP_PROJECT:?GCP_PROJECT env is required (e.g. GCP_PROJECT=my-project)}"
DRY_RUN="${DRY_RUN:-0}"
NOTIFICATION_CHANNEL="${NOTIFICATION_CHANNEL:-}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "[FATAL] gcloud CLI not found" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "[FATAL] python3 not found (required for YAML parse)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
METRICS_YAML="${ROOT_DIR}/config/log-based-metrics.yaml"
ALERTS_YAML="${ROOT_DIR}/config/alert-policies.yaml"

if [[ ! -f "${METRICS_YAML}" ]]; then
  echo "[FATAL] ${METRICS_YAML} not found" >&2
  exit 1
fi
if [[ ! -f "${ALERTS_YAML}" ]]; then
  echo "[FATAL] ${ALERTS_YAML} not found" >&2
  exit 1
fi

echo "[INFO] GCP_PROJECT=${GCP_PROJECT} DRY_RUN=${DRY_RUN}"

# ===========================================================
# Helper: 既存メトリクスの存在チェック (冪等性)
# ===========================================================

metric_exists() {
  local name="$1"
  gcloud logging metrics describe "${name}" \
    --project="${GCP_PROJECT}" >/dev/null 2>&1
}

policy_exists() {
  local display_name="$1"
  gcloud alpha monitoring policies list \
    --project="${GCP_PROJECT}" \
    --filter="displayName=\"${display_name}\"" \
    --format="value(name)" 2>/dev/null | grep -q '^projects/'
}

# ===========================================================
# 1. ログベースメトリクス登録
# ===========================================================
# YAML を parse して 1 メトリクスずつ JSON 化 → gcloud に流し込む。
# gcloud は `--config-from-file=` 形式で JSON/YAML どちらでも受けるが、
# 1 ファイル 1 メトリクスを要求するため一時 JSON ファイル経由で処理する。

echo ""
echo "============================================================"
echo "[STEP 1] Deploying log-based metrics"
echo "============================================================"

METRIC_NAMES=$(python3 - <<PY
import yaml, sys
with open("${METRICS_YAML}") as f:
    data = yaml.safe_load(f)
for m in data.get("metrics", []):
    print(m["name"])
PY
)

for name in ${METRIC_NAMES}; do
  if metric_exists "${name}"; then
    echo "[SKIP]   metric already exists: ${name}"
    continue
  fi
  TMP_JSON="$(mktemp -t deepfact_metric_XXXX.json)"
  python3 - <<PY > "${TMP_JSON}"
import json, yaml
with open("${METRICS_YAML}") as f:
    data = yaml.safe_load(f)
target = next(m for m in data["metrics"] if m["name"] == "${name}")
# gcloud schema: filter / description / metricDescriptor / valueExtractor / bucketOptions
out = {
    "name": target["name"],
    "filter": target["filter"].strip(),
    "description": target.get("description", "").strip(),
}
md = {}
if "value_type" in target:
    md["valueType"] = target["value_type"]
if "metric_kind" in target:
    md["metricKind"] = target["metric_kind"]
if "unit" in target:
    md["unit"] = target["unit"]
if "labels" in target:
    md["labels"] = [
        {"key": lb["key"], "valueType": lb.get("value_type", "STRING"),
         "description": lb.get("description", "")}
        for lb in target["labels"]
    ]
if md:
    out["metricDescriptor"] = md
if "value_extractor" in target:
    out["valueExtractor"] = target["value_extractor"]
if "bucket_options" in target:
    bo = target["bucket_options"]
    if "exponential_buckets" in bo:
        eb = bo["exponential_buckets"]
        out["bucketOptions"] = {
            "exponentialBuckets": {
                "numFiniteBuckets": eb["num_finite_buckets"],
                "growthFactor": eb["growth_factor"],
                "scale": eb["scale"],
            }
        }
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
  echo "[CREATE] ${name}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "         (dry-run) payload:"
    cat "${TMP_JSON}" | sed 's/^/           /'
  else
    gcloud logging metrics create "${name}" \
      --config-from-file="${TMP_JSON}" \
      --project="${GCP_PROJECT}"
  fi
  rm -f "${TMP_JSON}"
done

# ===========================================================
# 2. アラートポリシー登録
# ===========================================================

echo ""
echo "============================================================"
echo "[STEP 2] Deploying alert policies"
echo "============================================================"

POLICY_NAMES=$(python3 - <<PY
import yaml
with open("${ALERTS_YAML}") as f:
    data = yaml.safe_load(f)
for p in data.get("policies", []):
    print(p["display_name"])
PY
)

for display_name in ${POLICY_NAMES}; do
  if policy_exists "${display_name}"; then
    echo "[SKIP]   policy already exists: ${display_name}"
    continue
  fi
  TMP_JSON="$(mktemp -t deepfact_policy_XXXX.json)"
  python3 - <<PY > "${TMP_JSON}"
import json, os, yaml
with open("${ALERTS_YAML}") as f:
    data = yaml.safe_load(f)
target = next(p for p in data["policies"] if p["display_name"] == "${display_name}")
notif = "${NOTIFICATION_CHANNEL}"
# Cloud Monitoring AlertPolicy JSON schema
out = {
    "displayName": target["display_name"],
    "combiner": target.get("combiner", "OR"),
    "enabled": target.get("enabled", True),
    "documentation": {
        "content": target["documentation"]["content"],
        "mimeType": target["documentation"]["mime_type"],
    },
    "conditions": [],
}
for cond in target["conditions"]:
    ct = cond["condition_threshold"]
    body = {
        "displayName": cond["display_name"],
        "conditionThreshold": {
            "comparison": ct["comparison"],
            "thresholdValue": ct["threshold_value"],
            "duration": ct["duration"],
            "aggregations": [
                {
                    "alignmentPeriod": agg["alignment_period"],
                    "perSeriesAligner": agg["per_series_aligner"],
                }
                for agg in ct.get("aggregations", [])
            ],
        },
    }
    if "filter" in ct:
        body["conditionThreshold"]["filter"] = ct["filter"]
    if "numerator_filter" in ct:
        # Ratio alert は MQL/PromQL も選択肢. ここは filter ベースで近似.
        body["conditionThreshold"]["filter"] = ct["numerator_filter"]
        body["conditionThreshold"]["denominatorFilter"] = ct["denominator_filter"]
    out["conditions"].append(body)
if notif:
    out["notificationChannels"] = [notif]
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
  echo "[CREATE] policy: ${display_name}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "         (dry-run) payload:"
    cat "${TMP_JSON}" | sed 's/^/           /'
  else
    gcloud alpha monitoring policies create \
      --policy-from-file="${TMP_JSON}" \
      --project="${GCP_PROJECT}"
  fi
  rm -f "${TMP_JSON}"
done

echo ""
echo "============================================================"
echo "[DONE] Cloud Logging / Monitoring deployment complete."
echo "       Open: https://console.cloud.google.com/logs/metrics?project=${GCP_PROJECT}"
echo "       Open: https://console.cloud.google.com/monitoring/alerting/policies?project=${GCP_PROJECT}"
echo "============================================================"
