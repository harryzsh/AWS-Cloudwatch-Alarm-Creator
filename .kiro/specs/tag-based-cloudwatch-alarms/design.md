# Design Document: Tag-Based CloudWatch Alarms Implementation

## Overview

This design implements a hybrid CloudWatch alarm deployment system that leverages AWS's tag-based alarm capabilities where supported, and falls back to resource-based alarms for services that don't support tags. The system reduces alarm count from thousands to hundreds while maintaining comprehensive monitoring coverage.

### Key Benefits

- **Reduced Alarm Count**: 162 tag-based alarms instead of thousands of individual alarms
- **Automatic Scaling**: New resources with matching tags are automatically monitored
- **Simplified Management**: 11 stacks instead of 500+ stacks
- **Cost Effective**: Fewer alarms = lower CloudWatch costs
- **Maintainable**: Clear separation between tag-based and resource-based services

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Script                         │
│                  (deploy-alarms-v2.py)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────────┐         ┌──────────────────┐
│  Tag-Based Mode   │         │ Resource-Based   │
│   (7 services)    │         │  Mode (4 svcs)   │
└────────┬──────────┘         └────────┬─────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐       ┌──────────────────────┐
│ Static CloudFormation│       │ CDK Template Generator│
│    Templates         │       │  (Dynamic)            │
└────────┬────────────┘       └────────┬─────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │  CloudFormation  │
              │   (11 Stacks)    │
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  CloudWatch      │
              │   Alarms         │
              └──────────────────┘
```

### Stack Architecture

```
Tag-Based Stack (1):
└─ tag-based-alarms        (162 alarms total)
   ├─ EC2 alarms           (8 alarms)
   ├─ RDS MySQL alarms     (21 alarms)
   ├─ RDS PostgreSQL alarms(30 alarms)
   ├─ Redis alarms         (27 alarms)
   ├─ DocumentDB alarms    (49 alarms)
   ├─ EFS alarms           (14 alarms)
   └─ ALB alarms           (13 alarms)

Resource-Based Stacks (4):
├─ opensearch-alarms       (N × 17 alarms)
├─ kafka-alarms            (N × 21 alarms)
├─ rabbitmq-alarms         (N × 12 alarms)
└─ waf-alarms              (N × 2 alarms)

Total: 5 stacks (1 tag-based + 4 resource-based)
```

## Components and Interfaces

### 1. Deployment Script (`deploy-alarms-v2.py`)

**Purpose**: Orchestrates alarm deployment for all services

**Key Functions**:
```python
def deploy_tag_based_alarms(service: str, tag_key: str, tag_value: str, 
                            sns_topic: str, region: str) -> DeploymentResult:
    """Deploy tag-based alarms for a service"""
    
def deploy_resource_based_alarms(service: str, resource_ids: List[str],
                                 sns_topic: str, region: str) -> DeploymentResult:
    """Deploy resource-based alarms for a service"""
    
def discover_resources(service: str, tag_filter: Dict, 
                      region: str) -> List[str]:
    """Discover all resources of a service type"""
    
def generate_cdk_template(service: str, resource_ids: List[str]) -> str:
    """Generate CloudFormation template using CDK"""
```

**CLI Interface**:
```bash
# Tag-based deployment
python deploy-alarms-v2.py \
  --service ec2 \
  --mode tag-based \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:123:alerts

# Resource-based deployment
python deploy-alarms-v2.py \
  --service opensearch \
  --mode resource-based \
  --discover-all \
  --sns-topic arn:aws:sns:us-east-1:123:alerts

# Deploy all services
python deploy-alarms-v2.py \
  --service all \
  --tag-key Environment \
  --tag-value Production \
  --sns-topic arn:aws:sns:us-east-1:123:alerts
```

### 2. Tag-Based CloudFormation Templates

**Template Structure** (example: `ec2-alarms-tagged.yaml`):
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Tag-based CloudWatch Alarms for EC2

Parameters:
  TagKey:
    Type: String
    Description: Tag key to filter resources
    Default: Environment
  
  TagValue:
    Type: String
    Description: Tag value to filter resources
    Default: Production
  
  SNSTopicArn:
    Type: String
    Description: SNS Topic ARN for notifications

Resources:
  CPUCriticalAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub '${TagValue}-EC2-CPU-Critical'
      # Uses Metrics Insights query with tag filter
      Metrics:
        - Id: m1
          ReturnData: true
          MetricStat:
            Metric:
              Namespace: AWS/EC2
              MetricName: CPUUtilization
              # Tag-based dimension filtering
            Period: 300
            Stat: Average
      Threshold: 90
      ComparisonOperator: GreaterThanThreshold
      EvaluationPeriods: 2
      AlarmActions:
        - !Ref SNSTopicArn
```

