# Implementation Plan: Tag-Based CloudWatch Alarms

## Overview

This implementation plan converts the current per-resource alarm system to a hybrid tag-based + resource-based system, reducing from 500+ stacks to just 5 stacks and cutting alarm count by 55%.

## Tasks

- [x] 1. Create unified tag-based CloudFormation template
  - Create single template with all 7 services (EC2, RDS MySQL/PG, Redis, DocumentDB, EFS, ALB)
  - Include 162 tag-based alarms total
  - Support parameterized tag key/value filtering
  - Include SNS topic integration
  - _Requirements: 1.1, 1.2, 1.4, 3.1, 5.4, 6.1, 6.2, 6.3, 6.4_

- [ ]* 1.1 Write property test for tag-based alarm automatic monitoring
  - **Property 1: Tag-Based Alarm Automatic Monitoring**
  - **Validates: Requirements 1.3**

- [ ]* 1.2 Write property test for alarm count per tag group
  - **Property 2: Alarm Count Per Tag Group**
  - **Validates: Requirements 1.4**

- [x] 2. Create CDK-based template generator for resource-based services
  - [x] 2.1 Implement CDK stack class for dynamic alarm generation
    - Support OpenSearch, Kafka, RabbitMQ, WAF
    - Generate alarms based on service configuration
    - _Requirements: 3.2, 3.3_

  - [x] 2.2 Create service configuration file (YAML)
    - Define alarm configs for each service
    - Include thresholds, metrics, namespaces
    - _Requirements: 3.3, 6.1, 6.2, 6.3_

  - [ ]* 2.3 Write property test for resource-based alarm count
    - **Property 3: Resource-Based Alarm Count**
    - **Validates: Requirements 2.2**

  - [ ]* 2.4 Write property test for CloudFormation resource limit
    - **Property 4: CloudFormation Resource Limit**
    - **Validates: Requirements 2.4**

- [x] 3. Implement deployment script (deploy-alarms-v2.py)
  - [x] 3.1 Implement tag-based deployment function
    - Deploy unified tag-based stack
    - Support tag key/value parameters
    - _Requirements: 4.1, 4.2_

  - [x] 3.2 Implement resource-based deployment function
    - Generate CDK template
    - Deploy per-service stacks
    - _Requirements: 4.1, 4.3_

  - [x] 3.3 Implement resource discovery
    - Auto-discover resources by service type
    - Support tag filtering
    - Handle multiple regions
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 3.4 Implement CLI interface
    - Support --service, --mode, --tag-key, --tag-value, --sns-topic flags
    - Support --discover-all flag
    - _Requirements: 4.1_

  - [ ]* 3.5 Write property test for idempotent deployment
    - **Property 6: Idempotent Deployment**
    - **Validates: Requirements 4.4**

  - [ ]* 3.6 Write property test for stack naming convention
    - **Property 7: Stack Naming Convention**
    - **Validates: Requirements 5.2**

- [x] 4. Implement error handling
  - [x] 4.1 Add CloudFormation limit validation
    - Check resource count before deployment
    - Provide clear error message with guidance
    - _Requirements: 8.2_

  - [x] 4.2 Add resource discovery error handling
    - Handle missing resources gracefully
    - Handle API throttling with retries
    - _Requirements: 7.4, 8.1_

  - [x] 4.3 Add template validation
    - Validate templates before deployment
    - Check prerequisites (credentials, boto3)
    - _Requirements: 3.4, 8.3_

  - [x] 4.4 Add deployment summary reporting
    - Show created/updated/failed counts
    - Display error details for failures
    - _Requirements: 8.4_

- [ ] 5. Checkpoint - Ensure core functionality works
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 6. Write property tests for configuration preservation
  - [ ]* 6.1 Write property test for threshold preservation
    - **Property 5: Configuration Preservation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [ ]* 6.2 Write property test for SNS integration
    - **Property 8: SNS Integration**
    - **Validates: Requirements 5.4**

- [ ]* 7. Write property tests for resource discovery
  - [ ]* 7.1 Write property test for discovery completeness
    - **Property 9: Resource Discovery Completeness**
    - **Validates: Requirements 7.1**

  - [ ]* 7.2 Write property test for tag filtering
    - **Property 10: Tag Filtering**
    - **Validates: Requirements 7.2**

  - [ ]* 7.3 Write property test for stack count
    - **Property 11: Stack Count**
    - **Validates: Requirements 5.3**

- [x] 8. Create documentation
  - [x] 8.1 Update README.md
    - Document new architecture
    - Add tag-based vs resource-based comparison
    - Include deployment examples
    - _Requirements: 9.1, 9.3_

  - [x] 8.2 Update QUICK_REFERENCE.md
    - Add new deployment commands
    - Update stack naming conventions
    - _Requirements: 9.2_

  - [x] 8.3 Create MIGRATION_GUIDE.md
    - Document migration steps
    - Include rollback procedures
    - Add troubleshooting tips
    - _Requirements: 9.4, 10.1, 10.2, 10.3, 10.4_

  - [x] 8.4 Create USAGE_EXAMPLES.md
    - Add examples for all 11 services
    - Include tag-based and resource-based examples
    - _Requirements: 9.1_

- [ ] 9. Testing and validation
  - [ ]* 9.1 Run all property tests
    - Execute all 11 property tests
    - Ensure minimum 100 iterations each
    - Fix any failures

  - [ ] 9.2 Integration test in development environment
    - Deploy tag-based stack
    - Deploy resource-based stacks
    - Verify alarms are created correctly
    - Test with actual AWS resources

  - [ ] 9.3 Validate alarm functionality
    - Trigger test alarms
    - Verify SNS notifications
    - Check CloudWatch console

- [ ] 10. Final checkpoint - Production readiness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each property test should run with minimum 100 iterations
- Tag-based template is the highest priority (biggest impact)
- CDK generator can be implemented incrementally (one service at a time)
- Migration should be done service by service, not all at once
- Keep old templates as backup during migration
