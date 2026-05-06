#!/usr/bin/env python3
"""
CloudFormation template generator for resource-based alarms.

Emits STANDARD CloudWatch alarms (not Metrics Insights) so they count against
the 5000+/region alarm quota instead of the 200/region Metrics Insights quota.

Sub-resource fan-out: Kafka per-broker metrics and DocDB per-instance metrics
publish with multiple dimensions (Cluster Name+Broker ID, DBClusterIdentifier+
DBInstanceIdentifier). A plain single-dimension standard alarm wouldn't find
those metrics. So the generator accepts a list of sub-resources per resource
and emits one alarm per (resource, sub_resource) pair for scope=broker/instance.

Tag-based templates (tag-based-alarms.yaml / eks-ec2-alarms.yaml) still use
Metrics Insights because they need GROUP BY tag.Name.
"""
import argparse
import json
import re
import yaml


def _logical_id(value: str) -> str:
    """CloudFormation logical IDs are alphanumeric. Strip everything else."""
    return re.sub(r'[^A-Za-z0-9]', '', value) or 'X'


def _service_short_name(service_config: dict) -> str:
    """Turn 'MSK (Kafka)' -> 'MSK', 'Application Load Balancer' -> 'ApplicationLoadBalancer'."""
    return service_config['name'].split('(')[0].strip().replace(' ', '')


def _build_dimensions(service_config, resource_id, sub_resource=None, sub_dimension_name=None):
    """Return a CFN Dimensions list for a single alarm."""
    dims = [{'Name': service_config['dimension_name'], 'Value': resource_id}]

    if sub_resource is not None:
        if not sub_dimension_name:
            raise ValueError("sub_dimension_name is required when sub_resource is set")
        dims.append({'Name': sub_dimension_name, 'Value': sub_resource})

    for extra in service_config.get('extra_dimensions', []) or []:
        if 'value' in extra:
            dims.append({'Name': extra['name'], 'Value': extra['value']})
        elif extra.get('source') == 'stack_region':
            # Auto-resolve to the stack's deployment region via pseudo-param.
            dims.append({'Name': extra['name'], 'Value': {'Ref': 'AWS::Region'}})
        else:
            raise ValueError(
                f"extra_dimension '{extra.get('name')}' must have 'value' or "
                f"'source: stack_region'"
            )
    return dims


def _build_alarm(service_config, tag_value, resource_id, alarm_cfg,
                 logical_id, sub_resource=None, sub_dimension_name=None):
    """Construct one AWS::CloudWatch::Alarm CFN resource dict."""
    metric_name = alarm_cfg['metric']
    severity = alarm_cfg['severity']
    statistic = alarm_cfg.get('statistic', 'Maximum')
    # Config uses lowercase 'sum' sometimes; normalise to CFN form.
    statistic_map = {'sum': 'Sum', 'avg': 'Average', 'min': 'Minimum',
                     'max': 'Maximum', 'count': 'SampleCount'}
    statistic = statistic_map.get(statistic.lower(), statistic.capitalize())

    service_short = _service_short_name(service_config)

    # Alarm name: TSP-{tag}-{service}-{resource}[-{sub}]-{metric}-{severity}
    name_parts = ['TSP', tag_value, service_short, resource_id]
    if sub_resource is not None:
        name_parts.append(sub_resource)
    name_parts.append(metric_name)
    name_parts.append(severity)
    alarm_name = '-'.join(name_parts)

    dimensions = _build_dimensions(
        service_config, resource_id,
        sub_resource=sub_resource,
        sub_dimension_name=sub_dimension_name,
    )

    return {
        'Type': 'AWS::CloudWatch::Alarm',
        'Properties': {
            'AlarmName': alarm_name,
            'AlarmDescription': alarm_cfg['description'],
            'Namespace': service_config['namespace'],
            'MetricName': metric_name,
            'Dimensions': dimensions,
            'Statistic': statistic,
            'Period': 300,
            'EvaluationPeriods': 2,
            'Threshold': alarm_cfg['threshold'],
            'ComparisonOperator': alarm_cfg['operator'],
            'TreatMissingData': 'notBreaching',
            'AlarmActions': [{'Ref': 'SNSTopicArn'}],
        },
    }


