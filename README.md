# AWS CloudWatch Alarms - Tag-Based + Resource-Based Hybrid

Optimized CloudWatch alarm deployment system with correct AWS metrics. Uses tag-based alarms with GROUP BY for individual resource visibility.

## 🎯 Architecture

```
Tag-Based Stack (1):
└─ tag-based-alarms → 64 alarms for ALL tagged resources
   ├─ EC2 (11 alarms) - CPU, Network, Status Checks
   ├─ RDS (25 alarms) - CPU, Memory, Storage, IOPS, Latency, Connections, DiskQueue, BurstBalance
   ├─ ElastiCache Redis (19 alarms) - CPU, Memory, Connections, Evictions, Cache Hit Rate
   └─ EFS (8 alarms) - Connections, IO Limit, Burst Credits

Resource-Based Stacks (6):
├─ opensearch-alarms (N × 17 alarms per domain)
├─ kafka-alarms (N × 21 alarms per cluster)
├─ rabbitmq-alarms (N × 12 alarms per broker)
├─ docdb-alarms (N × 27 alarms per cluster) - Enhanced with cache hit ratios, cursors
├─ alb-alarms (N × 18 alarms per load balancer) - Enhanced with ELB errors, connection errors
└─ waf-alarms (N × 2 alarms per WebACL)

Total: 7 stacks with production-grade monitoring
```

## 📊 Key Benefits

- **Individual Resource Visibility**: Each alarm shows which specific instance/cluster triggered
- **Correct AWS Metrics**: All metrics verified against official AWS documentation
- **Automatic Scaling**: New resources auto-monitored via tags
- **GROUP BY Support**: One alarm monitors multiple resources with separate states
- **Required SNS**: All alarms require SNS topic for notifications
- **S3 Auto-Upload**: Large templates automatically uploaded to S3

## 🌍 Regional Deployment

**CloudWatch alarms are region-specific.** Deploy once per region where you have resources. Use the `--region` flag to specify your target region (default: us-east-1).

---

## 🚀 Quick Start

### TL;DR - Deploy Everything

```bash
# One command to deploy/update ALL stacks
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**This command is safe to run multiple times:**
- First run: Creates all stacks
- Subsequent runs: Updates existing stacks (adds new alarms, no deletion)
- Zero downtime updates

---

### 1. Prerequisites

```bash
# Enable resource tags for telemetry (one-time per region)
aws cloudwatch put-managed-insight-rules \
  --managed-rules Identifier=arn:aws:cloudwatch:us-east-1::insight-rule/aws/resource-tags \
  --region us-east-1

# Install dependencies
pip install boto3 pyyaml aws-cdk-lib

# Tag your resources
aws ec2 create-tags --resources i-123 i-456 \
  --tags Key=Environment,Value=Production
```

### 2. Create SNS Topic for Alarm Notifications (Required)

**⚠️ Important:** Without an SNS topic, alarms will be created but won't send notifications!

```bash
# Create SNS topic
aws sns create-topic --name cloudwatch-alarms-uat --region ap-southeast-2

# Output: 
# {
#     "TopicArn": "arn:aws:sns:ap-southeast-2:476114114317:cloudwatch-alarms-uat"
# }

# Subscribe your email to receive notifications
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-southeast-2:476114114317:cloudwatch-alarms-uat \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region ap-southeast-2

# Check your email and confirm the subscription!
```

**Other notification options:**
```bash
# SMS notifications
aws sns subscribe --topic-arn <topic-arn> --protocol sms --notification-endpoint +1234567890

# Slack/webhook (via HTTPS endpoint)
aws sns subscribe --topic-arn <topic-arn> --protocol https --notification-endpoint https://hooks.slack.com/...

# Lambda function
aws sns subscribe --topic-arn <topic-arn> --protocol lambda --notification-endpoint arn:aws:lambda:...

