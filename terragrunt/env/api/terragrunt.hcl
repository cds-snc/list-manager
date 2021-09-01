terraform {
  source = "../../aws//api"
}

dependencies {
  paths = ["../hosted_zone"]
}

dependency "hosted_zone" {
  config_path = "../hosted_zone"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs = {
    hosted_zone_id = ""
  }
}

inputs = {
  hosted_zone_id              = dependency.hosted_zone.outputs.hosted_zone_id
  domain_name                 = "list-manager.alpha.canada.ca"
  rds_username                = "databaseuser"
  rds_proxy_security_group_id = "sg-0fe09739f4ab9712d"
}

include {
  path = find_in_parent_folders()
}
