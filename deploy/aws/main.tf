terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application Name"
  type        = string
  default     = "retail-intel-agentic"
}

provider "aws" {
  region = var.region
}

# Create an Elastic Container Registry (ECR) for the Docker image
resource "aws_ecr_repository" "repo" {
  name                 = var.app_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for App Runner to pull from ECR
resource "aws_iam_role" "apprunner_access_role" {
  name = "${var.app_name}-apprunner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# Wait for image push (Handled externally via deploy.sh)
# The App Runner service assumes the image is already pushed to ECR before apply

resource "aws_apprunner_service" "default" {
  service_name = var.app_name

  source_configuration {
    image_repository {
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          ENVIRONMENT = "production"
        }
      }
      image_identifier      = "${aws_ecr_repository.repo.repository_url}:latest"
      image_repository_type = "ECR"
    }
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access_role.arn
    }
  }
  
  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }
}

output "service_url" {
  value       = aws_apprunner_service.default.service_url
  description = "The public URL of the App Runner service."
}