# SQS queue
aws sns subscribe --topic-arn <topic-arn> --protocol sqs --notification-endpoint arn:aws:sqs:...
```

**Verify subscriptions:**
```bash
aws sns list-subscriptions-by-topic --topic-arn <topic-arn> --region ap-southeast-2
```

### 3. Deploy Tag-Based Alarms

**Required Parameters:**
- `--sns-topic` (REQUIRED) - SNS Topic ARN for alarm notifications
- `--tag-key` (optional, default: "Environment") - Tag key to filter resources
- `--tag-value` (optional, default: "Production") - Tag value to filter resources

**How It Works:**
Each alarm uses CloudWatch Metrics Insights with GROUP BY to create separate alarm states for each resource:
- **EC2:** Grouped by instance Name tag (only monitors instances with Name tag)
- **RDS:** Grouped by DBInstanceIdentifier
- **ElastiCache:** Grouped by CacheClusterId
- **EFS:** Grouped by FileSystemId

This means ONE alarm definition monitors ALL matching resources, but you can see which specific resource triggered the alarm.

```bash
# Deploy with defaults (Environment=Production)
python deploy-cloudwatch-alarms.py \
  --mode tag-based \
  --sns-topic arn:aws:sns:ap-southeast-2:476114114317:cloudwatch-alarms-prod \
  --region ap-southeast-2

# Deploy for UAT environment
python deploy-cloudwatch-alarms.py \
  --mode tag-based \
  --tag-value uat \
  --sns-topic arn:aws:sns:ap-southeast-2:476114114317:cloudwatch-alarms-uat \
  --region ap-southeast-2

# Deploy with custom tag
python deploy-cloudwatch-alarms.py \
  --mode tag-based \
  --tag-key Team \
  --tag-value DataEngineering \
  --sns-topic arn:aws:sns:ap-southeast-2:476114114317:cloudwatch-alarms-team \
  --region ap-southeast-2
```

**Creates ONE stack with 64 alarms** monitoring ALL resources with matching tags. Each alarm shows individual resource states.

**Enhanced for Production:**
- ✅ EC2 status checks for infrastructure health
- ✅ RDS I/O bottleneck detection
- ✅ RDS burst balance monitoring (gp2 volumes)

### 4. Deploy Resource-Based Alarms

```bash
# Auto-discover OpenSearch domains
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service opensearch --discover-all \
  --region us-east-1

# Deploy for specific Kafka clusters
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service kafka \
  --resources prod-kafka-cluster staging-kafka-cluster \
  --region us-east-1
```

### 5. Deploy Everything (Recommended)

**Deploy all stacks in one command** - tag-based + all resource-based services:

```bash
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**What this does:**
- ✅ Deploys/updates tag-based alarms (EC2, RDS, Redis, EFS)
- ✅ Auto-discovers and deploys/updates all resource-based services (DocumentDB, ALB, OpenSearch, Kafka, RabbitMQ, WAF)
- ✅ Skips services with no tagged resources
- ✅ **Updates existing stacks** (no deletion, zero downtime)
- ✅ Creates new stacks for newly tagged resources

**Output:** Creates or updates up to 7 CloudFormation stacks automatically

---

## 🔄 Updating Existing Stacks

### Update All Stacks (Recommended)

**To apply configuration changes to all existing stacks**, simply re-run the same deployment command:

