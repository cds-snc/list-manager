module "vpc" {
  source            = "github.com/cds-snc/terraform-modules?ref=v0.0.21//vpc"
  name              = var.product_name
  billing_tag_value = var.billing_code
  high_availability = true
  enable_flow_log   = true
}

data "aws_security_group" "rds_proxy_sg" {
  id = var.rds_proxy_security_group_id
}

resource "aws_security_group_rule" "rds_sg_egress_443" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = data.aws_security_group.rds_proxy_sg.id
}
