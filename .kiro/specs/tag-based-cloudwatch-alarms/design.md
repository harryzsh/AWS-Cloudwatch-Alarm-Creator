# Design Document: CloudWatch Alarms - Production Monitoring System

## Overview

Production-grade CloudWatch alarm deployment system using hybrid architecture optimized for AWS best practices. Combines tag-based alarms (for automatic scaling) with resource-based alarms (for specialized metrics).

### Current Architecture (January 2026)

```
Tag-Based Stack (1):
└─ 64 alarms for EC2, RDS, Redis, EFS
   ├─ EC2: 11 alarms (CPU, Network, Status Checks)
   ├─ RDS: 25 alarms (CPU, Memory, Storage, IOPS, Latency, I/O Queue)
   ├─ Redis: 19 alarms (CPU, Memory, Connections, Evictions, Cache Hit)
   └─ EFS: 8 alarms (Connections, IO Limit, Burst Credits)

Resource-Based Stacks (6):
├─ DocumentDB: 27 alarms/cluster (cache ratios, cursors, replication)
├─ ALB: 18 alarms/LB (errors, connections, health)
├─ OpenSearch: 17 alarms/domain (cluster health, shards)
├─ Kafka: 21 alarms/cluster (partitions, replication)
├─ RabbitMQ: 12 alarms/broker (messages, connections)
└─ WAF: 2 alarms/WebACL (blocked/allowed requests)
```

### Key Design Decisions

1. **Moved DocumentDB & ALB to Resource-Based**
   - Reason: Better granular control per cluster/load balancer
   - Benefit: Specialized metrics (cache hit ratios, ELB error sources)

2. **Use MAX Statistic**
   - Reason: Catches worst-case across GROUP BY resources
   - Benefit: No single resource issue goes undetected

3. **Production Enhancements**
   - Added EC2 status checks (infrastructure health)
   - Added RDS I/O monitoring (bottleneck detection)
   - Added DocumentDB cache metrics (memory pressure)
   - Added ALB error source identification (faster troubleshooting)

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────┐
│         deploy-cloudwatch-alarms.py              │
│  (Orchestrates deployment & resource discovery)  │
└────────────────┬─────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌─────────────┐    ┌────────────────────┐
│ Tag-Based   │    │ Resource-Based     │
│ Template    │    │ Generator          │
│ (Static)    │    │ (Dynamic)          │
└──────┬──────┘    └──────┬─────────────┘
       │                  │
       └────────┬─────────┘
                ▼
       ┌─────────────────┐
       │ CloudFormation  │
       │   (7 Stacks)    │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │  CloudWatch     │
       │   Alarms        │
       └─────────────────┘
```

### Data Flow

1. **User runs deployment script** with tag key/value and SNS topic
2. **Script validates** prerequisites (boto3, AWS credentials, templates)
3. **For tag-based services:**
   - Reads static CloudFormation template
   - Injects tag parameters
   - Deploys/updates stack
4. **For resource-based services:**
   - Discovers resources by tags using AWS APIs
   - Generates CloudFormation template dynamically
   - Deploys/updates stack per service
5. **CloudFormation** creates/updates alarm resources
6. **CloudWatch** monitors resources and sends alerts to SNS

## Components and Interfaces

### 1. Deployment Script

**File:** `deploy-cloudwatch-alarms.py`

**Key Functions:**

```python
def deploy_tag_based_alarms(tag_key, tag_value, sns_topic, region) -> DeploymentResult
def deploy_resource_based_alarms(service, resource_ids, sns_topic, region) -> DeploymentResult
def discover_resources(service, region, tag_key, tag_value) -> List[str]
def generate_resource_based_template(service, resource_ids, tag_value) -> str
```

**CLI Interface:**

```bash
# Deploy everything
--mode all --tag-key KEY --tag-value VALUE --sns-topic ARN --region REGION

# Deploy tag-based only
--mode tag-based --tag-key KEY --tag-value VALUE --sns-topic ARN

# Deploy specific resource-based service
--mode resource-based --service SERVICE --discover-all --sns-topic ARN
```

### 2. Tag-Based Template

**File:** `cloudformation-tag-based-alarms.yaml`

**Structure:**
- Parameters: TagKey, TagValue, SNSTopicArn
- Resources: 64 alarm definitions using Metrics Insights
- Outputs: Stack name, alarm count, monitored services

**Metrics Insights Query Pattern:**
```sql
SELECT MAX(MetricName) FROM "Namespace" 
WHERE tag.{TagKey} = '{TagValue}' 
GROUP BY DimensionName 
ORDER BY MAX() DESC
```

### 3. Resource-Based Generator

**File:** `generate-resource-alarms-simple.py`

**Purpose:** Generates CloudFormation templates for resource-based services

**Input:** Service config + resource IDs  
**Output:** CloudFormation YAML template

**Template Pattern:**
```yaml
Resources:
  ServiceMetricSeverityAlarmN:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: {TagValue}-{Service}-{ResourceID}-{Metric}-{Severity}
      Metrics:
        - Expression: SELECT max(Metric) FROM "Namespace" WHERE Dimension = 'ResourceID'