```bash
# This will UPDATE all existing stacks with new alarms (no deletion!)
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**CloudFormation Update Behavior:**
- ✅ **Adds new alarms** from updated configuration
- ✅ **Keeps existing alarms** running
- ✅ **Modifies changed alarms** (threshold updates, etc.)
- ✅ **Zero downtime** - monitoring continues during update
- ✅ **Automatic rollback** if update fails

### Update Individual Stacks

**Update only tag-based alarms:**
```bash
python deploy-cloudwatch-alarms.py --mode tag-based \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**Update specific resource-based service:**
```bash
# Update DocumentDB alarms
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service docdb \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --discover-all \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1

# Update ALB alarms
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service alb \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --discover-all \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

### When to Update

**Update your stacks when:**
- ✅ Adding new metrics to `alarm-config-resource-based.yaml`
- ✅ Changing alarm thresholds
- ✅ Adding new tagged resources (auto-discovered)
- ✅ Applying production enhancements
- ✅ Changing SNS topic

**The script automatically:**
- Detects if stack exists → **Updates** it
- Stack doesn't exist → **Creates** it
- No changes needed → Skips update

---

## 📋 Service Support Matrix

| Service | Tag-Based | Alarms | Stack Type | Production Ready |
|---------|-----------|--------|------------|------------------|
| **EC2** | ✅ YES | 11 | tag-based-alarms | ✅ Enhanced with status checks |
| **RDS** | ✅ YES | 25 | tag-based-alarms | ✅ Enhanced with I/O monitoring |
| **ElastiCache Redis** | ✅ YES | 19 | tag-based-alarms | ✅ Complete coverage |
| **EFS** | ✅ YES | 8 | tag-based-alarms | ✅ Complete coverage |
| **ALB** | ❌ NO | 18 per LB | alb-alarms | ✅ Enhanced with ELB errors |
| **DocumentDB** | ❌ NO | 27 per cluster | docdb-alarms | ✅ Enhanced with cache metrics |
| **OpenSearch** | ❌ NO | 17 per domain | opensearch-alarms | ✅ Complete coverage |
| **MSK (Kafka)** | ❌ NO | 21 per cluster | kafka-alarms | ✅ Complete coverage |
| **AmazonMQ (RabbitMQ)** | ❌ NO | 12 per broker | rabbitmq-alarms | ✅ Complete coverage |
| **WAF** | ❌ NO | 2 per WebACL | waf-alarms | ✅ Basic coverage |

### Detailed Metrics by Service

**All metrics verified against official AWS CloudWatch documentation**

<details>
<summary><b>EC2 (11 alarms) - PRODUCTION ENHANCED</b></summary>

- **CPUUtilization**: Info (85%), Warning (90%), Critical (95%)
- **NetworkIn**: Info (150MB), Warning (300MB)
- **NetworkOut**: Info (150MB), Warning (300MB)
- **StatusCheckFailed**: Critical (≥ 1) - Overall status check
- **StatusCheckFailed_System**: Critical (≥ 1) - AWS infrastructure issues
- **StatusCheckFailed_Instance**: Critical (≥ 1) - Instance configuration issues
- **StatusCheckFailed_AttachedEBS**: Critical (≥ 1) - EBS volume connectivity issues

**New Additions:** Status check monitoring prevents undetected infrastructure failures

</details>

<details>
<summary><b>RDS (25 alarms - MySQL & PostgreSQL) - PRODUCTION ENHANCED</b></summary>

**Unified alarms work for both MySQL and PostgreSQL**

- **DatabaseConnections**: Info (100), Warning (200), Critical (300)
- **CPUUtilization**: Info (70%), Warning (80%), Critical (90%)
- **FreeableMemory**: Info (1GB free), Warning (512MB free), Critical (256MB free)
- **FreeStorageSpace**: Info (10GB free), Warning (5GB free), Critical (2GB free)
- **ReadIOPS**: Warning (10000), Critical (20000)
- **WriteIOPS**: Warning (10000), Critical (20000)
- **ReadLatency**: Warning (10ms), Critical (20ms)
- **WriteLatency**: Warning (10ms), Critical (20ms)
- **ReplicaLag**: Warning (30s), Critical (60s) - Only for read replicas
- **DiskQueueDepth**: Warning (10), Critical (20) - I/O bottleneck detection
- **BurstBalance**: Warning (< 20%) - GP2 IOPS credit monitoring

**New Additions:** I/O bottleneck detection and burst balance monitoring

**Note:** Adjust thresholds based on your RDS instance size and workload.

</details>

<details>
<summary><b>ElastiCache Redis (19 alarms)</b></summary>

- **EngineCPUUtilization**: Info (70%), Warning (80%), Critical (90%) - Redis engine CPU
- **DatabaseMemoryUsagePercentage**: Info (70%), Warning (80%), Critical (90%)
- **CurrConnections**: Info (5000), Warning (8000), Critical (10000)
- **Evictions**: Warning (1000), Critical (5000) - Keys evicted due to memory pressure
- **CacheHitRate**: Warning (< 0.8), Critical (< 0.6) - Lower is worse
- **ReplicationLag**: Warning (30s), Critical (60s)
- **NetworkBytesIn**: Warning (150MB), Critical (300MB)
- **NetworkBytesOut**: Warning (150MB), Critical (300MB)

</details>

<details>
<summary><b>DocumentDB (27 alarms) - PRODUCTION ENHANCED</b></summary>

- **CPUUtilization**: Info (70%), Warning (80%), Critical (90%)
- **DatabaseConnections**: Info (100), Warning (200), Critical (300)
- **FreeableMemory**: Info (1GB free), Warning (512MB free), Critical (256MB free)
- **ReadIOPS**: Warning (5000), Critical (10000)
- **WriteIOPS**: Warning (5000), Critical (10000)
- **ReadLatency**: Warning (10ms), Critical (20ms)
- **WriteLatency**: Warning (10ms), Critical (20ms)
- **DBInstanceReplicaLag**: Warning (1000ms), Critical (5000ms)
- **VolumeBytesUsed**: Info (100GB), Warning (150GB)
- **BufferCacheHitRatio**: Warning (< 95%) - Memory pressure indicator
- **IndexBufferCacheHitRatio**: Warning (< 95%) - Index memory pressure
- **DatabaseCursors**: Warning (> 4000) - Cursor exhaustion prevention
- **DatabaseCursorsTimedOut**: Info (> 10) - Application cursor management
- **DBClusterReplicaLagMaximum**: Critical (> 5000ms) - Cluster-level replication health

**New Additions:** Cache hit ratio and cursor monitoring for early problem detection

</details>

<details>
<summary><b>EFS (8 alarms)</b></summary>

- **ClientConnections**: Info (100), Warning (200), Critical (300)
- **PercentIOLimit**: Info (80%), Warning (90%), Critical (95%)
- **BurstCreditBalance**: Warning (< 1TB), Critical (< 512GB) - Lower is worse

</details>

<details>
<summary><b>ALB (18 alarms) - PRODUCTION ENHANCED</b></summary>

- **ActiveConnectionCount**: Warning (10000), Critical (20000)
- **HTTPCode_Target_5XX_Count**: Warning (100), Critical (500) - Target errors
- **HTTPCode_ELB_5XX_Count**: Critical (10) - ALB internal errors
- **HTTPCode_ELB_4XX_Count**: Warning (100) - Client request errors
- **UnHealthyHostCount**: Warning (≥ 1), Critical (≥ 2)
- **HealthyHostCount**: Critical (< 1) - No healthy targets
- **TargetResponseTime**: Warning (1s), Critical (3s)
- **TargetConnectionErrorCount**: Warning (10), Critical (50) - Backend connectivity
- **TargetTLSNegotiationErrorCount**: Warning (10) - SSL/TLS handshake failures
- **ProcessedBytes**: Warning (1GB), Critical (5GB)
- **RejectedConnectionCount**: Warning (10), Critical (50)

**New Additions:** ALB-originated errors and backend connectivity monitoring for better troubleshooting

</details>

<details>
<summary><b>OpenSearch (17 alarms per domain)</b></summary>

- ClusterDisconnectedNodeCount: Info (1)
- ClusterPrimaryShardCount: Warning (900), Critical (950)
- ClusterSlowSearchingCount: Warning (200), Critical (500)
- ClusterStatus.green: Critical (< 1)
- ClusterStatus.yellow: Warning (> 1)
- ClusterStatus.red: Critical (> 1)
- CPUUtilization: Info (70%), Warning (80%), Critical (90%)
- JVMMemoryPressure: Info (70%), Warning (80%), Critical (90%)
- MasterCPUUtilization: Warning (80%), Critical (90%)
- MasterJVMMemoryPressure: Critical (90%)

</details>

<details>
<summary><b>MSK Kafka (21 alarms per cluster)</b></summary>

- InstanceCpuUsageV2: Info (70%), Warning (80%), Critical (90%)
- InstanceFetchThrottleQueueSizeV2: Warning (300), Critical (500)
- InstanceMemoryUsedV2: Info (70%), Warning (80%), Critical (90%)
- InstanceProduceThrottleQueueSizeV2: Warning (300), Critical (500)
- InstanceRootDiskUsedV2: Info (70%), Warning (80%), Critical (90%)
- PartitionCount: Warning (1000), Critical (1500)
- TopicCount: Warning (500), Critical (800)
- UnderReplicatedPartitions: Warning (10), Critical (50)
- ZooKeeperRequestLatencyMsMean: Warning (100ms), Critical (200ms)

</details>

<details>
<summary><b>AmazonMQ RabbitMQ (12 alarms per broker)</b></summary>

- ConsumerLag: Info (5000), Warning (10000), Critical (50000)
- ConsumerLagPerGidTopic: Info (5000), Warning (10000), Critical (50000)
- CpuUtilization: Info (70%), Warning (80%), Critical (90%)
- MemoryUsage: Info (70%), Warning (80%), Critical (90%)

</details>

<details>
<summary><b>WAF (2 alarms per WebACL)</b></summary>

- BlockedRequests: Warning (50)
- AllowedRequests: Info (10000)

</details>

---

## 🎯 Production Enhancements (January 2026)

### What's New

Based on AWS best practices and official documentation review, the following critical metrics have been added:

**EC2 Enhancements (4 new alarms):**
- ✅ `StatusCheckFailed` - Overall instance health
- ✅ `StatusCheckFailed_System` - AWS infrastructure issues
- ✅ `StatusCheckFailed_Instance` - Instance configuration problems
- ✅ `StatusCheckFailed_AttachedEBS` - EBS volume connectivity

**RDS Enhancements (3 new alarms):**
- ✅ `DiskQueueDepth` - I/O bottleneck detection (Warning: 10, Critical: 20)
- ✅ `BurstBalance` - GP2 IOPS credit monitoring (Warning: < 20%)

**DocumentDB Enhancements (6 new alarms):**
- ✅ `BufferCacheHitRatio` - Memory pressure indicator (Warning: < 95%)
- ✅ `IndexBufferCacheHitRatio` - Index memory pressure (Warning: < 95%)
- ✅ `DatabaseCursors` - Cursor exhaustion prevention (Warning: > 4000)
- ✅ `DatabaseCursorsTimedOut` - Application cursor management (Info: > 10)
- ✅ `DBClusterReplicaLagMaximum` - Cluster-level replication health (Critical: > 5s)

**ALB Enhancements (6 new alarms):**
- ✅ `HTTPCode_ELB_5XX_Count` - ALB internal errors (Critical: 10)
- ✅ `HTTPCode_ELB_4XX_Count` - Client request format errors (Warning: 100)
- ✅ `TargetConnectionErrorCount` - Backend connectivity issues (Warning: 10, Critical: 50)
- ✅ `HealthyHostCount` - Minimum healthy targets (Critical: < 1)
- ✅ `TargetTLSNegotiationErrorCount` - SSL/TLS handshake failures (Warning: 10)

### Why These Matter

- **EC2 Status Checks:** Detect underlying infrastructure failures before they cause outages
- **RDS DiskQueueDepth:** Identify storage bottlenecks causing high latency
- **DocumentDB Cache Ratios:** Early warning for memory pressure (AWS recommends < 95% as scale-up indicator)
- **ALB ELB Errors:** Distinguish load balancer issues from application issues for faster troubleshooting

### Architecture Review

See `ARCHITECTURE_REVIEW.md` for complete production readiness assessment including:
- Service-by-service analysis
- Threshold validation against AWS recommendations
- Missing metrics analysis
- Production deployment checklist

---

## 🔧 Common Commands

### Deploy Tag-Based Alarms

**Required Parameters:**
- `--sns-topic` (REQUIRED) - SNS Topic ARN for alarm notifications
- `--tag-key` (optional, default: "Environment")
- `--tag-value` (optional, default: "Production")

**How Tag Injection Works:**
The deployment script passes `--tag-key` and `--tag-value` as CloudFormation parameters. The template validates all parameters are non-empty and SNS ARN is valid format.

**Individual Resource Visibility:**
Each alarm uses CloudWatch Metrics Insights with `GROUP BY` to create separate alarm states per resource:
- **EC2:** Grouped by `tag.Name` (only monitors instances with Name tag)
- **RDS:** Grouped by `DBInstanceIdentifier`
- **ElastiCache:** Grouped by `CacheClusterId`
- **EFS:** Grouped by `FileSystemId`

This means ONE alarm monitors ALL matching resources, but you see which specific instance/cluster triggered.

```bash
# Production (uses defaults: Environment=Production)
python deploy-cloudwatch-alarms.py --mode tag-based \
  --sns-topic arn:aws:sns:ap-southeast-2:123:cloudwatch-alarms-prod \
  --region ap-southeast-2

