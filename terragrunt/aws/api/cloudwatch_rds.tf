#
# RDS alarms
# 
resource "aws_cloudwatch_metric_alarm" "rds_cpu_utilization_writer" {
  alarm_name          = "RDSCpuUtilizationWriter"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = 80

  alarm_description = "CPU utilization for RDS cluster writer in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "WRITER"
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
  threshold           = 64000000

  alarm_description = "Minimum freeable memory (Bytes) for RDS cluster writer in a 5 minute period"
  alarm_actions     = [aws_sns_topic.warning.arn]
  ok_actions        = [aws_sns_topic.warning.arn]

  dimensions = {
    DBClusterIdentifier = module.rds.rds_cluster_id
    Role                = "WRITER"
  }
}
