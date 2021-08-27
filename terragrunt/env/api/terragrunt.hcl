terraform {
  source = "../../aws//api"
}

inputs = {
  rds_username                = "databaseuser"
  rds_proxy_security_group_id = "sg-0fe09739f4ab9712d"
}

include {
  path = find_in_parent_folders()
}
