locals {
  project_prefix = "nhai-das-${var.env}"
}

module "networking" {
  source         = "./modules/networking"
  project_id     = var.project_id
  region         = var.region
  network_name   = "${local.project_prefix}-shared-vpc"
  connector_name = "${local.project_prefix}-vpc-connector"
}

module "storage" {
  source        = "./modules/storage"
  project_id    = var.project_id
  region        = var.region
  env           = var.env
  bucket_prefix = local.project_prefix
}

module "security" {
  source         = "./modules/security"
  project_id     = var.project_id
  project_prefix = local.project_prefix
}

module "database" {
  source      = "./modules/database"
  project_id  = var.project_id
  region      = var.region
  network_id  = module.networking.network_id
  db_name     = "nhaidb"
  db_user     = "postgres"
  db_password = module.security.db_password
}

module "messaging" {
  source                = "./modules/messaging"
  project_id            = var.project_id
  region                = var.region
  project_prefix        = local.project_prefix
  raw_video_bucket      = module.storage.raw_video_bucket_name
  service_account_email = module.security.cloud_run_sa_email
}

module "api_gateway" {
  source         = "./modules/api_gateway"
  project_id     = var.project_id
  region         = var.region
  project_prefix = local.project_prefix
}

module "observability" {
  source      = "./modules/observability"
  project_id  = var.project_id
  region      = var.region
  alert_email = var.alert_email
}

module "billing" {
  source             = "./modules/billing"
  project_id         = var.project_id
  billing_account_id = var.billing_account_id
}
