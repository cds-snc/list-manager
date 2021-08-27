resource "aws_sns_topic" "critical" {
  name              = "critical-alert-list-manager"
  kms_master_key_id = aws_kms_key.list-manager.arn

  tags = {
    CostCenter = var.billing_code
  }
}

resource "aws_sns_topic" "warning" {
  name              = "warning-alert-list-manager"
  kms_master_key_id = aws_kms_key.list-manager.arn

  tags = {
    CostCenter = var.billing_code
  }
}