# Sub-dimension name per service. Only Kafka and DocDB actually fan out;
# other services use scope=cluster (default) and don't need this.
SUB_DIMENSION = {
    'kafka': 'Broker ID',
    'docdb': 'DBInstanceIdentifier',
}


def generate_template(service_key, service_config, tag_value, resources):
    """
    resources: dict mapping resource_id -> list of sub-resources (or [] if none)
               e.g. {'my-cluster': ['1', '2', '3']} for Kafka brokers
                    {'my-docdb': ['inst-1', 'inst-2']} for DocDB instances
                    {'my-alb': []} for single-scope resources
    """
    template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': f'{service_config["name"]} CloudWatch Alarms (standard)',
        'Parameters': {
            'SNSTopicArn': {
                'Type': 'String',
                'Description': 'SNS Topic ARN for alarm notifications',
                'AllowedPattern': 'arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+',
                'ConstraintDescription': 'Must be a valid SNS Topic ARN',
            },
        },
        'Resources': {},
    }

    service_short = _service_short_name(service_config)
    sub_dim = SUB_DIMENSION.get(service_key)
    alarm_index = 0

    for resource_id, sub_resources in resources.items():
        for alarm_cfg in service_config['alarms']:
            scope = alarm_cfg.get('scope', 'cluster')

            if scope == 'cluster' or not sub_resources:
                # One alarm per resource.
                logical_id = (f"{_logical_id(service_short)}"
                              f"{_logical_id(resource_id)[:30]}"
                              f"{alarm_cfg['severity']}"
                              f"A{alarm_index}")
                alarm = _build_alarm(
                    service_config, tag_value, resource_id, alarm_cfg, logical_id,
                )
                template['Resources'][logical_id] = alarm
                alarm_index += 1
            else:
                # Fan out: one alarm per (resource, sub_resource).
                for sub in sub_resources:
                    logical_id = (f"{_logical_id(service_short)}"
                                  f"{_logical_id(resource_id)[:20]}"
                                  f"{_logical_id(sub)[:10]}"
                                  f"{alarm_cfg['severity']}"
                                  f"A{alarm_index}")
                    alarm = _build_alarm(
                        service_config, tag_value, resource_id, alarm_cfg, logical_id,
                        sub_resource=sub, sub_dimension_name=sub_dim,
                    )
                    template['Resources'][logical_id] = alarm
                    alarm_index += 1

    return template, alarm_index


def _parse_resources_arg(raw_list):
    """Turn --resources args into the resources dict.

    Each arg is either:
      'resource_id'                           (no sub-resources)
      'resource_id:sub1,sub2,sub3'            (fan-out)
      'resource_id:JSON_LIST'                 (JSON list of sub-resources)
    """
    result = {}
    for entry in raw_list:
        if ':' in entry:
            resource_id, subs_part = entry.split(':', 1)
            if subs_part.startswith('['):
                subs = json.loads(subs_part)
            else:
                subs = [s for s in subs_part.split(',') if s]
        else:
            resource_id, subs = entry, []
        result[resource_id] = subs
    return result


def main():
    parser = argparse.ArgumentParser(description='Generate resource-based alarm template')
    parser.add_argument(
        '--service', required=True,
        choices=['opensearch', 'kafka', 'rabbitmq', 'waf', 'docdb', 'alb'],
    )
    parser.add_argument('--tag-value', required=True, help='Tag value for alarm naming')
    parser.add_argument(
        '--resources', nargs='+', required=True,
        help=('Resource identifiers. Use plain IDs for non-fanout services, '
              'or "ID:sub1,sub2" / "ID:[\\"sub1\\",\\"sub2\\"]" for Kafka/DocDB.'),
    )
    args = parser.parse_args()

    with open('alarm-config-resource-based.yaml', 'r', encoding='utf-8', errors='ignore') as f:
        config = yaml.safe_load(f)

    service_config = config['services'][args.service]
    resources = _parse_resources_arg(args.resources)
    template, alarm_count = generate_template(
        args.service, service_config, args.tag_value, resources,
    )

    output_file = f'cloudformation-{args.service}-alarms-generated.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Generated {output_file}")
    print(f"   Resources: {len(resources)}")
    print(f"   Alarms: {alarm_count} (standard CloudWatch alarms)")


if __name__ == '__main__':
    main()
