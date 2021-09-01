resource "aws_route53_zone" "list_manager" {
  name = var.hosted_zone_name

  tags = {
    CostCenter = var.billing_code
  }
}
