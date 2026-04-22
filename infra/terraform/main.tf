terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.13"
    }
  }
  backend "azurerm" {
    # Configured via -backend-config in CI/CD
    # resource_group_name  = set via TF_STATE_RG secret
    # storage_account_name = set via TF_STATE_SA secret
    # container_name       = set via TF_STATE_CONTAINER secret (value: "tfstate")
    # key                  = "coco-colors-{env}.tfstate"
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
}

provider "azapi" {
  use_oidc = true
}

# ── DATA SOURCES ─────────────────────────────────────────────────────────────
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# ── AI SEARCH (for RAG / Knowledge base) ─────────────────────────────────────
resource "azurerm_search_service" "candidate_search" {
  name                = "coco-search-${var.environment}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = var.environment == "production" ? "basic" : "free"
  tags                = local.common_tags
}

# ── STORAGE (Bronze / Silver / Gold medallion) ───────────────────────────────
resource "azurerm_storage_account" "pipeline" {
  name                     = "cococolors${var.environment}sa"
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = data.azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.common_tags
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.pipeline.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.pipeline.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.pipeline.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "candidate_docs" {
  name                  = "candidate-docs"
  storage_account_name  = azurerm_storage_account.pipeline.name
  container_access_type = "private"
}

# ── KEY VAULT (secrets management) ───────────────────────────────────────────
resource "azurerm_key_vault" "pipeline" {
  name                = "coco-kv-${var.environment}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"
  tags                = local.common_tags
}

# ── LOCALS ────────────────────────────────────────────────────────────────────
locals {
  common_tags = {
    project     = "coco-colors"
    environment = var.environment
    managed_by  = "terraform"
    owner       = "mayuksacred@gmail.com"
  }
}

# ── OUTPUTS ───────────────────────────────────────────────────────────────────
output "search_service_endpoint" {
  value = "https://${azurerm_search_service.candidate_search.name}.search.windows.net"
}

output "storage_account_name" {
  value = azurerm_storage_account.pipeline.name
}
