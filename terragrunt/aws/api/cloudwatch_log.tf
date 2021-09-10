###
# AWS log log metric filters
###
resource "aws_cloudwatch_log_metric_filter" "lambda-429-errors" {
  name           = "429-errors"
  pattern        = "failed with 429"
  log_group_name = "/aws/lambda/${aws_lambda_function.api.function_name}"

  metric_transformation {
    name      = "429-errors"
    namespace = "LogMetrics"
    value     = "1"
  }
}