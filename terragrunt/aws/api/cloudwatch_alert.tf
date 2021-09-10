resource "aws_cloudwatch_metric_alarm" "logs-1-5XX-error-1-minute-warning" {
  alarm_name          = "logs-1-5XX-error-1-minute-warning"
  alarm_description   = "One 5XX error in 1 minute"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "logs-10-5XX-error-5-minutes-critical" {
  alarm_name          = "logs-10-5XX-error-5-minutes-critical"
  alarm_description   = "Ten 5XX errors in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.critical.arn]
  ok_actions          = [aws_sns_topic.critical.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "logs-1-4xx-error-1-minute-warning" {
  alarm_name          = "logs-1-4xx-error-1-minute-warning"
  alarm_description   = "One 4xx error in 1 minute"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "logs-10-4xx-error-5-minutes-critical" {
  alarm_name          = "logs-10-4xx-error-5-minutes-critical"
  alarm_description   = "Ten 4xx errors in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.critical.arn]
  ok_actions          = [aws_sns_topic.critical.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
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
  alarm_actions       = [aws_sns_topic.warning.arn]
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
  alarm_actions       = [aws_sns_topic.critical.arn]
  ok_actions          = [aws_sns_topic.critical.arn]
}