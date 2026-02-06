# Requirements Document

## Introduction

Restructure the CloudWatch alarms project to match the 海平观测Metric.xlsx requirements file. This involves removing services no longer needed (Redis, RDS, EFS, OpenSearch, RabbitMQ, WAF, DocumentDB, EKS EC2), adding new services (NAT Gateway, VPN, ACM, Direct Connect), moving ALB from resource-based to tag-based, and trimming existing services (EC2, Kafka) to only the metrics specified in the Excel. The project maintains two alarm deployment approaches: tag-based (using CloudWatch Metrics Insights SQL with tag filtering) and resource-based (per-resource alarms discovered by tags).

## Glossary

- **Tag_Based_Template**: The CloudFormation YAML template (`cloudformation-tag-based-alarms.yaml`) that defines alarms using CloudWatch Metrics Insights SQL queries with tag-based filtering via `SELECT ... FROM ... WHERE tag.TagKey = 'TagValue'`
- **Resource_Based_Config**: The YAML configuration file (`alarm-config-resource-based.yaml`) that defines per-resource alarm definitions consumed by the template generator
- **Template_Generator**: The Python script (`generate-resource-alarms-simple.py`) that reads the Resource_Based_Config and produces per-resource CloudFormation templates
- **Deployment_Script**: The Python script (`deploy-cloudwatch-alarms.py`) that orchestrates discovery and deployment of both tag-based and resource-based alarm stacks
- **CWAgent_Metrics**: CloudWatch Agent custom metrics published to the `CWAgent` namespace (mem_used_percent, disk_used_percent, disk_inodes_used_percent) requiring the CloudWatch Agent to be installed on EC2 instances
- **Metrics_Insights_SQL**: CloudWatch Metrics Insights query language used for tag-based alarms, supporting `SELECT`, `FROM`, `WHERE`, `GROUP BY` clauses
- **Math_Expression**: CloudWatch metric math expressions used to compute derived metrics (e.g., memory percentage from MemoryUsed and MemoryFree)

## Requirements

### Requirement 1: Remove Obsolete Services from Tag-Based Template

**User Story:** As an operations engineer, I want the tag-based alarm template to only contain services specified in the Excel requirements, so that we do not deploy unnecessary alarms.

#### Acceptance Criteria

1. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL contain zero alarm resources for Redis (ElastiCache), RDS (MySQL/PostgreSQL), and EFS services
2. WHEN the Tag_Based_Template is inspected, THE Tag_Based_Template SHALL contain only EC2, NAT Gateway, ALB, and VPN alarm resources

### Requirement 2: Remove Obsolete Services from Resource-Based Config

**User Story:** As an operations engineer, I want the resource-based alarm config to only contain services specified in the Excel requirements, so that obsolete service alarms are not generated.

#### Acceptance Criteria

1. WHEN the Resource_Based_Config is loaded, THE Resource_Based_Config SHALL contain zero entries for OpenSearch, RabbitMQ, WAF, DocumentDB, and ALB services
2. WHEN the Resource_Based_Config is loaded, THE Resource_Based_Config SHALL contain only Kafka, ACM, and Direct Connect service entries

### Requirement 3: Restructure EC2 Alarms

**User Story:** As an operations engineer, I want EC2 alarms to match the Excel specification exactly, so that monitoring covers CPU, memory, disk, inode, system status, and instance status.

#### Acceptance Criteria

1. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 CPUUtilization alarm from the AWS/EC2 namespace with a threshold of 90%
2. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 mem_used_percent alarm from the CWAgent namespace with a threshold of 90%
3. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 disk_used_percent alarm from the CWAgent namespace with a threshold of 90%
4. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 disk_inodes_used_percent alarm from the CWAgent namespace with a threshold of 90%
5. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 StatusCheckFailed_System alarm from the AWS/EC2 namespace with a threshold of >=1
6. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one EC2 StatusCheckFailed alarm from the AWS/EC2 namespace with a threshold of >=1
7. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL contain zero EC2 NetworkIn or NetworkOut alarm resources

