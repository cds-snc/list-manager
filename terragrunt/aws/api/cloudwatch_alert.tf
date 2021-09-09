resource "aws_cloudwatch_metric_alarm" "logs-1-500-error-1-minute-warning" {
  alarm_name          = "logs-1-500-error-1-minute-warning"
  alarm_description   = "One 500 error in 1 minute"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.lambda-500-errors.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.lambda-500-errors.metric_transformation[0].namespace
  period              = "60"
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning]
}

resource "aws_cloudwatch_metric_alarm" "logs-10-500-error-5-minutes-critical" {
  alarm_name          = "logs-10-500-error-5-minutes-critical"
  alarm_description   = "Ten 500 errors in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.lambda-500-errors.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.lambda-500-errors.metric_transformation[0].namespace
  period              = "300"
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.critical]
  ok_actions          = [aws_sns_topic.critical]
}

resource "aws_cloudwatch_metric_alarm" "logs-1-429-error-1-minute-warning" {
  alarm_name          = "logs-1-429-error-1-minute-warning"
  alarm_description   = "One 429 error in 1 minute"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.lambda-429-errors.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.lambda-429-errors.metric_transformation[0].namespace
  period              = "60"
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning]
}

resource "aws_cloudwatch_metric_alarm" "logs-10-429-error-5-minutes-critical" {
  alarm_name          = "logs-10-429-error-5-minutes-critical"
  alarm_description   = "Ten 429 errors in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.lambda-429-errors.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.lambda-429-errors.metric_transformation[0].namespace
  period              = "300"
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.critical]
  ok_actions          = [aws_sns_topic.critical]
}