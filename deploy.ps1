# AgentMaster — Deploy to Google Cloud Run
# Usage: .\deploy.ps1 -ApiKey "your-gemini-api-key"
# Or set env var GEMINI_API_KEY before running

param(
    [string]$ApiKey = "",
    [string]$Region = "europe-west1",
    [string]$ServiceName = "agentmaster"
)

# Auto-read GEMINI_API_KEY from backend/.env if not passed
if (-not $ApiKey) {
    $envFile = Join-Path $PSScriptRoot "backend\.env"
    if (Test-Path $envFile) {
        $match = Select-String -Path $envFile -Pattern "^GEMINI_API_KEY=(.+)$"
        if ($match) { $ApiKey = $match.Matches[0].Groups[1].Value.Trim() }
    }
}

$PROJECT = (gcloud config get-value project 2>$null).Trim()
if (-not $PROJECT) { Write-Error "No GCP project set. Run: gcloud config set project YOUR_PROJECT"; exit 1 }
if (-not $ApiKey)  { Write-Error "Provide -ApiKey or set GEMINI_API_KEY env var"; exit 1 }

$IMAGE = "gcr.io/$PROJECT/$ServiceName"

Write-Host "==> Project : $PROJECT" -ForegroundColor Cyan
Write-Host "==> Image   : $IMAGE" -ForegroundColor Cyan
Write-Host "==> Region  : $Region" -ForegroundColor Cyan
Write-Host ""

# 1. Enable required APIs
Write-Host "[1/4] Enabling Cloud APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com containerregistry.googleapis.com --project $PROJECT

# 2. Build & push image using Cloud Build (no local Docker needed)
Write-Host "[2/4] Building image via Cloud Build..." -ForegroundColor Yellow
Set-Location $PSScriptRoot
gcloud builds submit . `
    --tag $IMAGE `
    --project $PROJECT
if ($LASTEXITCODE -ne 0) { Write-Error "Cloud Build failed"; exit 1 }

# 3. Deploy to Cloud Run
Write-Host "[3/4] Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image $IMAGE `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --timeout 3600 `
    --set-env-vars "GEMINI_API_KEY=$ApiKey,DATABASE_URL=sqlite:////tmp/data/agentmaster.db,CORS_ORIGINS_RAW=*,GCS_BUCKET=agentmaster-db-$PROJECT,GCS_DB_KEY=agentmaster.db" `
    --project $PROJECT

if ($LASTEXITCODE -ne 0) { Write-Error "Cloud Run deploy failed"; exit 1 }

# 4. Get the URL
Write-Host "[4/4] Getting service URL..." -ForegroundColor Yellow
$URL = (gcloud run services describe $ServiceName --region $Region --project $PROJECT --format "value(status.url)" 2>$null).Trim()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Deployed successfully!" -ForegroundColor Green
Write-Host " URL: $URL" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open: $URL" -ForegroundColor Cyan
