resource "aws_lambda_function" "api" {
  # checkov:skip=CKV_AWS_115: No function-level concurrent execution limit required
  # checkov:skip=CKV_AWS_116: No Dead Letter Queue required
  # checkov:skip=CKV_AWS_173: Lambda environment variable encryption with default KMS key is acceptable

  function_name = "api"

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.api.repository_url}:latest"

  role    = aws_iam_role.api.arn
  timeout = 60

  memory_size = 1024

  environment {
    variables = {
      API_AUTH_TOKEN          = var.api_auth_token
      NOTIFY_KEY              = var.notify_key
      SQLALCHEMY_DATABASE_URI = module.rds.proxy_connection_string_value
    }
  }

  vpc_config {
    security_group_ids = [module.rds.proxy_security_group_id, aws_security_group.api.id]
    subnet_ids         = module.vpc.private_subnet_ids
  }

  tracing_config {
    mode = "PassThrough"
  }

  lifecycle {
    ignore_changes = [
      image_uri,
    ]
  }
}

resource "aws_lambda_permission" "api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}
