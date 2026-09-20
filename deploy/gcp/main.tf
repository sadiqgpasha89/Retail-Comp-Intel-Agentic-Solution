terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application Name"
  type        = string
  default     = "retail-intel-agentic"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Create an Artifact Registry repository for the Docker image
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Docker repository for Retail Intel Agentic Demo"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifact_registry_api]
}

# Define the Cloud Run Service
resource "google_cloud_run_v2_service" "default" {
  name     = var.app_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.app_name}:latest"
      
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      
      resources {
        limits = {
          cpu    = "2"
          memory = "2048Mi"
        }
      }
    }
  }

  depends_on = [google_project_service.run_api]
}

# Make the Cloud Run service publicly accessible (no IAM required)
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_v2_service.default.location
  project  = google_cloud_run_v2_service.default.project
  service  = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value       = google_cloud_run_v2_service.default.uri
  description = "The public URL of the Cloud Run service."
}