# UAT environment
python deploy-cloudwatch-alarms.py --mode tag-based \
  --tag-value uat \
  --sns-topic arn:aws:sns:ap-southeast-2:123:cloudwatch-alarms-uat \
  --region ap-southeast-2

# Custom tag (specify both key and value)
python deploy-cloudwatch-alarms.py --mode tag-based \
  --tag-key Team --tag-value DataEngineering \
  --sns-topic arn:aws:sns:ap-southeast-2:123:cloudwatch-alarms-team \
  --region ap-southeast-2
```

**Note:** Large templates (>51KB) are automatically uploaded to S3 bucket `cloudformation-templates-{account-id}-{region}` before deployment.

### Deploy Resource-Based Alarms

```bash
# OpenSearch (auto-discover all domains)
python deploy-cloudwatch-alarms.py --mode resource-based --service opensearch --discover-all

# DocumentDB (auto-discover all clusters)
python deploy-cloudwatch-alarms.py --mode resource-based --service docdb --discover-all

# ALB (auto-discover all load balancers)
python deploy-cloudwatch-alarms.py --mode resource-based --service alb --discover-all

# Kafka (specific clusters)
python deploy-cloudwatch-alarms.py --mode resource-based --service kafka \
  --resources prod-kafka staging-kafka

# RabbitMQ (auto-discover)
python deploy-cloudwatch-alarms.py --mode resource-based --service rabbitmq --discover-all

