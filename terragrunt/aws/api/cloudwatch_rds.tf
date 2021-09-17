#
# RDS alarms
# 
locals {
  rds_aurora_replica_lag_maximum = 2000
  rds_cpu_maxiumum               = 80
  rds_freeable_memory_minimum    = 64000000
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_utilization_writer" {
  alarm_name          = "RDSCpuUtilizationWriter"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = local.rds_cpu_maxiumum

  alarm_description = "CPU utilization for RDS cluster writer in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "WRITER"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_utilization_reader" {
  alarm_name          = "RDSCpuUtilizationReader"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = local.rds_cpu_maxiumum

  alarm_description = "CPU utilization for RDS cluster reader in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "READER"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_aurora_replica_lag" {
  alarm_name          = "RdsAuroraReplicaLag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "AuroraReplicaLag"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = local.rds_aurora_replica_lag_maximum

  alarm_description = "Replica lag (milliseconds) for RDS cluster reader in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "READER"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_freeable_memory_writer" {
  alarm_name          = "RdsFreeableMemoryWriter"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Minimum"
  threshold           = local.rds_freeable_memory_minimum

  alarm_description = "Minimum freeable memory (Bytes) for RDS cluster writer in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "WRITER"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_freeable_memory_reader" {
  alarm_name          = "RdsFreeableMemoryReader"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Minimum"
  threshold           = local.rds_freeable_memory_minimum

  alarm_description = "Freeable memory (Bytes) for RDS cluster reader in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "READER"
  }
}