```

### 4. Service Configuration

**File:** `alarm-config-resource-based.yaml`

**Structure:**
```yaml
services:
  docdb:
    name: DocumentDB
    namespace: AWS/DocDB
    dimension_name: DBClusterIdentifier
    alarms:
      - metric: CPUUtilization
        severity: Warning
        threshold: 80
        operator: GreaterThanThreshold
        description: DocumentDB CPU使用率
```

## Data Models

### DeploymentResult
```python
@dataclass
class DeploymentResult:
    service: str
    stack_name: str
    status: str  # 'created', 'updated', 'failed', 'no-change'
    alarm_count: int
    resource_count: int
    error_message: Optional[str] = None
```

## Correctness Properties

### Property 1: Tag-Based Automatic Monitoring
*For any* resource with matching tags, the existing tag-based alarm should automatically monitor it without stack updates.
**Validates: Requirements 1.3**

### Property 2: Resource Discovery Completeness
*For any* service and tag filter, resource discovery should find all matching resources in the region.
**Validates: Requirements 7.1, 7.2**

### Property 3: Idempotent Deployment
*For any* deployment configuration, running the script twice should produce the same result (no duplicates, same alarm count).
**Validates: Requirements 4.4, 6.1**

### Property 4: Zero-Downtime Updates
*For any* stack update, existing alarms should remain active and monitoring should continue uninterrupted.
**Validates: Requirements 6.1, 6.3**

### Property 5: Alarm Count Accuracy
*For any* resource-based service with N resources and M alarms per resource, exactly N × M alarms should be created.
**Validates: Requirements 2.2**

## Error Handling

### CloudFormation Limit Exceeded
```python
if alarm_count > 500:
    raise ValueError(
        f"Stack would have {alarm_count} alarms, exceeding 500 limit. "
        f"Consider splitting resources or using tag-based alarms."
    )
```

### Resource Discovery Failures
```python
try:
    resources = discover_resources(service, region, tag_key, tag_value)
except ClientError as e:
    logger.warning(f"Discovery failed for {service}: {e}")
    return []  # Gracefully skip service
```

### Stack Update Failures
```python
try:
    cfn.update_stack(StackName=stack_name, TemplateBody=template)
except ClientError as e:
    if 'No updates are to be performed' in str(e):
        return DeploymentResult(status='no-change')
    raise  # Automatic rollback by CloudFormation
```

## Testing Strategy

### Unit Tests
- Template generation for each service
- Resource discovery with mocked AWS responses
- Configuration parsing and validation
- Error handling scenarios

### Integration Tests
- Deploy to test AWS account
- Verify alarms monitor resources correctly
- Test stack updates with new resources
- Validate idempotency

### Property-Based Tests
- Test Properties 1-5 with 100+ iterations each
- Use hypothesis for Python property testing
- Tag format: `Feature: tag-based-cloudwatch-alarms, Property N`

## Security

### Required IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "cloudformation:*Stack",
      "cloudwatch:PutMetricAlarm",
      "ec2:DescribeInstances",
      "rds:DescribeDBInstances",
      "elasticache:DescribeCacheClusters",
      "docdb:DescribeDBClusters",
      "efs:DescribeFileSystems",
      "elasticloadbalancing:DescribeLoadBalancers",
      "es:ListDomainNames",
      "kafka:ListClusters",
      "mq:ListBrokers",
      "wafv2:ListWebACLs",
      "*:ListTagsForResource"
    ],
    "Resource": "*"
  }]
}
```

### SNS Topic Policy
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudwatch.amazonaws.com"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:region:account:topic"
  }]
}
```

## Performance

### Deployment Time
- Tag-based stack: ~30 seconds
- Resource-based stacks: ~2-5 minutes each
- Total: ~10-15 minutes for complete deployment

### Cost
- Old system: ~800 alarms × $0.10 = $80/month
- New system: ~130 alarms × $0.10 = $13/month
- **Savings: $67/month (84% reduction)**

## Migration from Old System

### Approach
1. Deploy new system in parallel
2. Verify alarms working correctly
3. Update SNS subscriptions if needed
4. Delete old stacks
5. No monitoring gaps

### Rollback
- Keep old stacks during migration
- Can revert by deleting new stacks
- Zero data loss (alarms don't store data)

