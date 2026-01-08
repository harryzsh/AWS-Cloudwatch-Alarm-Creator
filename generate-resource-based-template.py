#!/usr/bin/env python3
"""
CDK-based CloudFormation template generator for resource-based alarms.
Generates templates for services that don't support tag-based alarms:
- OpenSearch, MSK (Kafka), AmazonMQ (RabbitMQ), WAF
"""

from aws_cdk import (
    Stack,
    CfnParameter,
    CfnCondition,
    CfnOutput,
    Fn,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    App
)
from constructs import Construct
import yaml
from typing import List, Dict

class ResourceBasedAlarmsStack(Stack):
    """CDK Stack for generating resource-based CloudWatch alarms"""
    
    def __init__(self, scope: Construct, construct_id: str, 
                 service_config: Dict, resource_ids: List[str], **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Parameters
        self.sns_topic_param = CfnParameter(
            self, "SNSTopicArn",
            type="String",
            description="SNS Topic ARN for alarm notifications",
            default=""
        )
        
        # Condition for SNS
        self.has_sns_condition = CfnCondition(
            self, "HasSNSTopic",
            expression=Fn.condition_not(
                Fn.condition_equals(self.sns_topic_param.value_as_string, "")
            )
        )
        
        # Generate alarms for each resource
        alarm_count = 0
        for resource_id in resource_ids:
            for alarm_config in service_config['alarms']:
                self.create_alarm(resource_id, alarm_config, service_config)
                alarm_count += 1
        
        # Outputs
        CfnOutput(
            self, "AlarmCount",
            value=str(alarm_count),
            description="Total number of alarms created"
        )
        
        CfnOutput(
            self, "ServiceType",
            value=service_config['name'],
            description="AWS service type"
        )
    
    def create_alarm(self, resource_id: str, alarm_config: Dict, service_config: Dict):
        """Create a CloudWatch alarm for a specific resource"""
        
        # Clean resource ID for logical ID (remove special characters)
        clean_id = resource_id.replace('/', '').replace(':', '').replace('-', '')
        logical_id = f"{clean_id}{alarm_config['metric']}{alarm_config['severity']}"
        
        # Create metric
        metric = cloudwatch.Metric(
            namespace=service_config['namespace'],
            metric_name=alarm_config['metric'],
            dimensions_map={
                service_config['dimension_name']: resource_id
            },
            statistic=cloudwatch.Stats.AVERAGE,
            period=cloudwatch.Duration.minutes(5)
        )
        
        # Create alarm
        alarm = cloudwatch.Alarm(
            self, logical_id,
            alarm_name=f"{resource_id}-{alarm_config['metric']}-{alarm_config['severity']}",
            alarm_description=alarm_config.get('description', ''),
            metric=metric,
            threshold=alarm_config['threshold'],
            evaluation_periods=2,
            comparison_operator=self._get_comparison_operator(alarm_config['operator']),
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Add SNS action conditionally
        # Note: CDK doesn't support Fn::If directly in alarm actions
        # We'll handle this in the generated template post-processing
    
    def _get_comparison_operator(self, operator_str: str) -> cloudwatch.ComparisonOperator:
        """Convert operator string to CDK enum"""
        operator_map = {
            'GreaterThanThreshold': cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            'LessThanThreshold': cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            'GreaterThanOrEqualToThreshold': cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            'LessThanOrEqualToThreshold': cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
        }
        return operator_map.get(operator_str, cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD)


def load_service_config(config_file: str) -> Dict:
    """Load service configuration from YAML file"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_template(service: str, resource_ids: List[str], config_file: str = 'alarm-config-resource-based.yaml') -> str:
    """Generate CloudFormation template for a service"""
    
    # Load configuration
    all_configs = load_service_config(config_file)
    service_config = all_configs['services'][service]
    
    # Create CDK app and stack
    app = App()
    stack = ResourceBasedAlarmsStack(
        app, f"{service}-alarms",
        service_config=service_config,
        resource_ids=resource_ids
    )
    
    # Synthesize to CloudFormation
    cloud_assembly = app.synth()
    template_path = cloud_assembly.get_stack_by_name(f"{service}-alarms").template_full_path
    
    with open(template_path, 'r') as f:
        template = f.read()
    
    return template


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate resource-based CloudFormation templates using CDK')
    parser.add_argument('--service', required=True, 
                        choices=['opensearch', 'kafka', 'rabbitmq', 'waf'],
                        help='Service type')
    parser.add_argument('--resources', nargs='+', required=True,
                        help='List of resource IDs')
    parser.add_argument('--config', default='alarm-config-resource-based.yaml',
                        help='Service configuration file')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    print(f"Generating {args.service} alarms for {len(args.resources)} resources...")
    
    # Generate template
    template = generate_template(args.service, args.resources, args.config)
    
    # Save template
    output_file = args.output or f'cloudformation-{args.service}-alarms-generated.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"✅ Template saved to: {output_file}")
    print(f"   Resources: {len(args.resources)}")
    print(f"   Service: {args.service}")


if __name__ == '__main__':
    main()
