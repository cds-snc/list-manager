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

resource "aws_cloudwatch_log_metric_filter" "lambda-api-errors" {
  name           = "api-errors"
  pattern        = "ERROR? Error? error?"
  log_group_name = "/aws/lambda/${aws_lambda_function.api.function_name}"

  metric_transformation {
    name      = "api-errors"
    namespace = "LogMetrics"
    value     = "1"
  }
}

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
  ok_actions          = [aws_sns_topic.warning.arn]
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

resource "aws_cloudwatch_metric_alarm" "logs-1-api-error-1-minute-warning" {
  alarm_name          = "logs-1-api-error-1-minute-warning"
  alarm_description   = "One API error in 1 minute"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = aws_cloudwatch_log_metric_filter.lambda-api-errors.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.lambda-api-errors.metric_transformation[0].namespace
  period              = "60"
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]
}

resource "aws_cloudwatch_metric_alarm" "api-gateway-above-maximum-latency-warning" {
  alarm_name          = "api-gateway-above-maximum-latency-warning"
  alarm_description   = "API gateway latency between request and response above 1500ms"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  extended_statistic  = "p95"
  threshold           = 1500
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "api-gateway-above-maximum-latency-critical" {
  alarm_name          = "api-gateway-above-maximum-latency-critical"
  alarm_description   = "API gateway latency between request and response above 3000ms"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  extended_statistic  = "p95"
  threshold           = 3000
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.critical.arn]
  ok_actions          = [aws_sns_topic.critical.arn]
  dimensions = {
    ApiName = aws_api_gateway_rest_api.api.name
  }
}

#
# API: possible brute-force of API auth token
#
resource "aws_cloudwatch_metric_alarm" "api-invalid-auth-token-warning" {
  alarm_name          = "api-invalid-auth-token-warning"
  alarm_description   = "API invalid auth token requests in 5 minute period warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "IncorrectAuthorizationToken"
  namespace           = "ListManager"
  statistic           = "Sum"
  period              = "300"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]
  dimensions = {
    service = "api"
  }
}

#
# WAF: high percentage of blocked requests
# 
resource "aws_cloudwatch_metric_alarm" "waf-block-request-warning" {
  alarm_name          = "waf-block-request-warning"
  alarm_description   = "50% of requests being blocked in 5 minute period warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  threshold           = "50"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.warning.arn]
  ok_actions          = [aws_sns_topic.warning.arn]

  metric_query {
    id          = "blocked_request_percent"
    expression  = "100*blocked/(blocked+allowed)"
    label       = "WAF blocked requests percent"
    return_data = "true"
  }

  metric_query {
    id = "blocked"
    metric {
      metric_name = "BlockedRequests"
      namespace   = "AWS/WAFV2"
      period      = "300"
      stat        = "Sum"

      dimensions = {
        Rule   = "ALL"
        Region = var.region
        WebACL = aws_wafv2_web_acl.api_waf.name
      }
    }
  }

  metric_query {
    id = "allowed"
    metric {
      metric_name = "AllowedRequests"
      namespace   = "AWS/WAFV2"
      period      = "300"
      stat        = "Sum"

      dimensions = {
        Rule   = "ALL"
        Region = var.region
        WebACL = aws_wafv2_web_acl.api_waf.name
      }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "route53_list_manager_health_check" {
  provider = aws.us-east-1

  alarm_name          = "route53-list-manager-health-check"
  alarm_description   = "Health check failing for the list manager"
  comparison_operator = "LessThanThreshold"
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = "60"
  evaluation_periods  = "2"
  statistic           = "Average"
  threshold           = "1"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.warning_us_east.arn]
  ok_actions          = [aws_sns_topic.warning_us_east.arn]
  dimensions = {
    HealthCheckId = aws_route53_health_check.list_manager.id
  }
}
