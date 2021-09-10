variable "api_auth_token" {
  type      = string
  sensitive = true
}

variable "domain_name" {
  type = string
}

variable "hosted_zone_id" {
  type = string
}

variable "notify_key" {
  type      = string
  sensitive = true
}

variable "rds_password" {
  type      = string
  sensitive = true
}

variable "rds_username" {
  type = string
}

variable "rds_proxy_security_group_id" {
  type = string
}

variable "slack_webhook_url" {
  type      = string
  sensitive = true
}