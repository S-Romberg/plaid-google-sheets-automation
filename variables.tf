variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The region to deploy resources to"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = "dev"
}

variable "plaid_env" {
  description = "Plaid environment (sandbox/development/production)"
  type        = string
  default     = "development"
}

variable "plaid_client_id" {
  description = "Plaid Client ID"
  type        = string
  sensitive   = true
}

variable "plaid_secret" {
  description = "Plaid Secret"
  type        = string
  sensitive   = true
}

variable "spreadsheet_id" {
  description = "Google Sheet ID to store transactions"
  type        = string
}

variable "plaid_tokens" {
  description = "JSON object mapping access tokens to item tokens"
  type        = string
  sensitive   = true
  # Example format:
  # {
  #   "access_token_1": ["item_id_1", "item_id_2"],
  #   "access_token_2": ["item_id_3"]
  # }
} 