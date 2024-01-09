locals {
  api_errors = [
    "ERROR",
    "Error",
    "error",
  ]
  api_errors_skip = [
    "email_address Not a valid email address",
  ]
  api_error_metric_pattern = "[(w1=\"*${join("*\" || w1=\"*", local.api_errors)}*\") && w1!=\"*${join("*\" && w1!=\"*", local.api_errors_skip)}*\"]"
}