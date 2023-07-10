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
  protocol  = "lambda"
  endpoint  = module.notify_slack.lambda_arn
}

resource "aws_sns_topic_subscription" "warning" {
  topic_arn = aws_sns_topic.warning.arn
  protocol  = "lambda"
  endpoint  = module.notify_slack.lambda_arn
}

resource "aws_sns_topic_subscription" "warning_us_east" {
  provider = aws.us-east-1

  topic_arn = aws_sns_topic.warning_us_east.arn
  protocol  = "lambda"
  endpoint  = module.notify_slack.lambda_arn
}

#
# Lambda: post notifications to Slack
#
#
# Lambda: post notifications to Slack
#
module "notify_slack" {
  source = "github.com/cds-snc/terraform-modules//notify_slack?ref=v0.0.49"

  function_name     = "notify_slack"
  project_name      = "ListManager"
  slack_webhook_url = var.slack_webhook_url

  sns_topic_arns = [
    aws_sns_topic.warning.arn,
    aws_sns_topic.warning_us_east.arn,
    aws_sns_topic.critical.arn
  ]

  billing_tag_key   = "CostCenter"
  billing_tag_value = var.billing_code
}
