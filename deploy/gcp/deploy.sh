#!/usr/bin/env bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
APP_NAME="retail-intel-agentic"

echo "Deploying to GCP Project: $PROJECT_ID in Region: $REGION"

# 1. Initialize and apply Terraform (creates Artifact Registry & Cloud Run service)
echo "Applying Terraform configuration..."
terraform init
terraform apply -var="project_id=$PROJECT_ID" -var="region=$REGION" -var="app_name=$APP_NAME" -auto-approve

# 2. Build and push Docker image via Cloud Build
REPO_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}-repo/${APP_NAME}:latest"
echo "Building and pushing Docker image to $REPO_URL..."

# Assuming script is run from deploy/gcp, we build from the project root
cd ../../
gcloud builds submit --tag "$REPO_URL" -f docker/Dockerfile .

# 3. Update the Cloud Run service to deploy the newly pushed image
echo "Deploying new revision to Cloud Run..."
gcloud run deploy "$APP_NAME" \
  --image "$REPO_URL" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --quiet

echo "Deployment complete!"
