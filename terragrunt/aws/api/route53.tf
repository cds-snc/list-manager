resource "aws_route53_record" "list_manager_A" {
  # checkov:skip=CKV2_AWS_23: False-positive, record is attached to API gateway domain name

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api.regional_domain_name
    zone_id                = aws_api_gateway_domain_name.api.regional_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_health_check" "list_manager" {
  fqdn              = var.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/healthcheck"
  failure_threshold = "3"
  request_interval  = "30"

  tags = {
    CostCenter = var.billing_code
  }
}