# WAF (auto-discover)
python deploy-cloudwatch-alarms.py --mode resource-based --service waf --discover-all
```

### Deploy Everything

**Deploy or update all stacks in one command:**

```bash
# Deploy tag-based + all resource-based services
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**This command:**
- Creates new stacks for first-time deployment
- Updates existing stacks with new alarms (no deletion)
- Auto-discovers all resources with matching tags
- Skips services with no tagged resources

### Manage Stacks

```bash
# Check status
aws cloudformation describe-stacks --stack-name tag-based-alarms-production

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name tag-based-alarms-production

# Update stack
aws cloudformation update-stack --stack-name tag-based-alarms-production \
  --template-body file://cloudformation-tag-based-alarms.yaml \
  --parameters ParameterKey=TagKey,UsePreviousValue=true

# Delete stack
aws cloudformation delete-stack --stack-name tag-based-alarms-production
```

### View Alarms

```bash
# List all Production alarms
aws cloudwatch describe-alarms --alarm-name-prefix "Production-"

# Count alarms
aws cloudwatch describe-alarms --alarm-name-prefix "Production-" \
  --query 'length(MetricAlarms)'

# Check specific alarm
aws cloudwatch describe-alarms --alarm-names "Production-EC2-CPUUtilization-Critical"

# Get alarm history
aws cloudwatch describe-alarm-history \
  --alarm-name "Production-EC2-CPUUtilization-Critical"
```

