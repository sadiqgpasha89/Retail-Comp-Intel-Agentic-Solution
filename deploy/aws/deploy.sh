#!/usr/bin/env bash
set -e

# Configuration
REGION="us-east-1"
APP_NAME="retail-intel-agentic"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URL="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
REPO_URL="${ECR_URL}/${APP_NAME}:latest"

echo "Deploying to AWS Account: $ACCOUNT_ID in Region: $REGION"

# 1. Initialize and apply Terraform specifically for ECR to exist before docker push
echo "Provisioning ECR repository..."
terraform init
terraform apply -target="aws_ecr_repository.repo" -var="region=$REGION" -var="app_name=$APP_NAME" -auto-approve

# 2. Build and push Docker image
echo "Logging into ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URL"

echo "Building Docker image..."
cd ../../
docker build -t "$APP_NAME" -f docker/Dockerfile .
docker tag "${APP_NAME}:latest" "$REPO_URL"

echo "Pushing Docker image to ECR..."
docker push "$REPO_URL"

# 3. Apply the rest of the Terraform to create App Runner service
cd deploy/aws
echo "Applying Terraform configuration to deploy App Runner..."
terraform apply -var="region=$REGION" -var="app_name=$APP_NAME" -auto-approve

echo "Deployment complete!"
