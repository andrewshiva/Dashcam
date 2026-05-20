# Enable Compute Engine API
resource "google_project_service" "compute" {
  project = var.project_id
  service = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vpcaccess" {
  project = var.project_id
  service = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

# Shared VPC Network
resource "google_compute_network" "shared_vpc" {
  name                    = var.network_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  depends_on              = [google_project_service.compute]
}


# Subnets
resource "google_compute_subnetwork" "web" {
  name          = "subnet-web"
  project       = var.project_id
  network       = google_compute_network.shared_vpc.id
  region        = var.region
  ip_cidr_range = "10.0.1.0/24"
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "app" {
  name          = "subnet-app"
  project       = var.project_id
  network       = google_compute_network.shared_vpc.id
  region        = var.region
  ip_cidr_range = "10.0.2.0/24"
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "data" {
  name          = "subnet-data"
  project       = var.project_id
  network       = google_compute_network.shared_vpc.id
  region        = var.region
  ip_cidr_range = "10.0.3.0/24"
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "mgmt" {
  name          = "subnet-mgmt"
  project       = var.project_id
  network       = google_compute_network.shared_vpc.id
  region        = var.region
  ip_cidr_range = "10.0.4.0/24"
  private_ip_google_access = true
}

# Cloud Router and NAT
resource "google_compute_router" "router" {
  name    = "nat-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.shared_vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "nat-config"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.router.name
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  nat_ip_allocate_option             = "AUTO_ONLY"
}

resource "google_vpc_access_connector" "serverless" {
  name          = var.connector_name
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.shared_vpc.name
  ip_cidr_range = "10.8.0.0/28"

  depends_on = [google_project_service.vpcaccess]
}

# Basic Firewall Rules
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  project = var.project_id
  network = google_compute_network.shared_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP range
}
