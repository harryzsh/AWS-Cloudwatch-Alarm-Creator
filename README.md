# AWS CloudWatch Alarms - Production-Grade Monitoring

Enterprise-ready CloudWatch alarm deployment system with AWS best practices. Hybrid architecture using tag-based alarms for scalability and resource-based alarms for specialized services.

## ⚡ Quick Start

```bash
# Deploy everything in one command
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**Safe to run multiple times** - Creates new stacks or updates existing ones (zero downtime, no deletion).

---

## 📊 What You Get

### Architecture Overview

```
Tag-Based Stack (1):
└─ 64 alarms for EC2, RDS, Redis, EFS
   ├─ EC2: CPU, Network, Status Checks (11 alarms)
   ├─ RDS: CPU, Memory, Storage, IOPS, Latency, I/O Queue (25 alarms)
   ├─ Redis: CPU, Memory, Connections, Evictions, Cache Hit Rate (19 alarms)
   └─ EFS: Connections, IO Limit, Burst Credits (8 alarms)

Resource-Based Stacks (6):
├─ DocumentDB: 27 alarms per cluster (cache ratios, cursors, replication)
├─ ALB: 18 alarms per load balancer (errors, connections, health)
├─ OpenSearch: 17 alarms per domain (cluster health, shards, performance)
├─ Kafka: 21 alarms per cluster (CPU, memory, partitions, replication)
├─ RabbitMQ: 12 alarms per broker (CPU, memory, messages, connections)
└─ WAF: 2 alarms per WebACL (blocked/allowed requests)
```

### Production Enhancements (Jan 2026)

Based on AWS official documentation and best practices:

- ✅ **EC2 Status Checks** - Detect infrastructure failures
- ✅ **RDS I/O Monitoring** - DiskQueueDepth, BurstBalance
- ✅ **DocumentDB Cache Metrics** - BufferCacheHitRatio, Cursors
- ✅ **ALB Error Source ID** - Distinguish ALB vs target errors
- ✅ **Multi-Severity Levels** - Info, Warning, Critical
- ✅ **Individual Resource Visibility** - See which specific resource triggered

---

## 🚀 Installation

### Prerequisites

```bash
# Install dependencies
pip install boto3 pyyaml

# Configure AWS credentials
aws configure
```

### Deploy

```bash
# 1. Create SNS topic (one-time)
aws sns create-topic --name cloudwatchTopic --region us-east-1

# 2. Subscribe to notifications
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1

# 3. Deploy all alarms
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

**Done!** Your infrastructure is now monitored.

---

## 🔄 Updates

### Update All Stacks

**Re-run the same command** to apply configuration changes:

```bash
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**What happens:**
- ✅ Adds new alarms from updated config
- ✅ Keeps existing alarms running
- ✅ Updates modified thresholds
- ✅ Zero downtime
- ✅ Auto-rollback on failure

### Update Individual Services

```bash
# Update only tag-based alarms (EC2, RDS, Redis, EFS)
python deploy-cloudwatch-alarms.py --mode tag-based \
  --tag-key businessTag --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1

# Update specific service
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service docdb --discover-all \
  --tag-key businessTag --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**Supported services:** `opensearch`, `kafka`, `rabbitmq`, `waf`, `docdb`, `alb`

---

## 📋 Monitored Services

| Service | Type | Alarms | Key Metrics |
|---------|------|--------|-------------|
| **EC2** | Tag-Based | 11 | CPU, Network, Status Checks |
| **RDS** | Tag-Based | 25 | CPU, Memory, Storage, IOPS, Latency, I/O Queue |
| **Redis** | Tag-Based | 19 | CPU, Memory, Connections, Evictions, Cache Hit |
| **EFS** | Tag-Based | 8 | Connections, IO Limit, Burst Credits |
| **DocumentDB** | Resource | 27/cluster | CPU, Memory, IOPS, Cache Ratios, Cursors |
| **ALB** | Resource | 18/LB | Connections, Errors, Health, Response Time |
| **OpenSearch** | Resource | 17/domain | Cluster Health, Shards, CPU, Memory |
| **Kafka** | Resource | 21/cluster | CPU, Memory, Partitions, Replication |
| **RabbitMQ** | Resource | 12/broker | CPU, Memory, Messages, Connections |
| **WAF** | Resource | 2/WebACL | Blocked/Allowed Requests |

**All metrics verified against AWS official documentation**

<details>
<summary><b>View Detailed Metrics</b></summary>

### EC2 (11 alarms)
- CPUUtilization: Info (85%), Warning (90%), Critical (95%)
- NetworkIn/Out: Info (150MB), Warning (300MB)
- StatusCheckFailed: Critical (≥ 1)
- StatusCheckFailed_System: Critical (≥ 1)
- StatusCheckFailed_Instance: Critical (≥ 1)
- StatusCheckFailed_AttachedEBS: Critical (≥ 1)

### RDS (25 alarms)
- DatabaseConnections: Info (100), Warning (200), Critical (300)
- CPUUtilization: Info (70%), Warning (80%), Critical (90%)
- FreeableMemory: Info (1GB), Warning (512MB), Critical (256MB)
- FreeStorageSpace: Info (10GB), Warning (5GB), Critical (2GB)
- ReadIOPS/WriteIOPS: Warning (10000), Critical (20000)
- ReadLatency/WriteLatency: Warning (10ms), Critical (20ms)
- ReplicaLag: Warning (30s), Critical (60s)
- DiskQueueDepth: Warning (10), Critical (20)
- BurstBalance: Warning (< 20%)

