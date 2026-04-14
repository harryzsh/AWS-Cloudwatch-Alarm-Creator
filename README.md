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
│  ├─ EC2: CPU WARNING/CRITICAL, StatusCheckFailed_System CRITICAL, StatusCheckFailed_Instance CRITICAL, EBS Throughput WARNING, EBS IOPS WARNING (6 alarms)
│  ├─ NAT Gateway: ErrorPortAllocation WARNING, PacketsDropCount WARNING (2 alarms)
│  └─ VPN: TunnelState Connection CRITICAL, TunnelState Tunnel CRITICAL (2 alarms)

Resource-Based Stacks (7):
├─ EC2 (CWAgent): up to 4 alarms per instance (mem WARNING/CRITICAL, disk WARNING/CRITICAL)
├─ Kafka (MSK): up to 7 alarms per cluster (MaxOffsetLag WARNING/CRITICAL, CPU, HeapMemory, Disk WARNING/CRITICAL, Controller CRITICAL)
├─ ACM: 1 alarm per certificate (DaysToExpiry WARNING)
├─ ALB: 1 alarm per load balancer (UnHealthyHostCount WARNING)
├─ NLB: 1 alarm per load balancer (UnHealthyHostCount WARNING)
├─ Direct Connect: up to 5 alarms per connection (ConnectionState CRITICAL, Ingress/Egress WARNING/CRITICAL)
├─ EBS: 3 alarms per volume (ThroughputExceeded, IOPSExceeded, StalledIO WARNING)
├─ EFS: up to 2 alarms per file system (PercentIOLimit WARNING/CRITICAL)
└─ NAT: 2 alarms per gateway (PacketsDropCount, ErrorPortAllocation WARNING)

Bedrock Stack (1):
└─ Auto-discovered models: up to 7 alarms per model
   ├─ EstimatedTPMQuotaUsage WARNING/CRITICAL (token count, set to TPM quota × 80%/90%)
   ├─ InvocationClientErrors WARNING/CRITICAL
   ├─ Invocations WARNING
   └─ TimeToFirstToken WARNING/CRITICAL (streaming only, ms)
```

Note: EC2 CWAgent alarms are auto-deployed with both `--mode tag-based` and `--mode all`.

### Key Features

- ✅ **CloudWatch Metrics Insights SQL** - Tag-based filtering for scalable monitoring
- ✅ **WARNING/CRITICAL severity tiers** - Dual severity support with `-WARNING` and `-CRITICAL` suffixes
- ✅ **OKActions** - Notified on both alarm trigger and recovery
- ✅ **Math Expressions** - Computed metrics for Direct Connect bandwidth
- ✅ **CWAgent Integration** - Per-instance EC2 memory, disk, and inode monitoring
- ✅ **Stable CloudFormation IDs** - Hash-based logical IDs prevent update collisions

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

EC2 memory and disk alarms are deployed as resource-based alarms per instance (not tag-based, since CWAgent doesn't support tag filtering in Metrics Insights). They are auto-discovered and deployed alongside the tag-based stack. Instances without CWAgent are automatically skipped — no manual filtering needed.

Required metrics: `mem_used_percent`, `disk_used_percent` (WARNING >85%, CRITICAL >95%)

**Install CloudWatch Agent:**
- [CloudWatch Agent Installation Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

Without the CloudWatch Agent, these alarms will show `INSUFFICIENT_DATA` but will not trigger false alerts (`TreatMissingData: notBreaching`).

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

| Service | Alarms | Metrics | Severity |
|---------|--------|---------|----------|
| **EC2** | 6 | CPUUtilization, StatusCheckFailed_System, StatusCheckFailed_Instance, InstanceEBSThroughputExceededCheck, InstanceEBSIOPSExceededCheck | CPU: WARNING(>90%) + CRITICAL(>98%); Status checks: CRITICAL(≥1); EBS: WARNING(≥1) |
| **NAT Gateway** | 2 | ErrorPortAllocation, PacketsDropCount | WARNING(>100) |
| **VPN** | 2 | TunnelState connection-level, TunnelState tunnel-level | CRITICAL(<1) |

### Resource-Based Services (9 services)

Creates dedicated alarms per discovered resource. EC2 CWAgent is auto-deployed alongside tag-based.

| Service | Alarms/Resource | Metrics | WARNING | CRITICAL |
|---------|-----------------|---------|---------|----------|
| **EC2 (CWAgent)** | up to 4 | mem_used_percent, disk_used_percent | >85% | >95% |
| **Kafka (MSK)** | up to 7 | MaxOffsetLag, CpuUser, HeapMemoryAfterGC, KafkaDataLogsDiskUsed, ActiveControllerCount | MaxOffsetLag >200,000; CPU/Heap >90%; Disk >75% | MaxOffsetLag >500,000; Disk >86%; Controller <1 |
| **ACM** | 1 | DaysToExpiry | ≤30 days | — |
| **ALB** | 1 | UnHealthyHostCount | ≥1 | — |
| **NLB** | 1 | UnHealthyHostCount | ≥1 | — |
| **Direct Connect** | up to 5 | ConnectionState, IngressBandwidthPercent, EgressBandwidthPercent | Bandwidth >80% | ConnectionState <1; Bandwidth >90% |
| **EBS** | 3 | VolumeThroughputExceededCheck, VolumeIOPSExceededCheck, VolumeStalledIOCheck | ≥1 | — |
| **EFS** | up to 2 | PercentIOLimit | >85% | >95% |
| **NAT (resource)** | 2 | PacketsDropCount, ErrorPortAllocation | >100 | — |

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
  --service kafka \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

#### ACM Certificates

```bash
python deploy_alarms.py --mode resource-based \
  --service acm \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

