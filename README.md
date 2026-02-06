# AWS CloudWatch Alarms - Production-Grade Monitoring

Enterprise-ready CloudWatch alarm deployment system with AWS best practices. Hybrid architecture using tag-based alarms for scalability and resource-based alarms for specialized services.

## ⚡ Quick Start

```bash
# Deploy everything in one command
python deploy_alarms.py --mode all \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

**Safe to run multiple times** - Creates new stacks or updates existing ones (zero downtime, no deletion).

> `--tag-key`, `--tag-value`, and `--sns-topic` are all required for every deployment mode.

---

## 📊 What You Get

### Architecture Overview

```
Tag-Based Stack (1):
├─ 10 alarms for EC2, NAT Gateway, VPN
│  ├─ EC2: CPU, Memory*, Disk*, Inodes*, Status Checks (7 alarms)
│  ├─ NAT Gateway: Port Allocation Errors (1 alarm)
│  ├─ │  └─ VPN: Tunnel State - Connection & Tunnel level (2 alarms)
│
│  * Requires CloudWatch Agent installed on EC2 instances

Resource-Based Stacks (4):
├─ Kafka (MSK): 5 alarms per cluster (MaxOffsetLag, CPU, Memory, Disk, Controller)
├─ ACM: 1 alarm per certificate (DaysToExpiry)
├─ ALB: 1 alarm per load balancer (UnHealthyHostCount)
└─ Direct Connect: 3 alarms per connection (ConnectionState, Ingress/Egress Bandwidth)
```

### Key Features

- ✅ **CloudWatch Metrics Insights SQL** - Tag-based filtering for scalable monitoring
- ✅ **One Alarm Per Metric** - Warning severity tier, ready for future `_CRITICAL` additions
- ✅ **Math Expressions** - Computed metrics for Kafka memory and Direct Connect bandwidth
- ✅ **CWAgent Integration** - EC2 memory, disk, and inode monitoring
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

### CloudWatch Agent (Required for EC2 Memory/Disk Monitoring)

The following EC2 alarms require the CloudWatch Agent to be installed:
- `mem_used_percent` - Memory utilization
- `disk_used_percent` - Disk utilization  
- `disk_inodes_used_percent` - Inode utilization

**Install CloudWatch Agent:**
- [CloudWatch Agent Installation Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [CloudWatch Agent Configuration](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)

Without the CloudWatch Agent, these alarms will show `INSUFFICIENT_DATA` but will not trigger false alerts (configured with `TreatMissingData: notBreaching`).

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
python deploy_alarms.py --mode all \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

**Done!** Your infrastructure is now monitored.

---

## 📋 Monitored Services

### Tag-Based Services (3 services, 10 alarms)

Uses CloudWatch Metrics Insights SQL with tag filtering. One alarm monitors ALL tagged resources.

| Service | Alarms | Metrics | Namespace |
|---------|--------|---------|-----------|
| **EC2** | 7 | CPUUtilization (>90%), mem_used_percent* (>90%), disk_used_percent* (>90%), disk_inodes_used_percent* (>90%), StatusCheckFailed_System (>=1), StatusCheckFailed (>=1), StatusCheckFailed_Instance (>=1) | AWS/EC2, CWAgent |
| **NAT Gateway** | 1 | ErrorPortAllocation (>100) | AWS/NATGateway |
| **VPN** | 2 | TunnelState connection-level (<1), TunnelState tunnel-level (<1) | AWS/VPN |

*\* Requires CloudWatch Agent*

### Resource-Based Services (4 services)

Creates dedicated alarms for each discovered resource.

| Service | Alarms/Resource | Metrics |
|---------|-----------------|---------|
| **Kafka (MSK)** | 5 | MaxOffsetLag (>200000), CpuUser (>90%), MemoryPercent† (>90%), KafkaDataLogsDiskUsed (>75%), ActiveControllerCount (<1) |
| **ACM** | 1 | DaysToExpiry (<=30 days) |
| **ALB** | 1 | UnHealthyHostCount (>=1) |
| **Direct Connect** | 3 | ConnectionState (<1), IngressBandwidthPercent† (>90%), EgressBandwidthPercent† (>90%) |

*† Uses metric math expressions*

---

## 🔄 Usage Examples

### Deploy All Alarms

```bash
python deploy_alarms.py --mode all \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

### Deploy Tag-Based Alarms Only

Deploys EC2, NAT Gateway, and VPN alarms:

