# Implementation Plan: Restructure CloudWatch Alarms

## Overview

Restructure the CloudWatch alarms project to match the Excel requirements. Work proceeds in phases: delete obsolete files, rewrite tag-based template, rewrite resource-based config, update template generator, update deployment script, update README, and validate.

## Tasks

- [x] 1. Delete obsolete files
  - Delete `cloudformation-eks-ec2-alarms.yaml`, `cloudformation-opensearch-alarms-generated.yaml`, `cloudformation-docdb-alarms-generated.yaml`, `cloudformation-rabbitmq-alarms-generated.yaml`, `cloudformation-waf-alarms-generated.yaml`, `cloudformation-alb-alarms-generated.yaml`, `cloudformation-kafka-alarms-generated.yaml`, `generate-resource-based-template.py`, `check_resources.py`
  - _Requirements: 12.1, 12.2_

- [x] 2. Rewrite tag-based CloudFormation template
  - [x] 2.1 Rewrite `cloudformation-tag-based-alarms.yaml` with exactly 10 alarms
    - EC2: CPUUtilization (AWS/EC2, >90), mem_used_percent (CWAgent, >90), disk_used_percent (CWAgent, >90), disk_inodes_used_percent (CWAgent, >90), StatusCheckFailed_System (AWS/EC2, >=1), StatusCheckFailed (AWS/EC2, >=1)
    - NAT Gateway: ErrorPortAllocation (AWS/NATGateway, >100)
    - ALB: UnHealthyHostCount (AWS/ApplicationELB, >=1)
    - VPN: TunnelState connection-level (AWS/VPN, <1), TunnelState tunnel-level (AWS/VPN, <1 with VpnId+TunnelIpAddress)
    - All alarms use Metrics Insights SQL with tag filtering, one alarm per metric, no severity tiers
    - Parameters: TagKey, TagValue, SNSTopicArn
    - _Requirements: 1.1, 1.2, 3.1-3.7, 4.1-4.2, 5.1-5.2, 6.1-6.2, 14.1_

  - [ ]* 2.2 Write property tests for tag-based template
    - **Property 1: Tag-based template namespace allowlist**
    - **Validates: Requirements 1.2**
    - **Property 4: One alarm per metric in tag-based template**
    - **Validates: Requirements 14.1**

  - [ ]* 2.3 Write unit tests for tag-based template alarm definitions
    - Verify each of the 10 alarms exists with correct namespace, metric, threshold, operator
    - Verify zero NetworkIn/NetworkOut alarms exist
    - Verify zero Redis/RDS/EFS alarms exist
    - _Requirements: 3.1-3.7, 4.1, 5.1, 6.1-6.2_

- [x] 3. Rewrite resource-based alarm config
  - [x] 3.1 Rewrite `alarm-config-resource-based.yaml` with Kafka (5 alarms), ACM (1 alarm), Direct Connect (3 alarms)
    - Add `math_expression`, `math_metrics`, `extra_dimensions`, `bandwidth_parameter` fields where needed
    - Kafka: MaxOffsetLag, CpuUser, MemoryPercent (math), KafkaDataLogsDiskUsed, ActiveControllerCount
    - ACM: DaysToExpiry
    - Direct Connect: ConnectionState, IngressBandwidthPercent (math), EgressBandwidthPercent (math)
    - _Requirements: 2.1, 2.2, 5.3, 7.1-7.6, 8.1, 9.1-9.4, 14.2_

  - [ ]* 3.2 Write property test for resource-based config
    - **Property 5: One alarm per metric in resource-based config**
    - **Validates: Requirements 14.2**

  - [ ]* 3.3 Write unit tests for resource-based config
    - Verify exactly 3 services exist (kafka, acm, directconnect)
    - Verify Kafka has exactly 5 alarms with correct metrics and thresholds
    - Verify ACM has DaysToExpiry with threshold 30
    - Verify Direct Connect has 3 alarms with correct math expressions
    - _Requirements: 2.2, 7.1-7.6, 8.1, 9.1-9.4_

- [x] 4. Checkpoint - Validate templates
  - Validate `cloudformation-tag-based-alarms.yaml` with cfn-lint using aws-infrastructure-as-code power
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Update template generator
  - [x] 5.1 Update `generate-resource-alarms-simple.py`
    - Change service choices to `kafka`, `acm`, `directconnect`
    - Add math expression support: when `math_expression` is present in alarm config, generate CloudFormation `Metrics` array with `MetricStat` entries for each `math_metrics` ID and an `Expression` entry
    - Add `--bandwidth` CLI argument for Direct Connect percentage calculations
    - Handle `extra_dimensions` for multi-dimension alarms
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ]* 5.2 Write property test for template generator math expressions
    - **Property 3: Math expression template generation**
    - **Validates: Requirements 11.2**

  - [ ]* 5.3 Write unit tests for template generator
    - Test generating a Kafka template with math expression alarm produces correct CloudFormation structure
    - Test generating a Direct Connect template with bandwidth parameter
    - Test generating an ACM template
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 6. Update deployment script
  - [x] 6.1 Update `deploy-cloudwatch-alarms.py`
    - Update `TAG_BASED_SERVICES` to `['ec2', 'nat-gateway', 'alb', 'vpn']`
    - Update `RESOURCE_BASED_SERVICES` to `['kafka', 'acm', 'directconnect']`
    - Add `discover_acm_certificates()` function using `boto3.client('acm')`
    - Add `discover_dx_connections()` function using `boto3.client('directconnect')`
    - Remove EKS discovery and deployment functions
    - Remove all references to removed services (redis, rds, efs, opensearch, rabbitmq, waf, docdb, eks)
    - Update `validate_prerequisites()` to check for current files only
    - Update alarm count references
    - _Requirements: 10.1-10.4, 8.2_

  - [ ]* 6.2 Write property test for deployment script
    - **Property 2: No removed service references in deployment script**
    - **Validates: Requirements 10.4**

  - [ ]* 6.3 Write unit tests for deployment script
    - Verify TAG_BASED_SERVICES and RESOURCE_BASED_SERVICES constants
    - Verify discover_resources handles 'acm' and 'directconnect'
    - _Requirements: 10.1-10.3_

- [x] 7. Update README
  - Update `README.md` to document current tag-based services (EC2, NAT Gateway, ALB, VPN), resource-based services (Kafka, ACM, Direct Connect), CWAgent dependency, and updated usage examples
  - _Requirements: 13.1, 13.2_

- [x] 8. Final checkpoint - Validate and verify
  - Validate rewritten CloudFormation template with cfn-lint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis` library (Python) with minimum 100 iterations
- CloudFormation validation uses the aws-infrastructure-as-code Kiro Power