### Test Alarms

```bash
# Trigger alarm
aws cloudwatch set-alarm-state \
  --alarm-name "Production-EC2-CPUUtilization-Critical" \
  --state-value ALARM \
  --state-reason "Testing"

# Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name "Production-EC2-CPUUtilization-Critical" \
  --state-value OK \
  --state-reason "Test complete"
```

---

## 🏷️ Tagging Resources

### Tag-Based Services (Required)

```bash
# EC2
aws ec2 create-tags --resources i-123 i-456 \
  --tags Key=Environment,Value=Production

# RDS
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:us-east-1:123:db:prod-mysql-01 \
  --tags Key=Environment,Value=Production

# ElastiCache
aws elasticache add-tags-to-resource \
  --resource-name arn:aws:elasticache:us-east-1:123:cluster:prod-redis-001 \
  --tags Key=Environment,Value=Production

# EFS
aws efs tag-resource \
  --resource-id fs-12345678 \
  --tags Key=Environment,Value=Production
```

---

## ❓ Frequently Asked Questions

### How do I update existing stacks with new alarms?

**Simply re-run the same deployment command.** The script automatically detects existing stacks and updates them:

```bash
# This command works for both initial deployment AND updates
python deploy-cloudwatch-alarms.py --mode all \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

**What happens during update:**
- ✅ Existing alarms continue running (no deletion)
- ✅ New alarms are added
- ✅ Modified alarms are updated
- ✅ Zero downtime
- ✅ Automatic rollback if update fails

### Will my existing alarms be deleted?

**No!** CloudFormation updates are additive:
- Existing alarms stay active
- New alarms are added
- Only explicitly removed resources are deleted (we never remove alarms)

### How often should I update?

**Update when:**
- Adding new metrics to configuration files
- Changing alarm thresholds
- Adding new resources with matching tags
- Applying production enhancements

**Safe to run:** Daily, weekly, or on-demand

### What if I add new resources?

**Automatic discovery:** Just re-run the deployment command. The script will:
- Discover newly tagged resources
- Add them to existing stacks
- Create alarms for them

### Can I update just one service?

**Yes!** Use `--mode resource-based` with `--service`:

```bash
# Update only DocumentDB alarms
python deploy-cloudwatch-alarms.py --mode resource-based \
  --service docdb \
  --tag-key businessTag \
  --tag-value EM-SNC-CLOUD \
  --discover-all \
  --sns-topic arn:aws:sns:us-east-1:476114114317:cloudwatchTopic \
  --region us-east-1
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **INSUFFICIENT_DATA** | Resources missing `Environment` tag - add tags |
| **No resources found** | Verify tag key/value match your resources |
| **boto3 not found** | Run `pip install boto3 pyyaml aws-cdk-lib` |
| **CloudFormation limit exceeded** | Too many resources - use tag-based or split |
| **Alarm not triggering** | Check metric data exists with `get-metric-statistics` |
| **Stack update failed** | Check CloudFormation events for details |
| **Template not found** | Run script from project directory |

