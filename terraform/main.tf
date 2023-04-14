terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

provider "google" {
}

resource "google_artifact_registry_repository" "my-repo" {
  location      = var.region
  repository_id = var.artifact_repository_name
  description   = "Repo for Prefect agent images"
  format        = "DOCKER"
}

resource "google_storage_bucket" "data-lake-bucket" {
  name                        = var.bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = true
  versioning {
    enabled = true
  }
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = var.dataset_name
  location                   = var.location
  friendly_name              = "Crypto Market Data"
  description                = "Dataset for crypto market analysis"
  delete_contents_on_destroy = true
}
