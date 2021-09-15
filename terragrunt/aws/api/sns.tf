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

resource "aws_sns_topic_subscription" "critical" {
  topic_arn = aws_sns_topic.critical.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.notify_slack.arn
}

resource "aws_sns_topic_subscription" "warning" {
  topic_arn = aws_sns_topic.warning.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.notify_slack.arn
}

#
# Lambda: post notifications to Slack
#
resource "aws_lambda_function" "notify_slack" {
  # checkov:skip=CKV_AWS_50: X-ray tracing not required for this function
  # checkov:skip=CKV_AWS_115: No function-level concurrent execution limit required
  # checkov:skip=CKV_AWS_116: No Dead Letter Queue required
  # checkov:skip=CKV_AWS_173: Lambda environment variable encryption with default KMS key is acceptable

  function_name = "notify_slack"
  description   = "Lambda function to post CloudWatch alarm notifications to a Slack channel."

  filename    = data.archive_file.notify_slack.output_path
  handler     = "notify_slack.lambda_handler"
  runtime     = "python3.8"
  timeout     = 30
  memory_size = 1024

  role             = aws_iam_role.notify_slack_lambda.arn
  source_code_hash = filebase64sha256(data.archive_file.notify_slack.output_path)

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      PROJECT_NAME      = "ListManager"
      LOG_EVENTS        = "True"
    }
  }

  vpc_config {
    security_group_ids = [aws_security_group.notify_slack.id]
    subnet_ids         = module.vpc.private_subnet_ids
  }

  depends_on = [
    aws_iam_role_policy_attachment.notify_slack_lambda,
    aws_cloudwatch_log_group.notify_slack_lambda,
  ]

  tags = {
    CostCenter = var.billing_code
  }
}

data "archive_file" "notify_slack" {
  type        = "zip"
  source_file = "notify_slack/notify_slack.py"
  output_path = "/tmp/notify_slack.py.zip"
}

resource "aws_lambda_permission" "notify_slack_warning" {
  statement_id  = "AllowExecutionFromSNSWarning"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_slack.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.warning.arn
}

resource "aws_lambda_permission" "notify_slack_critical" {
  statement_id  = "AllowExecutionFromSNSCritical"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_slack.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.critical.arn
}

#
# IAM: Lambda logs
#
resource "aws_iam_role" "notify_slack_lambda" {
  name               = "NotifySlackLambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_policy.json
}

resource "aws_iam_policy" "notify_slack_lambda" {
  name   = "NotifySlackLambda"
  path   = "/"
  policy = data.aws_iam_policy_document.notify_slack_lambda.json
}

resource "aws_iam_role_policy_attachment" "notify_slack_lambda" {
  role       = aws_iam_role.notify_slack_lambda.name
  policy_arn = aws_iam_policy.notify_slack_lambda.arn
}

data "aws_iam_policy_document" "lambda_assume_policy" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "notify_slack_lambda" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      aws_cloudwatch_log_group.notify_slack_lambda.arn
    ]
  }
}

#
# CloudWatch: Lambda logs
#
resource "aws_cloudwatch_log_group" "notify_slack_lambda" {
  # checkov:skip=CKV_AWS_158: CloudWatch log group encryption with default KMS key is acceptable
  name              = "/aws/lambda/notify_slack"
  retention_in_days = "14"

  tags = {
    CostCenter = var.billing_code
  }
}