---

## 📁 Project Files

**Core Files:**
- `cloudformation-tag-based-alarms.yaml` - Unified tag-based template (64 alarms for 4 services) - PRODUCTION ENHANCED
- `deploy-cloudwatch-alarms.py` - Main deployment script with auto-discovery
- `alarm-config-resource-based.yaml` - Alarm definitions for resource-based services (OpenSearch, Kafka, RabbitMQ, DocumentDB, ALB, WAF) - PRODUCTION ENHANCED
- `generate-resource-based-template.py` - Generates CloudFormation templates for resource-based services
- `ARCHITECTURE_REVIEW.md` - Comprehensive production readiness assessment

**Documentation:**
- `README.md` - This file (complete guide)

**Source:**
- `告警监控.xlsx` - Original Alicloud metrics

**Total: 6 files** (minimal and clean)

---

1. ✅ **Use tag-based for everything possible** - 90% cost savings
2. ✅ **Enforce consistent tagging** - Use AWS Config rules
3. ✅ **Deploy per environment** - Separate stacks for Prod/Staging/Dev
4. ✅ **Test in dev first** - Verify before production
5. ✅ **Monitor INSUFFICIENT_DATA** - Indicates missing tags
6. ✅ **Use MAX aggregation** - Catches individual resource issues
7. ✅ **SNS per environment** - Different topics for different environments

---
