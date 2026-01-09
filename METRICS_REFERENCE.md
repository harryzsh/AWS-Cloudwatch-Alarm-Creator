# CloudWatch Metrics Reference

Complete list of all monitored metrics, thresholds, and severity levels for each AWS service.

**Last Updated:** January 2026  
**Based on:** AWS Official Documentation & Best Practices

---

## Table of Contents

- [EC2 Instances](#ec2-instances)
- [RDS (MySQL/PostgreSQL)](#rds-mysqlpostgresql)
- [ElastiCache Redis](#elasticache-redis)
- [EFS](#efs)
- [DocumentDB](#documentdb)
- [Application Load Balancer (ALB)](#application-load-balancer-alb)
- [OpenSearch](#opensearch)
- [MSK (Kafka)](#msk-kafka)
- [AmazonMQ (RabbitMQ)](#amazonmq-rabbitmq)
- [AWS WAF](#aws-waf)

---

## EC2 Instances

**Deployment Type:** Tag-Based  
**Total Alarms:** 11  
**Namespace:** `AWS/EC2`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| CPUUtilization | Info | 85% | > | CPU使用率 - Info级别 | **MAX** |
| CPUUtilization | Warning | 90% | > | CPU使用率 - Warning级别 | **MAX** |
| CPUUtilization | Critical | 95% | > | CPU使用率 - Critical级别 | **MAX** |
| NetworkIn | Info | 157,286,400 bytes | > | 网络入口带宽 - 150MB | **MAX** |
| NetworkIn | Warning | 314,572,800 bytes | > | 网络入口带宽 - 300MB | **MAX** |
| NetworkOut | Info | 157,286,400 bytes | > | 网络出口带宽 - 150MB | **MAX** |
| NetworkOut | Warning | 314,572,800 bytes | > | 网络出口带宽 - 300MB | **MAX** |
| StatusCheckFailed | Critical | 1 | ≥ | 状态检查失败 - 系统或实例问题 | **MAX** |
| StatusCheckFailed_System | Critical | 1 | ≥ | 系统状态检查失败 - AWS基础设施问题 | **MAX** |
| StatusCheckFailed_Instance | Critical | 1 | ≥ | 实例状态检查失败 - 实例配置问题 | **MAX** |
| StatusCheckFailed_AttachedEBS | Critical | 1 | ≥ | 附加EBS卷状态检查失败 - 存储连接问题 | **MAX** |

**AWS Recommendations:**
- CPUUtilization: 80% threshold recommended
- Status Checks: Critical for detecting infrastructure failures
- Period: 300s for CPU/Network, 60s for status checks

**Note:** All tag-based alarms use `SELECT MAX()` to catch the worst-case across all matching resources.

---

## RDS (MySQL/PostgreSQL)

**Deployment Type:** Tag-Based  
**Total Alarms:** 25  
**Namespace:** `AWS/RDS`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| DatabaseConnections | Info | 100 | > | 数据库连接数 | **MAX** |
| DatabaseConnections | Warning | 200 | > | 数据库连接数 | **MAX** |
| DatabaseConnections | Critical | 300 | > | 数据库连接数 | **MAX** |
| CPUUtilization | Info | 70% | > | CPU使用率 | **MAX** |
| CPUUtilization | Warning | 80% | > | CPU使用率 | **MAX** |
| CPUUtilization | Critical | 90% | > | CPU使用率 | **MAX** |
| FreeableMemory | Info | 1,073,741,824 bytes | < | 可用内存 - 低于1GB | **MAX** |
| FreeableMemory | Warning | 536,870,912 bytes | < | 可用内存 - 低于512MB | **MAX** |
| FreeableMemory | Critical | 268,435,456 bytes | < | 可用内存 - 低于256MB | **MAX** |
| FreeStorageSpace | Info | 10,737,418,240 bytes | < | 可用存储空间 - 低于10GB | **MAX** |
| FreeStorageSpace | Warning | 5,368,709,120 bytes | < | 可用存储空间 - 低于5GB | **MAX** |
| FreeStorageSpace | Critical | 2,147,483,648 bytes | < | 可用存储空间 - 低于2GB | **MAX** |
| ReadIOPS | Warning | 10,000 | > | 读IOPS | **MAX** |
| ReadIOPS | Critical | 20,000 | > | 读IOPS | **MAX** |
| WriteIOPS | Warning | 10,000 | > | 写IOPS | **MAX** |
| WriteIOPS | Critical | 20,000 | > | 写IOPS | **MAX** |
| ReadLatency | Warning | 0.01 seconds | > | 读延迟 - 超过10ms | **MAX** |
| ReadLatency | Critical | 0.02 seconds | > | 读延迟 - 超过20ms | **MAX** |
| WriteLatency | Warning | 0.01 seconds | > | 写延迟 - 超过10ms | **MAX** |
| WriteLatency | Critical | 0.02 seconds | > | 写延迟 - 超过20ms | **MAX** |
| ReplicaLag | Warning | 30 seconds | > | 复制延迟 | **MAX** |
| ReplicaLag | Critical | 60 seconds | > | 复制延迟 | **MAX** |
| DiskQueueDepth | Warning | 10 | > | 磁盘队列深度 - IO等待队列过长 | **MAX** |
| DiskQueueDepth | Critical | 20 | > | 磁盘队列深度 - IO等待队列过长 | **MAX** |
| BurstBalance | Warning | 20% | < | 突发余额 - GP2卷IOPS积分不足 | **MIN** |

**AWS Recommendations:**
- CPUUtilization: 90% threshold
- DatabaseConnections: Set based on instance class (max varies by size)
- DiskQueueDepth: Critical for I/O bottleneck detection
- BurstBalance: Only applicable to gp2 volumes (uses MIN to catch lowest value)
- ReplicaLag: 60s maximum recommended

**Note:** Using MAX catches the worst-case scenario across all instances in the GROUP BY.

---

## ElastiCache Redis

**Deployment Type:** Tag-Based  
**Total Alarms:** 19  
**Namespace:** `AWS/ElastiCache`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| EngineCPUUtilization | Info | 70% | > | Redis引擎CPU使用率 - 单线程CPU | **MAX** |
| EngineCPUUtilization | Warning | 80% | > | Redis引擎CPU使用率 | **MAX** |
| EngineCPUUtilization | Critical | 90% | > | Redis引擎CPU使用率 | **MAX** |
| DatabaseMemoryUsagePercentage | Info | 70% | > | 内存使用率 - 数据库内存使用百分比 | **MAX** |
| DatabaseMemoryUsagePercentage | Warning | 80% | > | 内存使用率 | **MAX** |
| DatabaseMemoryUsagePercentage | Critical | 90% | > | 内存使用率 | **MAX** |
| CurrConnections | Info | 5,000 | > | 当前连接数 - 客户端连接数量 | **MAX** |
| CurrConnections | Warning | 8,000 | > | 当前连接数 | **MAX** |
| CurrConnections | Critical | 10,000 | > | 当前连接数 | **MAX** |
| Evictions | Warning | 1,000 | > | 键驱逐数 - 内存不足导致的键驱逐 | **MAX** |
| Evictions | Critical | 5,000 | > | 键驱逐数 | **MAX** |
| CacheHitRate | Warning | 0.8 | < | 缓存命中率 - 缓存效率指标 | **MAX** |
| CacheHitRate | Critical | 0.6 | < | 缓存命中率 | **MAX** |
| ReplicationLag | Warning | 30 seconds | > | 复制延迟 - 主从复制延迟时间 | **MAX** |
| ReplicationLag | Critical | 60 seconds | > | 复制延迟 | **MAX** |
| NetworkBytesIn | Warning | 157,286,400 bytes | > | 网络入流量 - 150MB | **MAX** |
| NetworkBytesIn | Critical | 314,572,800 bytes | > | 网络入流量 - 300MB | **MAX** |
| NetworkBytesOut | Warning | 157,286,400 bytes | > | 网络出流量 - 150MB | **MAX** |
| NetworkBytesOut | Critical | 314,572,800 bytes | > | 网络出流量 - 300MB | **MAX** |

**AWS Recommendations:**
- EngineCPUUtilization: 90% threshold (Redis is single-threaded)
- DatabaseMemoryUsagePercentage: Monitor to prevent evictions
- CacheHitRate: < 0.8 indicates cache inefficiency
- Max connections: 65,000 per node

**Note:** MAX statistic catches the worst-performing node in the cluster.

---

## EFS

**Deployment Type:** Tag-Based  
**Total Alarms:** 8  
**Namespace:** `AWS/EFS`

| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| ClientConnections | Info | 100 | > | 客户端连接数 | **MAX** |
| ClientConnections | Warning | 200 | > | 客户端连接数 | **MAX** |
| ClientConnections | Critical | 300 | > | 客户端连接数 | **MAX** |
| PercentIOLimit | Info | 80% | > | IO限制百分比 | **MAX** |
| PercentIOLimit | Warning | 90% | > | IO限制百分比 | **MAX** |
| PercentIOLimit | Critical | 95% | > | IO限制百分比 | **MAX** |
| BurstCreditBalance | Warning | 1,099,511,627,776 bytes | < | 突发积分余额 - 低于1TB | **MAX** |
| BurstCreditBalance | Critical | 549,755,813,888 bytes | < | 突发积分余额 - 低于512GB | **MAX** |

**AWS Recommendations:**
- PercentIOLimit: Monitor to prevent I/O throttling
- BurstCreditBalance: Critical for burst performance mode

**Note:** MAX catches the worst-case across all file systems.

---

## DocumentDB

**Deployment Type:** Resource-Based  
**Total Alarms:** 27 per cluster  
**Namespace:** `AWS/DocDB`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| CPUUtilization | Info | 70% | > | CPU使用率 | **MAX** |
| CPUUtilization | Warning | 80% | > | CPU使用率 | **MAX** |
| CPUUtilization | Critical | 90% | > | CPU使用率 | **MAX** |
| DatabaseConnections | Info | 100 | > | 连接数 | **MAX** |
| DatabaseConnections | Warning | 200 | > | 连接数 | **MAX** |
| DatabaseConnections | Critical | 300 | > | 连接数 | **MAX** |
| FreeableMemory | Info | 1,073,741,824 bytes | < | 可用内存 - 低于1GB | **MAX** |
| FreeableMemory | Warning | 536,870,912 bytes | < | 可用内存 - 低于512MB | **MAX** |
| FreeableMemory | Critical | 268,435,456 bytes | < | 可用内存 - 低于256MB | **MAX** |
| ReadIOPS | Warning | 5,000 | > | 读IOPS | **MAX** |
| ReadIOPS | Critical | 10,000 | > | 读IOPS | **MAX** |
| WriteIOPS | Warning | 5,000 | > | 写IOPS | **MAX** |
| WriteIOPS | Critical | 10,000 | > | 写IOPS | **MAX** |
| ReadLatency | Warning | 0.01 seconds | > | 读延迟 - 超过10ms | **MAX** |
| ReadLatency | Critical | 0.02 seconds | > | 读延迟 - 超过20ms | **MAX** |
| WriteLatency | Warning | 0.01 seconds | > | 写延迟 - 超过10ms | **MAX** |
| WriteLatency | Critical | 0.02 seconds | > | 写延迟 - 超过20ms | **MAX** |
| DBInstanceReplicaLag | Warning | 1,000 ms | > | 复制延迟 - 超过1秒 | **MAX** |
| DBInstanceReplicaLag | Critical | 5,000 ms | > | 复制延迟 - 超过5秒 | **MAX** |
| VolumeBytesUsed | Info | 107,374,182,400 bytes | > | 存储使用量 - 超过100GB | **MAX** |
| VolumeBytesUsed | Warning | 161,061,273,600 bytes | > | 存储使用量 - 超过150GB | **MAX** |
| BufferCacheHitRatio | Warning | 95% | < | 缓冲区缓存命中率 - 低于95%表示内存不足 | **MAX** |
| IndexBufferCacheHitRatio | Warning | 95% | < | 索引缓冲区缓存命中率 - 低于95% | **MAX** |
| DatabaseCursors | Warning | 4,000 | > | 游标数量 - 接近最大值4560 | **MAX** |
| DatabaseCursorsTimedOut | Info | 10 | > | 游标超时数量 - 应用未正确关闭游标 | **SUM** |
| DBClusterReplicaLagMaximum | Critical | 5,000 ms | > | 集群最大复制延迟 - 超过5秒 | **MAX** |

**AWS Recommendations:**
- CPUUtilization: 80% threshold
- DatabaseConnections: Max 30,000 (varies by instance size)
- BufferCacheHitRatio: < 95% indicates need to scale up
- DatabaseCursors: Max 4,560 per instance

**Note:** MAX statistic ensures we catch the worst-performing instance in the cluster.

---

## Application Load Balancer (ALB)

**Deployment Type:** Resource-Based  
**Total Alarms:** 18 per load balancer  
**Namespace:** `AWS/ApplicationELB`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| ActiveConnectionCount | Warning | 10,000 | > | 活跃连接数 | **MAX** |
| ActiveConnectionCount | Critical | 20,000 | > | 活跃连接数 | **MAX** |
| HTTPCode_Target_5XX_Count | Warning | 100 | > | 目标5XX错误 - 后端应用错误 | **SUM** |
| HTTPCode_Target_5XX_Count | Critical | 500 | > | 目标5XX错误 | **SUM** |
| HTTPCode_ELB_5XX_Count | Critical | 10 | > | ALB自身5XX错误 - 负载均衡器内部错误 | **SUM** |
| HTTPCode_ELB_4XX_Count | Warning | 100 | > | ALB自身4XX错误 - 客户端请求格式错误 | **SUM** |
| UnHealthyHostCount | Warning | 1 | ≥ | 不健康主机数 | **MAX** |
| UnHealthyHostCount | Critical | 2 | ≥ | 不健康主机数 | **MAX** |
| HealthyHostCount | Critical | 1 | < | 健康主机数 - 少于1个健康目标 | **MIN** |
| TargetResponseTime | Warning | 1 second | > | 目标响应时间 - 超过1秒 | **MAX** |
| TargetResponseTime | Critical | 3 seconds | > | 目标响应时间 - 超过3秒 | **MAX** |
| TargetConnectionErrorCount | Warning | 10 | > | 目标连接错误 - 无法连接到后端 | **SUM** |
| TargetConnectionErrorCount | Critical | 50 | > | 目标连接错误 | **SUM** |
| TargetTLSNegotiationErrorCount | Warning | 10 | > | 目标TLS协商错误 - SSL/TLS握手失败 | **SUM** |
| ProcessedBytes | Warning | 1,073,741,824 bytes | > | 处理字节数 - 超过1GB | **SUM** |
| ProcessedBytes | Critical | 5,368,709,120 bytes | > | 处理字节数 - 超过5GB | **SUM** |
| RejectedConnectionCount | Warning | 10 | > | 拒绝连接数 | **SUM** |
| RejectedConnectionCount | Critical | 50 | > | 拒绝连接数 | **SUM** |

**AWS Recommendations:**
- HTTPCode_ELB_5XX vs HTTPCode_Target_5XX: Distinguish ALB vs backend errors
- TargetResponseTime: Consider p90 percentile for better anomaly detection
- HealthyHostCount: Use MIN statistic to detect when ALL targets unhealthy
- TargetConnectionErrorCount: Critical for backend connectivity monitoring

**Note:** Error counts use SUM, health counts use MIN/MAX for appropriate detection.

---

## OpenSearch

**Deployment Type:** Resource-Based  
**Total Alarms:** 17 per domain  
**Namespace:** `AWS/ES`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| Shards.unassigned | Warning | 1 | ≥ | 未分配分片数 - 表示集群健康问题 | **MAX** |
| Shards.unassigned | Critical | 5 | ≥ | 未分配分片数 | **MAX** |
| Shards.activePrimary | Warning | 900 | > | 集群主分片数量 - 默认单节点分片1000 | **MAX** |
| Shards.activePrimary | Critical | 950 | > | 集群主分片数量 | **MAX** |
| ClusterStatus.green | Critical | 1 | < | 集群状态 - 绿色表示健康 | **MAX** |
| ClusterStatus.yellow | Warning | 1 | > | 集群状态 - 黄色表示部分不可用 | **MAX** |
| ClusterStatus.red | Critical | 1 | > | 集群状态 - 红色表示不可用 | **MAX** |
| CPUUtilization | Info | 70% | > | CPU使用率 | **MAX** |
| CPUUtilization | Warning | 80% | > | CPU使用率 | **MAX** |
| CPUUtilization | Critical | 90% | > | CPU使用率 | **MAX** |
| JVMMemoryPressure | Info | 70% | > | JVM内存压力 | **MAX** |
| JVMMemoryPressure | Warning | 80% | > | JVM内存压力 | **MAX** |
| JVMMemoryPressure | Critical | 90% | > | JVM内存压力 | **MAX** |
| MasterCPUUtilization | Warning | 80% | > | 主节点CPU使用率 | **MAX** |
| MasterCPUUtilization | Critical | 90% | > | 主节点CPU使用率 | **MAX** |
| MasterJVMMemoryPressure | Critical | 90% | > | 主节点JVM内存压力 | **MAX** |
| FreeStorageSpace | Warning | 20,480 MB | < | 可用存储空间 - 低于20GB | **MAX** |
| FreeStorageSpace | Critical | 10,240 MB | < | 可用存储空间 - 低于10GB | **MAX** |

**Key Metrics:**
- ClusterStatus: Most critical - monitors overall cluster health
- Shards.unassigned: Indicates cluster issues
- MasterNode metrics: Dedicated master node monitoring

**Note:** MAX statistic catches worst-case across all nodes in the domain.

---

## MSK (Kafka)

**Deployment Type:** Resource-Based  
**Total Alarms:** 21 per cluster  
**Namespace:** `AWS/Kafka`


| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| CpuUser | Info | 70% | > | Kafka CPU用户空间使用率 | **MAX** |
| CpuUser | Warning | 80% | > | Kafka CPU用户空间使用率 | **MAX** |
| CpuUser | Critical | 90% | > | Kafka CPU用户空间使用率 | **MAX** |
| MemoryUsed | Info | 6,442,450,944 bytes | > | Kafka内存使用 - 超过6GB | **MAX** |
| MemoryUsed | Warning | 7,516,192,768 bytes | > | Kafka内存使用 - 超过7GB | **MAX** |
| MemoryUsed | Critical | 8,589,934,592 bytes | > | Kafka内存使用 - 超过8GB | **MAX** |
| RootDiskUsed | Info | 70% | > | Kafka根磁盘使用率 | **MAX** |
| RootDiskUsed | Warning | 80% | > | Kafka根磁盘使用率 | **MAX** |
| RootDiskUsed | Critical | 90% | > | Kafka根磁盘使用率 | **MAX** |
| KafkaDataLogsDiskUsed | Info | 70% | > | Kafka数据磁盘使用率 | **MAX** |
| KafkaDataLogsDiskUsed | Warning | 80% | > | Kafka数据磁盘使用率 | **MAX** |
| KafkaDataLogsDiskUsed | Critical | 90% | > | Kafka数据磁盘使用率 | **MAX** |
| PartitionCount | Warning | 1,000 | > | 分区数量 | **MAX** |
| PartitionCount | Critical | 1,500 | > | 分区数量 | **MAX** |
| GlobalTopicCount | Warning | 500 | > | Topic总数 | **MAX** |
| GlobalTopicCount | Critical | 800 | > | Topic总数 | **MAX** |
| UnderReplicatedPartitions | Warning | 10 | > | 未充分备份的分区数 | **MAX** |
| UnderReplicatedPartitions | Critical | 50 | > | 未充分备份的分区数 | **MAX** |
| ZooKeeperRequestLatencyMsMean | Warning | 100 ms | > | ZooKeeper请求平均延迟 | **MAX** |
| ZooKeeperRequestLatencyMsMean | Critical | 200 ms | > | ZooKeeper请求平均延迟 | **MAX** |

**Key Metrics:**
- UnderReplicatedPartitions: Critical for data durability
- PartitionCount/TopicCount: Monitor cluster limits
- ZooKeeper latency: Indicates coordination issues

**Note:** MAX ensures we catch the worst-performing broker in the cluster.

---

## AmazonMQ (RabbitMQ)

**Deployment Type:** Resource-Based  
**Total Alarms:** 12 per broker  
**Namespace:** `AWS/AmazonMQ`

| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| SystemCpuUtilization | Info | 70% | > | RabbitMQ CPU使用率 | **MAX** |
| SystemCpuUtilization | Warning | 80% | > | RabbitMQ CPU使用率 | **MAX** |
| SystemCpuUtilization | Critical | 90% | > | RabbitMQ CPU使用率 | **MAX** |
| RabbitMQMemUsed | Info | 70% | > | RabbitMQ内存使用率百分比 | **MAX** |
| RabbitMQMemUsed | Warning | 80% | > | RabbitMQ内存使用率百分比 | **MAX** |
| RabbitMQMemUsed | Critical | 90% | > | RabbitMQ内存使用率百分比 | **MAX** |
| RabbitMQDiskFree | Warning | 2,147,483,648 bytes | < | 可用磁盘空间 - 低于2GB | **MAX** |
| RabbitMQDiskFree | Critical | 1,073,741,824 bytes | < | 可用磁盘空间 - 低于1GB | **MAX** |
| MessageCount | Warning | 100,000 | > | 消息总数 | **MAX** |
| MessageCount | Critical | 500,000 | > | 消息总数 | **MAX** |
| ConnectionCount | Warning | 1,000 | > | 连接数 | **MAX** |
| ConnectionCount | Critical | 2,000 | > | 连接数 | **MAX** |

**Note:** MAX catches the worst-case across all brokers.

---

## AWS WAF

**Deployment Type:** Resource-Based  
**Total Alarms:** 2 per WebACL  
**Namespace:** `AWS/WAFV2`

| Metric | Severity | Threshold | Operator | Description | Statistic |
|--------|----------|-----------|----------|-------------|-----------|
| BlockedRequests | Warning | 50 | > | WAF触发拦截机制 - 检测到异常流量被拦截 | Sum |
| AllowedRequests | Info | 10,000 | > | WAF允许的请求数 - 监控正常流量 | Sum |

---

## Severity Levels Explained

| Severity | Purpose | Response Time | Example Use Case |
|----------|---------|---------------|------------------|
| **Info** | Early warning | Monitor, no immediate action | CPU at 70% - trending up |
| **Warning** | Action needed soon | Investigate within hours | CPU at 80% - performance impact |
| **Critical** | Immediate action | Respond immediately | CPU at 90% - service degradation |

---

## Threshold Justification

### CPU Utilization
- **70% (Info):** Early warning, trending analysis
- **80% (Warning):** AWS recommended threshold, action needed
- **90% (Critical):** Performance degradation, immediate action

### Memory
- **< 1GB (Info):** Monitor memory pressure
- **< 512MB (Warning):** Significant memory pressure
- **< 256MB (Critical):** Risk of OOM, immediate action

### Latency
- **10ms (Warning):** Noticeable delay, investigate
- **20ms (Critical):** Significant performance impact

### Connections
- **Thresholds:** Based on max limits and typical usage patterns
- **DocumentDB:** Max 30,000 connections
- **Redis:** Max 65,000 connections per node

### Cache Hit Ratios
- **< 95% (Warning):** AWS recommendation for DocumentDB
- **< 0.8 (Warning):** Redis cache efficiency threshold
- **< 0.6 (Critical):** Severe cache inefficiency

---

## Statistic Types

**Default Statistic: MAX** (used for most metrics)

| Statistic | Use Case | Services Using It |
|-----------|----------|-------------------|
| **MAX** | Catches worst-case across resources | EC2, RDS, Redis, EFS, DocumentDB, OpenSearch, Kafka, RabbitMQ (most metrics) |
| **MIN** | Detects when ALL resources affected | RDS BurstBalance, ALB HealthyHostCount |
| **SUM** | Count-based metrics (errors, requests) | ALB error counts, WAF requests, DocumentDB cursor timeouts |

**Why MAX?**
- Tag-based alarms use `SELECT MAX()` with `GROUP BY` to monitor multiple resources
- MAX catches the worst-performing resource in the group
- Ensures no single resource issue goes undetected
- Example: If 10 EC2 instances, alarm triggers when ANY instance exceeds threshold

**Why SUM for errors?**
- Error counts should be totaled across the evaluation period
- Detects cumulative error rates
- Example: 100 5XX errors in 5 minutes indicates a problem

**Why MIN for health?**
- HealthyHostCount uses MIN to detect when NO healthy targets exist
- Ensures alarm triggers only when situation is critical across ALL availability zones

---

## Evaluation Periods

**Standard Configuration:**
- **Period:** 300 seconds (5 minutes) for most metrics
- **Period:** 60 seconds (1 minute) for status checks
- **Evaluation Periods:** 2 consecutive periods
- **TreatMissingData:** notBreaching (prevents false alarms)

**Why 2 periods?**
- Prevents false positives from transient spikes
- Confirms sustained issues
- Balances sensitivity vs noise

---

## Regional Considerations

**CloudWatch alarms are region-specific:**
- Deploy separately in each region
- SNS topics must be in same region as alarms
- Tag-based discovery works per-region
- Use same configuration across regions for consistency

---

## Cost Estimation

**Alarm Pricing:** $0.10 per alarm per month (first 10 free)

**Example Costs:**
- Tag-based stack (64 alarms): ~$5.40/month
- DocumentDB (27 alarms × 1 cluster): ~$2.70/month
- ALB (18 alarms × 1 LB): ~$1.80/month
- **Total for typical deployment:** ~$10-15/month

**ROI:** Minimal cost compared to preventing production outages.

---

## References

- [AWS CloudWatch Best Practice Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html)
- [DocumentDB Monitoring Guide](https://aws.amazon.com/blogs/database/monitoring-metrics-and-setting-up-alarms-on-your-amazon-documentdb-with-mongodb-compatibility-clusters/)
- [ALB CloudWatch Metrics](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html)
- [EC2 Status Checks](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html)
- [RDS Monitoring](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/monitoring-cloudwatch.html)

---

**Last Updated:** January 2026  
**Maintained by:** DevOps Team
