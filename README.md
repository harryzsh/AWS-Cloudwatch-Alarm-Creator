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
Tag-Based Stack (1) + EKS EC2 Stacks:
├─ 64 alarms for EC2, RDS, Redis, EFS
│  ├─ EC2: CPU, Network, Status Checks (11 alarms)
│  ├─ RDS: CPU, Memory, Storage, IOPS, Latency, I/O Queue (25 alarms)
│  ├─ Redis: CPU, Memory, Connections, Evictions, Cache Hit Rate (19 alarms)
│  └─ EFS: Connections, IO Limit, Burst Credits (8 alarms)
└─ EKS EC2 Nodes: 11 alarms per EKS cluster (auto-discovered via eks:cluster-name tag)

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

## 📛 Alarm Naming Convention

All alarms use the prefix **`TSP-`** followed by the tag value, service, (resource id for resource-based), metric, and severity:

```
TSP-{TagValue}-{Service}-[{ResourceId}-]{Metric}-{Severity}
```

Examples:
- `TSP-EM-SNC-CLOUD-EC2-CPUUtilization-Critical`
- `TSP-EM-SNC-CLOUD-RDS-FreeStorageSpace-Warning`
- `TSP-EM-SNC-CLOUD-MSK-publicMSK-CpuUser-Warning`
- `TSP-EM-SNC-CLOUD-OpenSearch-mytestos-ClusterStatus.red-Critical`
- `TSP-EM-SNC-CLOUD-EKS-prod-cluster-EC2-StatusCheckFailed_System-Critical`

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
# Update tag-based alarms (EC2, RDS, Redis, EFS + EKS EC2 nodes)
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
| **EKS EC2** | Tag-Based | 11/cluster | CPU, Network, Status Checks (via eks:cluster-name) |
| **RDS** | Tag-Based | 25 | CPU, Memory, Storage, IOPS, Latency, I/O Queue |
| **Redis** | Tag-Based | 19 | CPU, Memory, Connections, Evictions, Cache Hit |
| **EFS** | Tag-Based | 8 | Connections, IO Limit, Burst Credits |
| **DocumentDB** | Resource | 27/cluster | CPU, Memory, IOPS, Cache Ratios, Cursors |
| **ALB** | Resource | 18/LB | Connections, Errors, Health, Response Time |
| **OpenSearch** | Resource | 17/domain | Cluster Health, Shards, CPU, Memory |
| **Kafka** | Resource | 21/cluster | CPU, Memory, Partitions, Replication |
| **RabbitMQ** | Resource | 12/broker | CPU, Memory, Messages, Connections |
| **WAF** | Resource | 2/WebACL | Blocked/Allowed Requests |

**📖 [View Complete Metrics Reference](METRICS_REFERENCE.md)** - Detailed thresholds, descriptions, and AWS recommendations for all metrics.

**All metrics verified against AWS official documentation**

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

Creates dedicated alarms for each resource using Metrics Insights SQL:

```sql
SELECT max(CPUUtilization) FROM "AWS/DocDB"
WHERE DBClusterIdentifier = 'my-cluster'
```

**Why Metrics Insights and not standard alarms?** Many service metrics publish
with multiple dimensions (e.g. MSK `CpuUser` uses `Cluster Name + Broker ID`
together). A standard alarm specifying only one of those dimensions would
match nothing. Metrics Insights aggregates across unspecified dimensions, so
one alarm per resource correctly covers all brokers/instances/shards.

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

**Q: I hit the "Metrics Insights alarm limit exceeded" error. What do I do?**
A: Resource-based alarms now emit as **standard CloudWatch alarms** (not Metrics
Insights), so they count against the 5000/region alarm quota, not the 200
Metrics Insights quota. The only alarms using Metrics Insights are the
tag-based ones (`cloudformation-tag-based-alarms.yaml` + EKS EC2 node alarms),
which need `GROUP BY tag.Name` to cover many resources with a single alarm.
That leaves plenty of headroom — expect ~75 Metrics Insights alarms max.

