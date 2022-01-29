resource "aws_wafv2_web_acl" "api_waf" {
  name        = "api_waf"
  description = "WAF for API protection"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "api_rate_limit"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 10000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "api_rate_limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "api_invalid_path"
    priority = 10

    action {
      block {
        custom_response {
          response_code = 204
        }
      }
    }

    statement {
      not_statement {
        statement {
          regex_pattern_set_reference_statement {
            arn = aws_wafv2_regex_pattern_set.re_list_manager_api.arn
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 1
              type     = "COMPRESS_WHITE_SPACE"
            }
            text_transformation {
              priority = 2
              type     = "LOWERCASE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "api_invalid_path"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 20

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        excluded_rule {
          name = "GenericRFI_BODY"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 30

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesLinuxRuleSet"
    priority = 40

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesLinuxRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 50

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "api"
    sampled_requests_enabled   = false
  }
}

resource "aws_wafv2_regex_pattern_set" "re_list_manager_api" {
  name        = "re_list_manager_api"
  description = "Regex matching valid list manager endpoints"
  scope       = "REGIONAL"

  # WAF Regex blocks are combined with OR logic. 
  # Regex support is limited, please see: 
  # https://docs.aws.amazon.com/waf/latest/developerguide/waf-regex-pattern-set-managing.html

  # GET /healthcheck
  # POST /list
  # GET /lists
  # POST /send
  # POST /subscription
  # GET /version
  regular_expression {
    regex_string = "/healthcheck|/list|/lists|/send|/subscription|/version"
  }

  # PUT /list/<uuid:list_id>/reset
  # GET /lists/<uuid:service_id>
  # PUT /lists/<uuid:service_id>
  # GET /lists/<uuid:service_id>/subscriber-count/
  # DELETE /lists/<uuid:service_id>
  regular_expression {
    regex_string = "/lists?/[\\w]{8}-[\\w]{4}-[\\w]{4}-[\\w]{4}-[\\w]{12}(/subscriber-count/|/reset)?"
  }

  # GET /subscription/<uuid:subscription_id>/confirm
  # DELETE /subscription/<uuid:subscription_id>
  regular_expression {
    regex_string = "/subscription/[\\w]{8}-[\\w]{4}-[\\w]{4}-[\\w]{4}-[\\w]{12}(/confirm)?"
  }

  # GET /unsubscribe/<uuid:subscription_id>
  regular_expression {
    regex_string = "/unsubscribe/[\\w]{8}-[\\w]{4}-[\\w]{4}-[\\w]{4}-[\\w]{12}"
  }

  tags = {
    CostCenter = var.billing_code
  }
}

resource "aws_wafv2_web_acl_association" "waf_association" {
  resource_arn = aws_api_gateway_stage.api.arn
  web_acl_arn  = aws_wafv2_web_acl.api_waf.arn
}

#
# Write WAF logs to S3
#
resource "aws_wafv2_web_acl_logging_configuration" "api_waf" {
  log_destination_configs = [aws_kinesis_firehose_delivery_stream.api_waf_logs.arn]
  resource_arn            = aws_wafv2_web_acl.api_waf.arn
}

resource "aws_kinesis_firehose_delivery_stream" "api_waf_logs" {
  name        = "aws-waf-logs-api"
  destination = "extended_s3"

  server_side_encryption {
    enabled = true
  }

  extended_s3_configuration {
    role_arn   = aws_iam_role.write_waf_logs.arn
    prefix     = "waf_acl_logs/"
    bucket_arn = "arn:aws:s3:::${var.cbs_satellite_bucket_name}"
  }

  tags = {
    CostCenter = var.billing_code
    Terraform  = true
  }
}

resource "aws_iam_role" "write_waf_logs" {
  name               = "write-waf-logs"
  assume_role_policy = data.aws_iam_policy_document.firehose_assume_role.json

  tags = {
    CostCentre = var.billing_code
    Terraform  = true
  }
}

resource "aws_iam_policy" "write_waf_logs" {
  name        = "write-waf-logs"
  description = "Allow writing WAF logs to S3"
  policy      = data.aws_iam_policy_document.write_waf_logs.json

  tags = {
    CostCentre = var.billing_code
    Terraform  = true
  }
}

resource "aws_iam_role_policy_attachment" "write_waf_logs" {
  role       = aws_iam_role.write_waf_logs.name
  policy_arn = aws_iam_policy.write_waf_logs.arn
}

data "aws_iam_policy_document" "firehose_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "write_waf_logs" {
  statement {
    sid    = "S3PutObjects"
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject"
    ]
    resources = [
      "arn:aws:s3:::${var.cbs_satellite_bucket_name}",
      "arn:aws:s3:::${var.cbs_satellite_bucket_name}/waf_acl_logs/*"
    ]
  }
}
