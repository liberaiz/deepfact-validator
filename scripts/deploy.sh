#!/usr/bin/env bash
# DeepFact Validator Cloud Run デプロイスクリプト
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-deepfact-validator}"
REGION="${REGION:-asia-northeast1}"
SERVICE_NAME="${SERVICE_NAME:-deepfact-validator}"
REPO_NAME="${REPO_NAME:-deepfact-validator}"

echo "================================================"
echo " DeepFact Validator Cloud Run デプロイ"
echo "================================================"
echo "  PROJECT_ID: ${PROJECT_ID}"
echo "  REGION:     ${REGION}"
echo "  SERVICE:    ${SERVICE_NAME}"
echo "================================================"

gcloud config set project "${PROJECT_ID}"

echo "[1/4] Enable APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

echo "[2/4] Artifact Registry repo..."
gcloud artifacts repositories describe "${REPO_NAME}" \
  --location="${REGION}" 2>/dev/null || \
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="DeepFact Validator container repo"

echo "[3/4] Secrets + IAM..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "  Cloud Run SA: ${SERVICE_ACCOUNT}"

for secret in DEEPFACT_GEMINI_API_KEY DEEPFACT_LINE_CHANNEL_ACCESS_TOKEN DEEPFACT_LINE_CHANNEL_SECRET; do
  if ! gcloud secrets describe "${secret}" >/dev/null 2>&1; then
    echo "❌ ${secret} が未登録です. GCPコンソールで作成してください"
    exit 1
  fi
  echo "  ✅ ${secret} found, granting accessor to SA..."
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
done

echo "[4/4] Cloud Build submit..."
gcloud builds submit --config=cloudbuild.yaml

URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo "================================================"
echo "✅ デプロイ完了"
echo "  URL:    ${URL}"
echo "  Health: ${URL}/health"
echo "================================================"
