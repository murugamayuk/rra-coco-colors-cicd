variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

#### resource group name ####
variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "rg-mayuksacred-5599"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "foundry_endpoint" {
  description = "Azure AI Foundry project endpoint"
  type        = string
  sensitive   = true
}
