resource "aws_cloudwatch_event_rule" "every-three-minutes" {
  name                = "lambda-warmer"
  description         = "Fires every three minutes"
  schedule_expression = "rate(3 minutes)"
}

resource "aws_cloudwatch_event_target" "tigger-lambda-every-three-minutes" {
  rule      = aws_cloudwatch_event_rule.every-three-minutes.name
  target_id = "${var.product_name}-${var.env}-lambda-warmer"
  arn       = aws_lambda_function.api.arn
  input     = "{'task': 'heartbeat'}"
}

resource "aws_lambda_permission" "allow-cloudwatch-to-call-lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every-three-minutes.arn
}