### Requirement 4: Add NAT Gateway Alarms

**User Story:** As an operations engineer, I want NAT Gateway alarms for port allocation failures, so that I am notified when NAT Gateway connectivity issues occur.

#### Acceptance Criteria

1. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one NAT Gateway ErrorPortAllocation alarm from the AWS/NATGateway namespace with a threshold of >100
2. THE Tag_Based_Template SHALL use Metrics_Insights_SQL queries with tag filtering for NAT Gateway alarms

### Requirement 5: Move ALB to Tag-Based and Trim Metrics

**User Story:** As an operations engineer, I want ALB alarms moved from resource-based to tag-based with only UnHealthyHostCount, so that ALB monitoring is simplified and consistent with tag-based approach.

#### Acceptance Criteria

1. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one ALB UnHealthyHostCount alarm from the AWS/ApplicationELB namespace with a threshold of >=1
2. THE Tag_Based_Template SHALL use Metrics_Insights_SQL queries with tag filtering for ALB alarms
3. WHEN the Resource_Based_Config is loaded, THE Resource_Based_Config SHALL contain zero ALB service entries

### Requirement 6: Add VPN Alarms

**User Story:** As an operations engineer, I want VPN tunnel state alarms at both connection and tunnel levels, so that I am notified when VPN tunnels go down.

#### Acceptance Criteria

1. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one VPN TunnelState connection-level alarm from the AWS/VPN namespace that triggers when any tunnel is down (value <1)
2. WHEN the Tag_Based_Template is deployed, THE Tag_Based_Template SHALL include exactly one VPN TunnelState tunnel-level alarm from the AWS/VPN namespace using both VpnId and TunnelIpAddress dimensions

### Requirement 7: Restructure Kafka (MSK) Alarms

**User Story:** As an operations engineer, I want Kafka alarms trimmed to the five metrics specified in the Excel, so that monitoring focuses on the most critical Kafka health indicators.

#### Acceptance Criteria

1. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL include exactly one MaxOffsetLag alarm with Consumer Group and Topic dimensions and a threshold of >200000
2. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL include exactly one CpuUser alarm with Broker ID dimension and a threshold of >90%
3. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL include exactly one memory percentage alarm using a Math_Expression of MemoryUsed/(MemoryUsed+MemoryFree)*100 with a threshold of >90%
4. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL include exactly one KafkaDataLogsDiskUsed alarm with Broker ID dimension and a threshold of >75%
5. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL include exactly one ActiveControllerCount alarm that triggers when the value is <1
6. WHEN the Resource_Based_Config is loaded for Kafka, THE Resource_Based_Config SHALL contain exactly five alarm definitions for the Kafka service

### Requirement 8: Add ACM Certificate Expiry Alarms

**User Story:** As an operations engineer, I want ACM certificate expiry alarms, so that I am notified when certificates are approaching expiration.

#### Acceptance Criteria

1. WHEN the Resource_Based_Config is loaded for ACM, THE Resource_Based_Config SHALL include exactly one DaysToExpiry alarm from the AWS/CertificateManager namespace with CertificateArn dimension and a threshold of <=30 days
2. WHEN ACM resources are discovered, THE Deployment_Script SHALL discover ACM certificates filtered by tags

### Requirement 9: Add Direct Connect Alarms

**User Story:** As an operations engineer, I want Direct Connect alarms for connection state and bandwidth utilization, so that I am notified of connectivity and capacity issues.

#### Acceptance Criteria

