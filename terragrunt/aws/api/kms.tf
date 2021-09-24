
data "aws_iam_policy_document" "kms_policies" {
  # checkov:skip=CKV_AWS_109: `resources=["*"]` references the key the policy is attached to
  # checkov:skip=CKV_AWS_111: `resources=["*"]` references the key the policy is attached to

  statement {

    effect = "Allow"

    actions = [
      "kms:*"
    ]

    resources = [
      "*"
    ]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.account_id}:root"]
    }
  }
  statement {

    effect = "Allow"

    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]

    resources = [
      "*"
    ]

    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }
  }

  statement {

    effect = "Allow"

    actions = [
      "kms:Decrypt*",
      "kms:GenerateDataKey*",
    ]

    resources = [
      "*"
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
  }

}

resource "aws_kms_key" "list-manager" {
  description         = "KMS Key"
  enable_key_rotation = true

  policy = data.aws_iam_policy_document.kms_policies.json

  tags = {
    CostCenter = var.billing_code
  }
}

resource "aws_kms_key" "list-manager-us-east" {
  provider = aws.us-east-1

  description         = "KMS Key"
  enable_key_rotation = true

  policy = data.aws_iam_policy_document.kms_policies.json

  tags = {
    CostCenter = var.billing_code
  }
}
