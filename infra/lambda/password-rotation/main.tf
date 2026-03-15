terraform {
  backend "s3" {
    bucket = "tecnoepec-terraform-state"
    key    = "brandbrain.lambda.rotation.terraform.tfstate"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "tecnoepec-dev"
}

# ──────────────────────────────────────────────
# Variables
# ──────────────────────────────────────────────

variable "rds_cluster_id" {
  default = "tecnoepec-development"
}

variable "app_secret_name" {
  default = "development.BRANDBRAIN_DATABASE_URL"
}

variable "ecs_cluster" {
  default = "main"
}

variable "ecs_services" {
  default = "brandbrain-api,brandbrain-worker"
}

# ──────────────────────────────────────────────
# Data sources
# ──────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_rds_cluster" "aurora" {
  cluster_identifier = var.rds_cluster_id
}

# ──────────────────────────────────────────────
# IAM Role
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "brandbrain-password-rotation-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "brandbrain-password-rotation-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["rds:DescribeDBClusters"]
        Resource = data.aws_rds_cluster.aurora.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:rds!cluster-*",
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.app_secret_name}-*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService"]
        Resource = "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/${var.ecs_cluster}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
    ]
  })
}

# ──────────────────────────────────────────────
# Lambda Function
# ──────────────────────────────────────────────

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/handler.py"
  output_path = "${path.module}/handler.zip"
}

resource "aws_lambda_function" "password_rotation" {
  function_name    = "brandbrain-password-rotation-sync"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  timeout          = 60
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      RDS_CLUSTER_ID  = var.rds_cluster_id
      APP_SECRET_NAME = var.app_secret_name
      ECS_CLUSTER     = var.ecs_cluster
      ECS_SERVICES    = var.ecs_services
    }
  }
}

# ──────────────────────────────────────────────
# EventBridge Rule — triggers on RDS secret rotation
# ──────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "rds_secret_rotation" {
  name        = "brandbrain-rds-password-rotated"
  description = "Triggers when RDS managed secret is rotated"

  event_pattern = jsonencode({
    source      = ["aws.secretsmanager"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = ["secretsmanager.amazonaws.com"]
      eventName   = ["RotateSecret", "PutSecretValue"]
      requestParameters = {
        secretId = [{ prefix = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:rds!cluster-" }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "invoke_lambda" {
  rule      = aws_cloudwatch_event_rule.rds_secret_rotation.name
  target_id = "password-rotation-lambda"
  arn       = aws_lambda_function.password_rotation.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.password_rotation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rds_secret_rotation.arn
}
