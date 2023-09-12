module "rds" {
  source                  = "github.com/cds-snc/terraform-modules//rds?ref=v7.0.2"
  database_name           = "list_manager"
  name                    = "list-manager"
  engine_version          = "13.11"
  instances               = 1
  username                = var.rds_username
  password                = var.rds_password
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  backup_retention_period = 7

  preferred_backup_window      = "07:00-09:00"
  preferred_maintenance_window = "wed:06:00-wed:07:00" # timezone is UTC
  allow_major_version_upgrade  = true

  billing_tag_value = var.billing_code
}