1. WHEN the Resource_Based_Config is loaded for Direct Connect, THE Resource_Based_Config SHALL include exactly one ConnectionState alarm from the AWS/DX namespace with ConnectionId dimension that triggers when value is <1
2. WHEN the Resource_Based_Config is loaded for Direct Connect, THE Resource_Based_Config SHALL include exactly one ingress bandwidth utilization alarm using a Math_Expression of ConnectionBpsIngress/connection_bandwidth*100 with a threshold of >90%
3. WHEN the Resource_Based_Config is loaded for Direct Connect, THE Resource_Based_Config SHALL include exactly one egress bandwidth utilization alarm using a Math_Expression of ConnectionBpsEgress/connection_bandwidth*100 with a threshold of >90%
4. THE Resource_Based_Config SHALL support parameterized connection bandwidth capacity for Direct Connect bandwidth calculations

### Requirement 10: Update Deployment Script

**User Story:** As an operations engineer, I want the deployment script updated to reflect the new service list, so that deployment covers exactly the services in the Excel requirements.

#### Acceptance Criteria

1. WHEN the Deployment_Script is executed, THE Deployment_Script SHALL reference only EC2, NAT Gateway, ALB, and VPN as tag-based services
2. WHEN the Deployment_Script is executed, THE Deployment_Script SHALL reference only Kafka, ACM, and Direct Connect as resource-based services
3. WHEN the Deployment_Script discovers resources, THE Deployment_Script SHALL include discovery functions for ACM certificates and Direct Connect connections filtered by tags
4. WHEN the Deployment_Script is executed, THE Deployment_Script SHALL contain zero references to EKS, Redis, RDS, EFS, OpenSearch, RabbitMQ, WAF, or DocumentDB services

### Requirement 11: Update Template Generator

**User Story:** As an operations engineer, I want the template generator updated to support the new resource-based services, so that generated templates match the new configuration.

#### Acceptance Criteria

1. WHEN the Template_Generator is invoked, THE Template_Generator SHALL accept Kafka, ACM, and Direct Connect as valid service choices
2. WHEN the Template_Generator generates alarms with Math_Expression configurations, THE Template_Generator SHALL produce CloudFormation metric math expressions instead of simple Metrics_Insights_SQL queries
3. WHEN the Template_Generator generates Direct Connect bandwidth alarms, THE Template_Generator SHALL accept a connection bandwidth parameter for percentage calculations

### Requirement 12: Delete Obsolete Files

**User Story:** As an operations engineer, I want obsolete files removed from the project, so that the repository contains only relevant code and templates.

#### Acceptance Criteria

1. WHEN the restructuring is complete, THE project SHALL not contain the files: cloudformation-eks-ec2-alarms.yaml, cloudformation-opensearch-alarms-generated.yaml, cloudformation-docdb-alarms-generated.yaml, cloudformation-rabbitmq-alarms-generated.yaml, cloudformation-waf-alarms-generated.yaml, cloudformation-alb-alarms-generated.yaml, cloudformation-kafka-alarms-generated.yaml
2. WHEN the restructuring is complete, THE project SHALL not contain the files: generate-resource-based-template.py, check_resources.py

### Requirement 13: Update Documentation

**User Story:** As an operations engineer, I want the README updated to reflect the new service list and architecture, so that documentation matches the current state of the project.

#### Acceptance Criteria

1. WHEN the restructuring is complete, THE README.md SHALL document the current tag-based services (EC2, NAT Gateway, ALB, VPN) and resource-based services (Kafka, ACM, Direct Connect)
2. WHEN the restructuring is complete, THE README.md SHALL document the CWAgent_Metrics dependency for EC2 memory, disk, and inode monitoring

### Requirement 14: One Alarm Per Metric

**User Story:** As an operations engineer, I want exactly one alarm per metric per service, so that alarm noise is minimized and each metric has a single clear threshold.

#### Acceptance Criteria

1. THE Tag_Based_Template SHALL define exactly one alarm resource per metric per service with no Info/Warning/Critical severity tiers
2. THE Resource_Based_Config SHALL define exactly one alarm entry per metric per service with no multiple severity levels for the same metric
