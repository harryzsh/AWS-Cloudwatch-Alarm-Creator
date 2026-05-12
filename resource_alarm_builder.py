#!/usr/bin/env python3
"""
Simple CloudFormation template generator for resource-based alarms (no CDK required)

Supports:
- EC2 (CWAgent): mem_used_percent, disk_used_percent
- Kafka (MSK): 5 alarms including math expression for memory percentage
- ACM: 1 alarm for certificate expiry
- ALB / NLB: UnHealthyHostCount
- Direct Connect: 3 alarms including math expressions for bandwidth percentage
- EBS: throughput / IOPS / stalled IO checks
- EFS: PercentIOLimit
- NAT: PacketsDropCount, ErrorPortAllocation

Dual-severity support:
- If an alarm config has threshold_warning + threshold_critical, TWO alarms are generated:
    <name>-WARNING  (threshold_warning)
    <name>-CRITICAL (threshold_critical)
- If only threshold_warning (or legacy threshold) is present, ONE -WARNING alarm is generated.
"""
import yaml
import argparse
import hashlib


class _NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that disables aliases �?CloudFormation doesn't support them."""
    def ignore_aliases(self, data):
        return True


def _stable_resource_name(service_name_clean, resource_id, metric_name, severity):
    """Generate a stable CloudFormation logical ID from resource_id + metric + severity."""
    resource_hash = hashlib.md5(resource_id.encode()).hexdigest()[:8]
    metric_clean = metric_name.replace('.', '').replace('_', '')
    return f"{service_name_clean}{metric_clean}{resource_hash}{severity.capitalize()}"


def _get_thresholds(alarm_config):
    """Return list of (threshold, severity) tuples from alarm config.
    
    Supports:
    - threshold_warning + threshold_critical -> two alarms
    - threshold_warning only               -> one -WARNING alarm
    - legacy threshold key                 -> one -WARNING alarm
    """
    warning = alarm_config.get('threshold_warning', alarm_config.get('threshold'))
    critical = alarm_config.get('threshold_critical')

    tiers = []
    if warning is not None:
        tiers.append((warning, 'WARNING'))
    if critical is not None:
        tiers.append((critical, 'CRITICAL'))
    return tiers


def _build_alarm_props(alarm_name, description, metrics, threshold, operator):
    return {
        'Type': 'AWS::CloudWatch::Alarm',
        'Properties': {
            'AlarmName': alarm_name,
            'AlarmDescription': description,
            'Metrics': metrics,
            'Threshold': threshold,
            'ComparisonOperator': operator,
            'EvaluationPeriods': 2,
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [{'Ref': 'SNSTopicArn'}],
            'OKActions': [{'Ref': 'SNSTopicArn'}]
        }
    }