If you do hit the Metrics Insights limit despite that (possible with many EKS
clusters), request a Service Quotas increase on CloudWatch → "Number of Metrics
Insights alarms". Default 50, adjustable up to 200 via the console.

**Q: How do Kafka/DocDB per-broker/per-instance alarms work?**
A: These metrics publish with multiple dimensions (Cluster Name + Broker ID
for MSK, DBClusterIdentifier + DBInstanceIdentifier for DocDB). The deploy
script discovers those sub-resources and the generator fans out — one alarm
per (resource, sub-resource) pair for `scope: broker` / `scope: instance`
metrics, one alarm per resource for `scope: cluster` metrics. No Metrics
Insights needed.

---

## 🔄 Migration: Upgrading from the Metrics Insights version

If you previously deployed an older version of this project (which used Metrics
Insights SQL for resource-based alarms), upgrading is straightforward because
the stack names stay the same. CloudFormation detects the alarm resource
property changes and replaces the alarm types in-place.

**Steps:**

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Redeploy each resource-based stack. Use the same flags you used before:
   ```bash
   for svc in opensearch kafka rabbitmq waf docdb alb; do
     python deploy-cloudwatch-alarms.py --mode resource-based --service $svc \
       --tag-key businessTag --tag-value EM-SNC-CLOUD \
       --sns-topic arn:aws:sns:us-east-1:ACCOUNT:topic \
       --region us-east-1
   done
   ```

   For each stack CloudFormation will:
   - Delete old Metrics Insights–based alarms
   - Create new standard alarms with the same names
   - Keep SNS subscriptions on the topic intact

3. (Optional) Redeploy tag-based alarms to pick up the TSP- naming prefix:
   ```bash
   python deploy-cloudwatch-alarms.py --mode tag-based \
     --tag-key businessTag --tag-value EM-SNC-CLOUD \
     --sns-topic arn:aws:sns:us-east-1:ACCOUNT:topic \
     --region us-east-1
   ```

**What changes:**
- Resource-based alarm count may go up because per-broker (Kafka) and per-instance (DocDB) metrics now fan out into one alarm per broker/instance instead of one aggregated Metrics Insights alarm. This is the whole point of the change — standard alarms live on the 5000/region quota, Metrics Insights live on the 200/region quota.
- Alarm names still follow `TSP-{TagValue}-{Service}-{Resource}-...` convention. Kafka alarms add the broker ID: `TSP-EM-SNC-CLOUD-MSK-my-cluster-1-CpuUser-Critical`. DocDB instance-scope alarms add the instance ID.
- Alarm history resets for the replaced alarms (state reverts to `INSUFFICIENT_DATA` briefly, then settles).

**What stays the same:**
- SNS topic wiring — notifications continue to flow uninterrupted
- Tag-based alarms in `cloudformation-tag-based-alarms.yaml` (unchanged behavior, still use Metrics Insights by necessity)
- EKS EC2 node alarms (also still Metrics Insights)

**Quick verification after redeploy:**
```bash
aws cloudwatch describe-alarms --region us-east-1 \
  --alarm-name-prefix "TSP-" \
  --query "MetricAlarms[?Metrics != null] | length(@)" --output text
```
That number should equal the count of tag-based + EKS EC2 alarms only. Resource-based alarms have moved off Metrics Insights, so they will not show up in this query.

---

## 📁 Files

- `cloudformation-tag-based-alarms.yaml` - Tag-based template (64 alarms)
- `cloudformation-eks-ec2-alarms.yaml` - EKS EC2 node alarms template (11 alarms per cluster)
- `alarm-config-resource-based.yaml` - Resource-based config
- `deploy-cloudwatch-alarms.py` - Deployment script
- `generate-resource-alarms.py` - Resource-based template generator
- `METRICS_REFERENCE.md` - Complete metrics reference
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
