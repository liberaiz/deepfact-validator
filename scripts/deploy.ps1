# DeepFact Validator Cloud Run deploy (PowerShell)
# Usage: cd ...\deepfact-validator; .\scripts\deploy.ps1
# NOTE: ErrorActionPreference must be Continue for PowerShell 5 + gcloud
$ErrorActionPreference = "Continue"

$ProjectId   = if ($env:PROJECT_ID)   { $env:PROJECT_ID }   else { "deepfact-validator" }
$Region      = if ($env:REGION)       { $env:REGION }       else { "asia-northeast1" }
$ServiceName = if ($env:SERVICE_NAME) { $env:SERVICE_NAME } else { "deepfact-validator" }
$RepoName    = if ($env:REPO_NAME)    { $env:REPO_NAME }    else { "deepfact-validator" }

Write-Host "----- DeepFact Validator Cloud Run deploy -----"
Write-Host "  PROJECT_ID: $ProjectId"
Write-Host "  REGION:     $Region"
Write-Host "  SERVICE:    $ServiceName"
Write-Host "-----------------------------------------------"

gcloud config set project $ProjectId
if ($LASTEXITCODE -ne 0) { Write-Host "[NG] gcloud config set project failed" -ForegroundColor Red; exit 1 }

Write-Host "[1/4] Enable APIs..."
gcloud services enable `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  aiplatform.googleapis.com `
  firestore.googleapis.com `
  cloudbuild.googleapis.com `
  logging.googleapis.com `
  monitoring.googleapis.com
if ($LASTEXITCODE -ne 0) { Write-Host "[NG] services enable failed" -ForegroundColor Red; exit 1 }

Write-Host "[2/4] Artifact Registry repo..."
gcloud artifacts repositories describe $RepoName --location=$Region 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
  Write-Host "  [OK] Repo $RepoName already exists"
} else {
  Write-Host "  [INFO] Repo not found, creating..."
  gcloud artifacts repositories create $RepoName `
    --repository-format=docker `
    --location=$Region `
    --description="DeepFact Validator container repo"
  if ($LASTEXITCODE -ne 0) { Write-Host "[NG] repo create failed" -ForegroundColor Red; exit 1 }
}

Write-Host "[3/4] Secrets + IAM..."
$ProjectNumber = (gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()
$ServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"
Write-Host "  Cloud Run SA: $ServiceAccount"

$secrets = @(
  "DEEPFACT_GEMINI_API_KEY",
  "DEEPFACT_LINE_CHANNEL_ACCESS_TOKEN",
  "DEEPFACT_LINE_CHANNEL_SECRET"
)
foreach ($secret in $secrets) {
  gcloud secrets describe $secret 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[NG] $secret not registered. Create in GCP Console." -ForegroundColor Red
    exit 1
  }
  Write-Host "  [OK] $secret found, granting accessor to SA..."
  gcloud secrets add-iam-policy-binding $secret `
    --member="serviceAccount:$ServiceAccount" `
    --role="roles/secretmanager.secretAccessor" `
    --quiet 2>&1 | Out-Null
}

Write-Host "[4/4] Cloud Build submit..."
gcloud builds submit --config=cloudbuild.yaml
if ($LASTEXITCODE -ne 0) { Write-Host "[NG] Cloud Build failed" -ForegroundColor Red; exit 1 }

$Url = (gcloud run services describe $ServiceName --region=$Region --format="value(status.url)").Trim()

Write-Host ""
Write-Host "----- DEPLOY COMPLETE -----" -ForegroundColor Green
Write-Host "  URL:     $Url"
Write-Host "  Health:  $Url/health"
Write-Host "  Webhook: $Url/webhook   (paste this into LINE Developers)"
Write-Host "---------------------------"