#### Direct Connect

```bash
# Bandwidth is auto-detected from the AWS Direct Connect API
python deploy_alarms.py --mode resource-based \
  --service directconnect \
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

All alarms use `-WARNING` or `-CRITICAL` suffix:

```
{TagValue}-{Service}-{Resource}-{Metric}-WARNING
{TagValue}-{Service}-{Resource}-{Metric}-CRITICAL
```

Examples:
- `Production-EC2-CPUUtilization-WARNING`
- `Production-EC2-CPUUtilization-CRITICAL`
- `Production-MSK-mycluster-CpuUser-WARNING`
- `Production-DirectConnect-dxcon-abc123-ConnectionState-CRITICAL`

---

## 🤖 Bedrock Alarm Configuration

Bedrock alarms are automatically included in `--mode all`. They use **auto-discovery + YAML overrides**.

### How It Works

1. Auto-discovers all ModelIds with active CloudWatch data in `AWS/Bedrock`
2. Applies default thresholds to all discovered models
3. Models listed in `alarm-config-bedrock.yaml` overrides use custom thresholds instead
4. No duplicates — override always wins

### Default Alarms (applied to every discovered model)

| Metric | WARNING | CRITICAL | Statistic | Description |
|--------|---------|----------|-----------|-------------|
| `EstimatedTPMQuotaUsage` | >80,000* | >90,000* | Sum/60s | TPM配额使用率（token count，需按实际quota调整） |
| `InvocationClientErrors` | ≥5/5min | ≥20/5min | Sum | 调用错误（含throttling 429） |
| `Invocations` | >1000/5min | — | Sum | 异常调用量保护 |
| `TimeToFirstToken` | >3000ms | >5000ms | Average | 首Token延迟（仅streaming API） |

*`EstimatedTPMQuotaUsage` 阈值需按实际 TPM quota 调整，见下方说明。

### Customize Per-Model Thresholds

**EstimatedTPMQuotaUsage** — threshold is in raw token count (not %). Calculate from your TPM quota:

```bash
# Find your TPM quota for a model
aws service-quotas list-service-quotas --service-code bedrock --region us-east-1 \
  --query "Quotas[?contains(QuotaName,'Sonnet 4.6')].{Name:QuotaName,Value:Value}"
# Example result: 6,000,000 TPM
# threshold_warning  = 6,000,000 × 80% = 4,800,000
# threshold_critical = 6,000,000 × 90% = 5,400,000
```

**TimeToFirstToken** — recommended baselines by model tier:

| Model tier | WARNING | CRITICAL |
|------------|---------|----------|
| Fast (Haiku, Nova Micro) | >2000ms | >4000ms |
| Mid (Sonnet, Nova Lite) | >3000ms | >5000ms |
| Large (Opus, Nova Pro) | >5000ms | >8000ms |

Edit `alarm-config-bedrock.yaml` and add entries under `overrides`:

```yaml
overrides:
  - model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    alarms:
      - metric: EstimatedTPMQuotaUsage
        threshold_warning: 70        # stricter than default 80%
        threshold_critical: 85
        operator: GreaterThanThreshold
        period: 60
        evaluation_periods: 3
        description: Claude 3.5 Sonnet TPM配额使用率

      - metric: InvocationClientErrors
        threshold_warning: 2
        threshold_critical: 10
        operator: GreaterThanOrEqualToThreshold
        period: 300
        evaluation_periods: 2
        description: Claude 3.5 Sonnet调用错误
```

> **Note:** Override is a full replacement — if you only list one metric in overrides, that model only gets one alarm. Other metrics won't inherit from defaults.

### Deploy Bedrock Alarms Only

```bash
python deploy_alarms.py --mode resource-based --service bedrock \
  --tag-key Environment --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:YOUR_ACCOUNT:cloudwatchTopic \
  --region us-east-1
```

### Monitored Metrics

| Metric | Namespace | Statistic | Unit | Notes |
|--------|-----------|-----------|------|-------|
| `EstimatedTPMQuotaUsage` | AWS/Bedrock | Sum | Count (tokens) | Period=60s, Sum=TPM consumed |
| `InvocationClientErrors` | AWS/Bedrock | Sum | Count | Includes throttling 429 |
| `Invocations` | AWS/Bedrock | Sum | Count | Total calls per period |
| `TimeToFirstToken` | AWS/Bedrock | Average | Milliseconds | Streaming APIs only |

---

## 🔧 Configuration

### Modify Alarm Thresholds

Edit `alarm-config-resource-based.yaml`:

```yaml
services:
  kafka:
    alarms:
      - metric: CpuUser
        threshold_warning: 90   # Change WARNING threshold
        # threshold_critical: 95  # Optionally add CRITICAL threshold
        operator: GreaterThanThreshold
```

Then redeploy:

```bash
python deploy_alarms.py --mode resource-based --service kafka \
  --tag-key Environment --tag-value Production \
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
| `alarm-config-bedrock.yaml` | Bedrock alarm configuration (defaults + per-model overrides) |
| `deploy_alarms.py` | Main deployment script |
| `resource_alarm_builder.py` | Template builder for resource-based alarms |
| `bedrock_alarm_builder.py` | Template builder for Bedrock alarms (auto-discover + overrides) |
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