```bash
python deploy_alarms.py --mode tag-based \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

### Deploy Resource-Based Alarms

#### Kafka (MSK)

```bash
python deploy_alarms.py --mode resource-based \
  --service kafka --discover-all \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

#### ACM Certificates

```bash
python deploy_alarms.py --mode resource-based \
  --service acm --discover-all \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

#### Direct Connect

```bash
# Bandwidth is auto-detected from the AWS Direct Connect API
python deploy_alarms.py --mode resource-based \
  --service directconnect --discover-all \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

---

## 🎯 How It Works

### Tag-Based Alarms

Uses CloudWatch Metrics Insights with `GROUP BY` to monitor multiple resources with one alarm:

```sql
SELECT MAX(CPUUtilization) FROM "AWS/EC2" 
WHERE tag.Environment = 'Production' 
GROUP BY InstanceId ORDER BY MAX() DESC
```

**Benefits:**
- One alarm monitors ALL tagged resources
- Individual resource visibility (see which instance triggered)
- Automatic scaling (new resources auto-monitored)
- Cost-effective (1 alarm vs N alarms)

### Resource-Based Alarms

Creates dedicated alarms for each resource with support for:
- **Math Expressions** - Computed metrics (e.g., memory percentage from MemoryUsed and MemoryFree)
- **Multi-Dimension Metrics** - Alarms with multiple dimensions (e.g., Kafka MaxOffsetLag with Consumer Group and Topic)
- **Parameterized Calculations** - Bandwidth percentage with configurable capacity

---

### Alarm Naming Convention

All alarms use the `_WARNING` suffix to support future severity tiers:

```
{TagValue}-{Service}-{Resource}-{Metric}_WARNING
```

Examples:
- `Production-EC2-CPUUtilization_WARNING`
- `Production-MSK-mycluster-CpuUser_WARNING`
- `Production-DirectConnect-dxcon-abc123-ConnectionState_WARNING`

When adding critical-tier alarms later, use `_CRITICAL` with higher thresholds.

---

## 🔧 Configuration

### Modify Alarm Thresholds

Edit `alarm-config-resource-based.yaml`:

```yaml
services:
  kafka:
    alarms:
      - metric: CpuUser
        threshold: 90  # Change this
        operator: GreaterThanThreshold
```

Then redeploy:

```bash
python deploy_alarms.py --mode resource-based --service kafka \
  --tag-key Environment --tag-value Production --discover-all \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
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

**Q: Why do EC2 memory/disk alarms show INSUFFICIENT_DATA?**  
A: The CloudWatch Agent must be installed on EC2 instances to collect these metrics. See the [CloudWatch Agent Installation Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html).

---

## 📁 Files

| File | Description |
|------|-------------|
| `cloudformation-tag-based-alarms.yaml` | Tag-based CloudFormation template (10 alarms) |
| `alarm-config-resource-based.yaml` | Resource-based alarm configuration (Kafka, ACM, ALB, Direct Connect) |
| `deploy_alarms.py` | Main deployment script |
| `resource_alarm_builder.py` | Template builder for resource-based alarms |
| `METRICS_REFERENCE.md` | Detailed metrics reference with thresholds and descriptions |
| `README.md` | This file |

---

## 🏆 Best Practices

1. ✅ **Tag all resources** - Consistent tagging enables auto-discovery
2. ✅ **Install CloudWatch Agent** - Required for EC2 memory/disk monitoring
3. ✅ **One SNS topic per environment** - Separate prod/staging/dev notifications
4. ✅ **Deploy per region** - CloudWatch alarms are region-specific
5. ✅ **Test in dev first** - Validate before production
6. ✅ **Monitor INSUFFICIENT_DATA** - Indicates missing tags or CloudWatch Agent
7. ✅ **Review alarm history** - Tune thresholds based on actual workload

---

## 🌍 Multi-Region Deployment

CloudWatch alarms are region-specific. Deploy to each region:

```bash
# US East 1
python deploy_alarms.py --mode all \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:ACCOUNT:topic \
  --region us-east-1

# AP Southeast 2
python deploy_alarms.py --mode all \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:ap-southeast-2:ACCOUNT:topic \
  --region ap-southeast-2
```

---

## 🔗 Resources

- [AWS CloudWatch Best Practice Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html)
- [CloudWatch Metrics Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/query_with_cloudwatch-metrics-insights.html)
- [CloudWatch Agent Installation Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [Tag-Based Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingResourceTagsForTelemetry.html)

---

**Built with ❤️ for production reliability**