### 3. CDK Template Generator

**Purpose**: Dynamically generate CloudFormation templates for resource-based alarms

**Implementation**:
```python
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns
)

class ResourceBasedAlarmsStack(Stack):
    def __init__(self, scope, id, service_config, resource_ids, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create alarms for each resource
        for resource_id in resource_ids:
            for alarm_config in service_config['alarms']:
                self.create_alarm(resource_id, alarm_config)
    
    def create_alarm(self, resource_id, config):
        return cloudwatch.Alarm(
            self, f"{resource_id}-{config['metric']}-{config['severity']}",
            metric=cloudwatch.Metric(
                namespace=config['namespace'],
                metric_name=config['metric'],
                dimensions={config['dimension_name']: resource_id}
            ),
            threshold=config['threshold'],
            evaluation_periods=2,
            comparison_operator=config['operator']
        )
```

### 4. Service Configuration

**Configuration File** (`service-config.yaml`):
```yaml
services:
  ec2:
    supports_tags: true
    template: cloudformation-alarms-ec2-tagged.yaml
    alarms_per_resource: 8
    namespace: AWS/EC2
    dimension_name: InstanceId
    
  opensearch:
    supports_tags: false
    alarms_per_resource: 17
    namespace: AWS/ES
    dimension_name: DomainName
    alarms:
      - metric: CPUUtilization
        severity: Critical
        threshold: 90
        operator: GreaterThanThreshold
      # ... more alarm configs
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

### ServiceConfig
```python
@dataclass
class ServiceConfig:
    name: str
    supports_tags: bool
    template_path: Optional[str]
    alarms_per_resource: int
    namespace: str
    dimension_name: str
    alarm_configs: List[AlarmConfig]
```

### AlarmConfig
```python
@dataclass
class AlarmConfig:
    metric: str
    severity: str  # 'Info', 'Warning', 'Critical'
    threshold: float
    operator: str
    period: int = 300
    evaluation_periods: int = 2
    description: str = ""
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Tag-Based Alarm Automatic Monitoring
*For any* resource with matching tags, when the resource is created, the existing tag-based alarm should automatically monitor it without requiring any CloudFormation stack updates.
**Validates: Requirements 1.3**

### Property 2: Alarm Count Per Tag Group
*For any* set of resources with the same tag key-value pair, there should be exactly one alarm per metric (not one alarm per resource per metric).
**Validates: Requirements 1.4**

### Property 3: Resource-Based Alarm Count
*For any* service with N resources, when deploying resource-based alarms, the system should create exactly N × alarms_per_resource alarms.
**Validates: Requirements 2.2**

### Property 4: CloudFormation Resource Limit
*For any* generated CloudFormation stack, the total number of resources in the stack must be ≤ 500.
**Validates: Requirements 2.4**

### Property 5: Configuration Preservation
*For any* alarm configuration in the original templates, the generated template should preserve the threshold value, metric name, namespace, and severity level.
**Validates: Requirements 6.1, 6.2, 6.3**

### Property 6: Idempotent Deployment
*For any* deployment configuration, running the deployment script twice should produce the same result as running it once (same stacks, same alarms, no duplicates).
**Validates: Requirements 4.4**

### Property 7: Stack Naming Convention
*For all* created stacks, the stack name should match the pattern `tag-based-alarms` for the combined tag-based stack, or `{service}-alarms` for resource-based stacks.
**Validates: Requirements 5.2**

### Property 8: SNS Integration
*For all* generated alarms, the alarm should have an AlarmActions property that references an SNS topic parameter.
**Validates: Requirements 5.4**

### Property 9: Resource Discovery Completeness
*For any* service type and region, when discovering resources, the system should find all resources of that type that exist in that region.
**Validates: Requirements 7.1**

### Property 10: Tag Filtering
*For any* tag filter (key=value), when discovering resources, only resources with that exact tag key-value pair should be returned.
**Validates: Requirements 7.2**

### Property 11: Stack Count
*When* deploying all services, exactly 5 CloudFormation stacks should be created (1 tag-based stack + 4 resource-based stacks).
**Validates: Requirements 5.3**

## Error Handling

### CloudFormation Limit Exceeded
```python
if resource_count > 500:
    raise CloudFormationLimitError(
        f"Stack would have {resource_count} resources, exceeding the 500 limit. "
        f"Consider splitting into multiple stacks or reducing resource count."
    )
```

