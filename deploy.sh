#!/bin/bash
# AgentMaster — Deploy to Google Cloud Run
# Usage: ./deploy.sh [REGION]

set -e

REGION="${1:-europe-west1}"
SERVICE_NAME="agentmaster"

# Get API key from backend/.env
if [ -f "backend/.env" ]; then
    GEMINI_API_KEY=$(grep "^GEMINI_API_KEY=" backend/.env | cut -d'=' -f2)
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY not found in backend/.env"
    exit 1
fi

PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    echo "Error: No GCP project set. Run: gcloud config set project YOUR_PROJECT"
    exit 1
fi

IMAGE="gcr.io/$PROJECT/$SERVICE_NAME"

echo "==> Project : $PROJECT"
echo "==> Image   : $IMAGE"
echo "==> Region  : $REGION"
echo ""

# 1. Enable required APIs
echo "[1/4] Enabling Cloud APIs..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com --project "$PROJECT"

# 2. Build & push image using Cloud Build
echo "[2/4] Building image via Cloud Build..."
gcloud builds submit . \
    --tag "$IMAGE" \
    --project "$PROJECT"

# 3. Deploy to Cloud Run
echo "[3/4] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,DATABASE_URL=sqlite:////tmp/data/agentmaster.db,CORS_ORIGINS_RAW=*,GCS_BUCKET=agentmaster-db-$PROJECT,GCS_DB_KEY=agentmaster.db" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --project "$PROJECT"

# 4. Get the URL
echo "[4/4] Getting service URL..."
URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT" --format "value(status.url)")

echo ""
echo "✅ Deployed successfully!"
echo "URL: $URL"
echo ""
echo "To test the clear-blueprint endpoint:"
echo "curl -X POST $URL/api/pipelines/{pipeline_id}/clear-blueprint"
