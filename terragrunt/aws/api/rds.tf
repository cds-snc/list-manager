module "rds" {
  source                  = "github.com/cds-snc/terraform-modules//rds?ref=v9.4.9"
  database_name           = "list_manager"
  name                    = "list-manager"
  engine_version          = "15.4"
  instances               = 1
  username                = var.rds_username
  password                = var.rds_password
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  backup_retention_period = 7

  preferred_backup_window      = "07:00-09:00"
  preferred_maintenance_window = "fri:06:00-fri:07:00" # timezone is UTC
  allow_major_version_upgrade  = true

  billing_tag_value = var.billing_code
}

import {
  to = module.rds.aws_security_group_rule.rds_proxy_egress
  id = "${module.rds.proxy_security_group_id}_egress_tcp_5432_5432_self"
}

import {
  to = module.rds.aws_security_group_rule.rds_proxy_ingress
  id = "${module.rds.proxy_security_group_id}_ingress_tcp_5432_5432_self"
}