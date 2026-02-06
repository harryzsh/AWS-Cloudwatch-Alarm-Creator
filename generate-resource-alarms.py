#!/usr/bin/env python3
"""
Simple CloudFormation template generator for resource-based alarms (no CDK required)
"""
import yaml
import argparse

def generate_alarm(service_config, resource_id, alarm_config, alarm_index, tag_value):
    """Generate alarm using Metrics Insights SQL query"""
    
    metric_name = alarm_config['metric']
    severity = alarm_config['severity']
    threshold = alarm_config['threshold']
    operator = alarm_config['operator']
    description = alarm_config['description']
    
    # Create valid CloudFormation resource name (alphanumeric only)
    service_name_clean = service_config['name'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    resource_name = f"{service_name_clean}{severity}Alarm{alarm_index}"
    
    # Use tag-value based naming with resource name included
    service_short = service_config['name'].split('(')[0].strip().replace(' ', '')  # "MSK" from "MSK (Kafka)"
    alarm_name = f"{tag_value}-{service_short}-{resource_id}-{metric_name}-{severity}"
    
    # Use Metrics Insights SQL query
    # Quote metric names with dots to avoid syntax errors
    if '.' in metric_name:
        metric_name_quoted = f'"{metric_name}"'
    else:
        metric_name_quoted = metric_name
    
    # Quote dimension names with spaces
    dimension_name = service_config["dimension_name"]
    if ' ' in dimension_name:
        dimension_name_quoted = f'"{dimension_name}"'
    else:
        dimension_name_quoted = dimension_name
    
    expression = f'SELECT max({metric_name_quoted}) FROM "{service_config["namespace"]}" WHERE {dimension_name_quoted} = \'{resource_id}\''
    
    alarm = {
        'Type': 'AWS::CloudWatch::Alarm',
        'Properties': {
            'AlarmName': alarm_name,
            'AlarmDescription': description,
            'Metrics': [{
                'Id': 'm1',
                'ReturnData': True,
                'Expression': expression,
                'Period': 300
            }],
            'Threshold': threshold,
            'ComparisonOperator': operator,
            'EvaluationPeriods': 2,
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [{'Ref': 'SNSTopicArn'}]
        }
    }
    
    return resource_name, alarm


def main():
    parser = argparse.ArgumentParser(description='Generate resource-based alarm template')
    parser.add_argument('--service', required=True, choices=['opensearch', 'kafka', 'rabbitmq', 'waf', 'docdb', 'alb'])
    parser.add_argument('--tag-value', required=True, help='Tag value for alarm naming')
    parser.add_argument('--resources', nargs='+', required=True, help='Resource IDs')
    args = parser.parse_args()
    
    # Load service configuration
    with open('alarm-config-resource-based.yaml', 'r', encoding='utf-8', errors='ignore') as f:
        config = yaml.safe_load(f)
    
    service_config = config['services'][args.service]
    
    # Build template
    template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': f'{service_config["name"]} CloudWatch Alarms',
        'Parameters': {
            'SNSTopicArn': {
                'Type': 'String',
                'Description': 'SNS Topic ARN for alarm notifications',
                'AllowedPattern': 'arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+',
                'ConstraintDescription': 'Must be a valid SNS Topic ARN'
            }
        },
        'Resources': {}
    }
    
    # Generate alarms for each resource
    alarm_index = 0
    for resource_id in args.resources:
        for alarm_config in service_config['alarms']:
            resource_name, alarm = generate_alarm(service_config, resource_id, alarm_config, alarm_index, args.tag_value)
            template['Resources'][resource_name] = alarm
            alarm_index += 1
    
    # Write template
    output_file = f'cloudformation-{args.service}-alarms-generated.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"Generated {output_file}")
    print(f"   Resources: {len(args.resources)}")
    print(f"   Alarms: {alarm_index}")


if __name__ == '__main__':
    main()
