#
# SNS: topics & subscriptions
#
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

resource "aws_sns_topic" "warning_us_east" {
  provider = aws.us-east-1

  name              = "warning-alert-list-manager"
  kms_master_key_id = aws_kms_key.list-manager-us-east.arn

  tags = {
    CostCenter = var.billing_code
  }
}

resource "aws_sns_topic_subscription" "critical" {
  topic_arn = aws_sns_topic.critical.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

resource "aws_sns_topic_subscription" "warning" {
  topic_arn = aws_sns_topic.warning.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

resource "aws_sns_topic_subscription" "warning_us_east" {
  provider = aws.us-east-1

  topic_arn = aws_sns_topic.warning_us_east.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}
