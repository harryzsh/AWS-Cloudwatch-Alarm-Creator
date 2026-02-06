#!/usr/bin/env python3
"""
Simple CloudFormation template generator for resource-based alarms (no CDK required)

Supports:
- Kafka (MSK): 5 alarms including math expression for memory percentage
- ACM: 1 alarm for certificate expiry
- Direct Connect: 3 alarms including math expressions for bandwidth percentage

Features:
- Math expression support for computed metrics
- Extra dimensions for multi-dimension alarms
- Bandwidth parameter for Direct Connect percentage calculations
"""
import yaml
import argparse


class _NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that disables aliases — CloudFormation doesn't support them."""
    def ignore_aliases(self, data):
        return True


def generate_simple_alarm(service_config, resource_id, alarm_config, alarm_index, tag_value, extra_dim_values=None):
    """Generate alarm using Metrics Insights SQL query (for non-math-expression alarms)"""
    
    metric_name = alarm_config['metric']
    threshold = alarm_config['threshold']
    operator = alarm_config['operator']
    description = alarm_config['description']
    
    # Create valid CloudFormation resource name (alphanumeric only)
    service_name_clean = service_config['name'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    resource_name = f"{service_name_clean}Alarm{alarm_index}"
    
    # Use tag-value based naming with resource name included
    service_short = service_config['name'].split('(')[0].strip().replace(' ', '')  # "MSK" from "MSK (Kafka)"
    alarm_name = f"{tag_value}-{service_short}-{resource_id}-{metric_name}_WARNING"
    
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


def generate_math_expression_alarm(service_config, resource_id, alarm_config, alarm_index, tag_value, bandwidth=None, extra_dim_values=None):
    """Generate alarm using CloudFormation metric math expressions"""
    
    metric_name = alarm_config['metric']
    threshold = alarm_config['threshold']
    operator = alarm_config['operator']
    description = alarm_config['description']
    math_expression = alarm_config['math_expression']
    math_metrics = alarm_config['math_metrics']
    extra_dimensions = alarm_config.get('extra_dimensions', [])
    
    # Create valid CloudFormation resource name (alphanumeric only)
    service_name_clean = service_config['name'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    resource_name = f"{service_name_clean}Alarm{alarm_index}"
    
    # Use tag-value based naming with resource name included
    service_short = service_config['name'].split('(')[0].strip().replace(' ', '')
    alarm_name = f"{tag_value}-{service_short}-{resource_id}-{metric_name}_WARNING"
    
    # Build dimensions list - primary dimension hardcoded with resource_id
    dimensions = [
        {
            'Name': service_config['dimension_name'],
            'Value': resource_id
        }
    ]
    
    # Add extra dimensions if present
    # Note: extra dimensions like Broker ID, Consumer Group need actual values
    # For now, these are placeholder — math expression alarms that need extra dims
    # should be used with specific resource discovery that provides these values
    for dim_name in extra_dimensions:
        dimensions.append({
            'Name': dim_name,
            'Value': 'ALL'
        })
    
    # Build metrics array with MetricStat entries for each math_metric
    metrics = []
    for metric_id, actual_metric_name in math_metrics.items():
        metric_stat_entry = {
            'Id': metric_id,
            'ReturnData': False,
            'MetricStat': {
                'Metric': {
                    'Namespace': service_config['namespace'],
                    'MetricName': actual_metric_name,
                    'Dimensions': dimensions
                },
                'Period': 300,
                'Stat': 'Maximum'
            }
        }
        metrics.append(metric_stat_entry)
    
    # Substitute bandwidth in expression if needed
    expression = math_expression
    if alarm_config.get('bandwidth_parameter') and bandwidth:
        expression = expression.replace('bandwidth', str(bandwidth))
    
    # Add the expression entry
    expression_entry = {
        'Id': 'result',
        'Expression': expression,
        'ReturnData': True
    }
    metrics.append(expression_entry)
    
    alarm = {
        'Type': 'AWS::CloudWatch::Alarm',
        'Properties': {
            'AlarmName': alarm_name,
            'AlarmDescription': description,
            'Metrics': metrics,
            'Threshold': threshold,
            'ComparisonOperator': operator,
            'EvaluationPeriods': 2,
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [{'Ref': 'SNSTopicArn'}]
        }
    }
    
    return resource_name, alarm


def generate_alarm(service_config, resource_id, alarm_config, alarm_index, tag_value, bandwidth=None, extra_dim_values=None):
    """Generate alarm - dispatches to appropriate generator based on alarm type"""
    
    if 'math_expression' in alarm_config:
        return generate_math_expression_alarm(
            service_config, resource_id, alarm_config, alarm_index, tag_value, bandwidth, extra_dim_values
        )
    else:
        return generate_simple_alarm(
            service_config, resource_id, alarm_config, alarm_index, tag_value, extra_dim_values
        )


def get_required_parameters(service_config):
    """Get all required CloudFormation parameters for a service"""
    return {
        'SNSTopicArn': {
            'Type': 'String',
            'Description': 'SNS Topic ARN for alarm notifications',
            'AllowedPattern': 'arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+',
            'ConstraintDescription': 'Must be a valid SNS Topic ARN'
        }
    }


def build_template(service: str, resource_ids: list, tag_value: str, bandwidth: int = None) -> dict:
    """Build a CloudFormation template dict for resource-based alarms.
    
    This is the main API for programmatic use (e.g., from deploy_alarms.py).
    Returns the template as a dict ready for yaml.dump() or direct CloudFormation use.
    """
    with open('alarm-config-resource-based.yaml', 'r', encoding='utf-8', errors='ignore') as f:
        config = yaml.safe_load(f)
    
    service_config = config['services'][service]
    
    # Validate bandwidth for services that need it
    needs_bandwidth = any(a.get('bandwidth_parameter') for a in service_config['alarms'])
    if needs_bandwidth and not bandwidth:
        raise ValueError(
            f'bandwidth is required for {service} (has bandwidth-based math expressions)')
    
    parameters = get_required_parameters(service_config)
    
    template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': f'{service_config["name"]} CloudWatch Alarms',
        'Parameters': parameters,
        'Resources': {}
    }
    
    alarm_index = 0
    for resource_id in resource_ids:
        for alarm_config in service_config['alarms']:
            resource_name, alarm = generate_alarm(
                service_config, resource_id, alarm_config, alarm_index,
                tag_value, bandwidth
            )
            template['Resources'][resource_name] = alarm
            alarm_index += 1
    
    return template


def main():
    parser = argparse.ArgumentParser(description='Generate resource-based alarm template')
    parser.add_argument('--service', required=True, choices=['kafka', 'acm', 'alb', 'directconnect'],
                        help='Service type: kafka, acm, or directconnect')
    parser.add_argument('--tag-value', required=True, help='Tag value for alarm naming')
    parser.add_argument('--resources', nargs='+', required=True, help='Resource IDs')
    parser.add_argument('--bandwidth', type=int, help='Connection bandwidth in bps (auto-detected for directconnect, optional manual override)')
    args = parser.parse_args()
    
    try:
        template = build_template(args.service, args.resources, args.tag_value, args.bandwidth)
    except ValueError as e:
        parser.error(str(e))
    
    # Write template to file (CLI mode only)
    output_file = f'cloudformation-{args.service}-alarms-generated.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False, Dumper=_NoAliasDumper)
    
    alarm_count = len(template['Resources'])
    print(f"Generated {output_file}")
    print(f"   Resources: {len(args.resources)}")
    print(f"   Alarms: {alarm_count}")


if __name__ == '__main__':
    main()