### Resource Not Found
```python
try:
    resources = discover_resources(service, region)
except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceNotFoundException':
        logger.warning(f"No {service} resources found in {region}")
        return []
    raise
```

### Template Generation Failure
```python
try:
    template = generate_template(service, resources)
    validate_template(template)
except TemplateValidationError as e:
    raise DeploymentError(
        f"Template validation failed for {service}: {e.message}\n"
        f"Check alarm configurations and CloudFormation syntax."
    )
```

### Stack Update Failure
```python
try:
    cfn.update_stack(StackName=stack_name, TemplateBody=template)
except ClientError as e:
    if 'No updates are to be performed' in str(e):
        return DeploymentResult(status='no-change')
    elif 'ValidationError' in str(e):
        raise DeploymentError(f"Stack update failed: {e}")
    raise
```

## Testing Strategy

### Unit Tests
- Test template generation for each service
- Test resource discovery with mocked AWS responses
- Test configuration parsing and validation
- Test error handling for various failure scenarios

### Property-Based Tests
- Property 1-11 (as defined in Correctness Properties section)
- Each property test should run with minimum 100 iterations
- Use hypothesis (Python) for property-based testing

### Integration Tests
- Deploy to test AWS account
- Verify stacks are created correctly
- Verify alarms are monitoring resources
- Test stack updates with new resources
- Test idempotency by running deployment twice

### Example Property Test
```python
from hypothesis import given, strategies as st
import pytest

@given(
    resources=st.lists(st.text(min_size=10, max_size=20), min_size=1, max_size=50),
    alarms_per_resource=st.integers(min_value=1, max_value=50)
)
def test_resource_based_alarm_count(resources, alarms_per_resource):
    """
    Property 3: Resource-Based Alarm Count
    Feature: tag-based-cloudwatch-alarms, Property 3
    """
    # Generate template
    template = generate_resource_based_template('test-service', resources, alarms_per_resource)
    
    # Parse template and count alarm resources
    alarm_count = count_alarms_in_template(template)
    
    # Verify: N resources × alarms_per_resource = total alarms
    expected_count = len(resources) * alarms_per_resource
    assert alarm_count == expected_count, \
        f"Expected {expected_count} alarms for {len(resources)} resources, got {alarm_count}"
```

## Migration Strategy

### Phase 1: Preparation
1. Backup existing alarm configurations
2. Document current stack names and alarm counts
3. Test new system in development environment

### Phase 2: Tag-Based Services (Low Risk)
1. Deploy tag-based alarms for EC2 (parallel to existing)
2. Verify alarms are working
3. Delete old per-instance EC2 alarm stacks
4. Repeat for RDS, Redis, DocumentDB, EFS, ALB

### Phase 3: Resource-Based Services (Medium Risk)
1. Deploy new resource-based stacks for OpenSearch, Kafka, RabbitMQ, WAF
2. Verify alarms are working
3. Delete old alarm stacks

### Phase 4: Cleanup
1. Remove old deployment scripts
2. Update documentation
3. Archive old templates

### Rollback Plan
If issues occur:
1. Keep old stacks running during migration
2. Can switch back by updating SNS subscriptions
3. Delete new stacks if needed
4. No data loss (alarms don't store data)

## Performance Considerations

### Deployment Time
- Tag-based: ~30 seconds per stack (7 stacks = 3.5 minutes)
- Resource-based: ~2-5 minutes per stack depending on resource count
- Total deployment time: ~10-15 minutes for all services

### CloudWatch Costs
- Old system: ~800 alarms × $0.10 = $80/month
- New system: ~162 tag-based + ~200 resource-based = ~$36/month
- **Savings: ~$44/month (55% reduction)**

### API Rate Limits
- Resource discovery: Paginated to handle large resource counts
- CloudFormation updates: Sequential to avoid throttling
- Implement exponential backoff for retries

## Security Considerations

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DescribeStacks",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DescribeAlarms",
        "ec2:DescribeInstances",
        "rds:DescribeDBInstances",
        "elasticache:DescribeCacheClusters",
        "docdb:DescribeDBClusters",
        "efs:DescribeFileSystems",
        "elasticloadbalancing:DescribeLoadBalancers",
        "es:ListDomainNames",
        "kafka:ListClusters",
        "mq:ListBrokers",
        "wafv2:ListWebACLs"
      ],
      "Resource": "*"
    }
  ]
}
```

### SNS Topic Permissions
- Ensure SNS topic allows CloudWatch to publish
- Use resource-based policy on SNS topic

### Tag-Based Security
- Ensure resources are tagged consistently
- Use AWS Config rules to enforce tagging
- Implement tag-based access control if needed