def generate_simple_alarm(service_config, resource_id, alarm_config, tag_value, extra_dim_values=None):
    """Generate alarms using standard MetricStat (not Metrics Insights SQL).
    Uses explicit resource dimension — does not count toward Metrics Insights quota."""

    metric_name = alarm_config['metric']
    operator = alarm_config['operator']
    description = alarm_config['description']

    service_name_clean = service_config['name'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    service_short = service_config['name'].split('(')[0].strip().replace(' ', '')

    dimension_name = service_config['dimension_name']

    query_id = resource_id
    display_id = resource_id
    if '|' in resource_id:
        display_id, query_id = resource_id.split('|', 1)

    results = []
    for threshold, severity in _get_thresholds(alarm_config):
        resource_name = _stable_resource_name(service_name_clean, resource_id, metric_name, severity)
        alarm_name = f"{tag_value}-{service_short}-{display_id}-{metric_name}-{severity}"

        alarm = {
            'Type': 'AWS::CloudWatch::Alarm',
            'Properties': {
                'AlarmName': alarm_name,
                'AlarmDescription': description,
                'Namespace': service_config['namespace'],
                'MetricName': metric_name,
                'Dimensions': [{'Name': dimension_name, 'Value': query_id}],
                'Statistic': 'Maximum',
                'Period': 300,
                'Threshold': threshold,
                'ComparisonOperator': operator,
                'EvaluationPeriods': 2,
                'TreatMissingData': 'notBreaching',
                'AlarmActions': [{'Ref': 'SNSTopicArn'}],
                'OKActions': [{'Ref': 'SNSTopicArn'}]
            }
        }
        results.append((resource_name, alarm))

    return results


def generate_math_expression_alarm(service_config, resource_id, alarm_config, tag_value, bandwidth=None, extra_dim_values=None):
    """Generate alarms using CloudFormation metric math expressions. Returns list of (resource_name, alarm)."""

    metric_name = alarm_config['metric']
    operator = alarm_config['operator']
    description = alarm_config['description']
    math_expression = alarm_config['math_expression']
    math_metrics = alarm_config['math_metrics']
    extra_dimensions = alarm_config.get('extra_dimensions', [])

    service_name_clean = service_config['name'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    service_short = service_config['name'].split('(')[0].strip().replace(' ', '')

    dimensions = [{'Name': service_config['dimension_name'], 'Value': resource_id}]
    for dim_name in extra_dimensions:
        dimensions.append({'Name': dim_name, 'Value': 'ALL'})

    # Build MetricStat entries
    metric_stats = []
    for metric_id, actual_metric_name in math_metrics.items():
        metric_stats.append({
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
        })

    expression = math_expression
    if alarm_config.get('bandwidth_parameter') and bandwidth:
        expression = expression.replace('bandwidth', str(bandwidth))

    results = []
    for threshold, severity in _get_thresholds(alarm_config):
        resource_name = _stable_resource_name(service_name_clean, resource_id, metric_name, severity)
        alarm_name = f"{tag_value}-{service_short}-{resource_id}-{metric_name}-{severity}"
        metrics = metric_stats + [{'Id': 'result', 'Expression': expression, 'ReturnData': True}]
        alarm = _build_alarm_props(alarm_name, description, metrics, threshold, operator)
        results.append((resource_name, alarm))

    return results


def generate_alarm(service_config, resource_id, alarm_config, tag_value, bandwidth=None, extra_dim_values=None):
    """Dispatch to appropriate generator. Returns list of (resource_name, alarm)."""
    if 'math_expression' in alarm_config:
        return generate_math_expression_alarm(
            service_config, resource_id, alarm_config, tag_value, bandwidth, extra_dim_values
        )
    return generate_simple_alarm(service_config, resource_id, alarm_config, tag_value, extra_dim_values)


def get_required_parameters(service_config):
    return {
        'SNSTopicArn': {
            'Type': 'String',
            'Description': 'SNS Topic ARN for alarm notifications',
            'AllowedPattern': 'arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+',
            'ConstraintDescription': 'Must be a valid SNS Topic ARN'
        }
    }


def build_template(service: str, resource_ids: list, tag_value: str, bandwidth: int = None) -> dict:
    """Build a CloudFormation template dict for resource-based alarms."""
    with open('alarm-config-resource-based.yaml', 'r', encoding='utf-8', errors='ignore') as f:
        config = yaml.safe_load(f)

    service_config = config['services'][service]

    needs_bandwidth = any(a.get('bandwidth_parameter') for a in service_config['alarms'])
    if needs_bandwidth and not bandwidth:
        raise ValueError(f'bandwidth is required for {service} (has bandwidth-based math expressions)')

    parameters = get_required_parameters(service_config)

    template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': f'{service_config["name"]} CloudWatch Alarms',
        'Parameters': parameters,
        'Resources': {}
    }

    for resource_id in resource_ids:
        for alarm_config in service_config['alarms']:
            for resource_name, alarm in generate_alarm(
                service_config, resource_id, alarm_config, tag_value, bandwidth
            ):
                template['Resources'][resource_name] = alarm

    return template


def main():
    valid_services = ['ec2', 'kafka', 'acm', 'alb', 'nlb', 'directconnect', 'ebs', 'efs', 'nat']
    parser = argparse.ArgumentParser(description='Generate resource-based alarm template')
    parser.add_argument('--service', required=True, choices=valid_services,
                        help=f'Service type: {", ".join(valid_services)}')
    parser.add_argument('--tag-value', required=True, help='Tag value for alarm naming')
    parser.add_argument('--resources', nargs='+', required=True, help='Resource IDs')
    parser.add_argument('--bandwidth', type=int, help='Connection bandwidth in bps (required for directconnect)')
    args = parser.parse_args()

    try:
        template = build_template(args.service, args.resources, args.tag_value, args.bandwidth)
    except ValueError as e:
        parser.error(str(e))

    output_file = f'cloudformation-{args.service}-alarms-generated.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False, Dumper=_NoAliasDumper)

    alarm_count = len(template['Resources'])
    print(f"Generated {output_file}")
    print(f"   Resources: {len(args.resources)}")
    print(f"   Alarms: {alarm_count}")


if __name__ == '__main__':
    main()