### DocumentDB (27 alarms)
- CPUUtilization: Info (70%), Warning (80%), Critical (90%)
- DatabaseConnections: Info (100), Warning (200), Critical (300)
- FreeableMemory: Info (1GB), Warning (512MB), Critical (256MB)
- ReadIOPS/WriteIOPS: Warning (5000), Critical (10000)
- ReadLatency/WriteLatency: Warning (10ms), Critical (20ms)
- DBInstanceReplicaLag: Warning (1s), Critical (5s)
- VolumeBytesUsed: Info (100GB), Warning (150GB)
- BufferCacheHitRatio: Warning (< 95%)
- IndexBufferCacheHitRatio: Warning (< 95%)
- DatabaseCursors: Warning (> 4000)
- DatabaseCursorsTimedOut: Info (> 10)
- DBClusterReplicaLagMaximum: Critical (> 5s)

### ALB (18 alarms)
- ActiveConnectionCount: Warning (10000), Critical (20000)
- HTTPCode_Target_5XX_Count: Warning (100), Critical (500)
- HTTPCode_ELB_5XX_Count: Critical (10)
- HTTPCode_ELB_4XX_Count: Warning (100)
- UnHealthyHostCount: Warning (≥ 1), Critical (≥ 2)
- HealthyHostCount: Critical (< 1)
- TargetResponseTime: Warning (1s), Critical (3s)
- TargetConnectionErrorCount: Warning (10), Critical (50)
- TargetTLSNegotiationErrorCount: Warning (10)
- ProcessedBytes: Warning (1GB), Critical (5GB)
- RejectedConnectionCount: Warning (10), Critical (50)

</details>

---

## 🎯 How It Works

### Tag-Based Alarms

Uses CloudWatch Metrics Insights with `GROUP BY` to monitor multiple resources with one alarm:

```sql
SELECT MAX(CPUUtilization) FROM "AWS/EC2" 
WHERE tag.businessTag = 'EM-SNC-CLOUD' 
GROUP BY tag.Name
```

**Benefits:**
- One alarm monitors ALL tagged resources
- Individual resource visibility (see which instance triggered)
- Automatic scaling (new resources auto-monitored)
- Cost-effective (1 alarm vs N alarms)

### Resource-Based Alarms

Creates dedicated alarms for each resource:

```sql
SELECT MAX(CPUUtilization) FROM "AWS/DocDB" 
WHERE DBClusterIdentifier = 'my-cluster'
```

**Use for:**
- Services without tag-based telemetry support
- Resources needing granular control
- Specialized metrics (OpenSearch shards, Kafka partitions)

---

## 🔧 Configuration

### Modify Alarm Thresholds

Edit `alarm-config-resource-based.yaml`:

```yaml
services:
  docdb:
    alarms:
      - metric: CPUUtilization
        severity: Warning
        threshold: 80  # Change this
        operator: GreaterThanThreshold
```

Then redeploy:

```bash
python deploy-cloudwatch-alarms.py --mode resource-based --service docdb \
  --tag-key businessTag --tag-value EM-SNC-CLOUD --discover-all \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

### Add New Metrics

1. Add metric to `alarm-config-resource-based.yaml`
2. Run deployment command
3. New alarms automatically created

---

## ❓ FAQ

**Q: Will updates delete my existing alarms?**  
A: No! CloudFormation updates are additive. Existing alarms stay active.

**Q: How do I update stacks?**  
A: Re-run the same deployment command. It auto-detects and updates.

**Q: What if I add new resources?**  
A: Just redeploy. Auto-discovery finds and monitors new tagged resources.

**Q: Can I update one service?**  
A: Yes! Use `--mode resource-based --service <name>`.

**Q: Is it safe to run daily?**  
A: Yes! Updates are idempotent and zero-downtime.

---

## 📁 Files

- `cloudformation-tag-based-alarms.yaml` - Tag-based template (64 alarms)
- `alarm-config-resource-based.yaml` - Resource-based config
- `deploy-cloudwatch-alarms.py` - Deployment script
- `generate-resource-alarms-simple.py` - Template generator
- `ARCHITECTURE_REVIEW.md` - Production readiness assessment
- `README.md` - This file

---

## 🏆 Best Practices

1. ✅ **Tag all resources** - Consistent tagging enables auto-discovery
2. ✅ **One SNS topic per environment** - Separate prod/staging/dev notifications
3. ✅ **Deploy per region** - CloudWatch alarms are region-specific
4. ✅ **Test in dev first** - Validate before production
5. ✅ **Monitor INSUFFICIENT_DATA** - Indicates missing tags
6. ✅ **Review alarm history** - Tune thresholds based on actual workload
7. ✅ **Update regularly** - Apply new metrics and threshold adjustments

---

## 📚 Documentation

- **Architecture Review:** See `ARCHITECTURE_REVIEW.md` for detailed production readiness assessment
- **AWS Best Practices:** All metrics validated against official AWS documentation
- **Threshold Justification:** Based on AWS recommended values

---

## 🌍 Multi-Region Deployment

CloudWatch alarms are region-specific. Deploy to each region:

```bash
# US East 1
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:ACCOUNT:topic \
  --region us-east-1

# AP Southeast 2
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:ap-southeast-2:ACCOUNT:topic \
  --region ap-southeast-2
```

---

## 🤝 Contributing

1. Fork the repository
2. Make your changes
3. Test in dev environment
4. Submit pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🔗 Resources

- [AWS CloudWatch Best Practice Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html)
- [CloudWatch Metrics Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html)
- [Tag-Based Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingResourceTagsForTelemetry.html)

---

**Built with ❤️ for production reliability**
