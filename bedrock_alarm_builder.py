#!/usr/bin/env python3
"""
Bedrock CloudWatch Alarm Builder

Reads alarm-config-bedrock.yaml and generates a CloudFormation template.
Only models explicitly listed under 'models' will have alarms created.
No auto-discovery — full customer control.
"""
import yaml
import hashlib
from typing import List, Tuple


CONFIG_FILE = 'alarm-config-bedrock.yaml'
NAMESPACE = 'AWS/Bedrock'

# Metrics that use Sum statistic (count-based)
SUM_METRICS = {
    'Invocations', 'InvocationClientErrors', 'InvocationServerErrors',
    'InputTokenCount', 'OutputTokenCount', 'EstimatedTPMQuotaUsage'
}


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _model_logical_id(model_id: str, metric: str, severity: str) -> str:
    """Stable CloudFormation logical ID from model_id + metric + severity."""
    h = hashlib.md5(model_id.encode()).hexdigest()[:8]
    metric_clean = metric.replace('.', '').replace('_', '')
    short = model_id.split('.')[-1].split('-')[0].capitalize()
    return f"Bedrock{short}{metric_clean}{h}{severity.capitalize()}"


def _get_thresholds(alarm_config: dict) -> List[Tuple]:
    """Return [(threshold, severity), ...] — one or two tiers."""
    warning = alarm_config.get('threshold_warning', alarm_config.get('threshold'))
    critical = alarm_config.get('threshold_critical')
    tiers = []
    if warning is not None:
        tiers.append((warning, 'WARNING'))
    if critical is not None:
        tiers.append((critical, 'CRITICAL'))
    return tiers


def load_config() -> dict:
    """Load alarm-config-bedrock.yaml."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠ {CONFIG_FILE} not found — no Bedrock alarms will be deployed")
        return {'models': []}


def build_alarm(model_id: str, alarm_cfg: dict, tag_value: str) -> List[Tuple[str, dict]]:
    """Generate one or two CloudWatch alarm resources for a model+metric."""
    metric = alarm_cfg['metric']
    operator = alarm_cfg['operator']
    description = alarm_cfg.get('description', f'Bedrock {metric} alarm')
    period = alarm_cfg.get('period', 300)
    eval_periods = alarm_cfg.get('evaluation_periods', 2)
    statistic = 'Sum' if metric in SUM_METRICS else 'Average'

    results = []
    for threshold, severity in _get_thresholds(alarm_cfg):
        logical_id = _model_logical_id(model_id, metric, severity)
        alarm_name = f"{tag_value}-Bedrock-{model_id}-{metric}-{severity}"

        alarm = {
            'Type': 'AWS::CloudWatch::Alarm',
            'Properties': {
                'AlarmName': alarm_name,
                'AlarmDescription': description,
                'Namespace': NAMESPACE,
                'MetricName': metric,
                'Dimensions': [{'Name': 'ModelId', 'Value': model_id}],
                'Statistic': statistic,
                'Period': period,
                'EvaluationPeriods': eval_periods,
                'Threshold': threshold,
                'ComparisonOperator': operator,
                'TreatMissingData': 'notBreaching',
                'AlarmActions': [{'Ref': 'SNSTopicArn'}],
                'OKActions': [{'Ref': 'SNSTopicArn'}]
            }
        }
        results.append((logical_id, alarm))
    return results


def build_template(tag_value: str, region: str) -> dict:
    """Build CloudFormation template from alarm-config-bedrock.yaml."""
    config = load_config()
    models = config.get('models') or []

    if not models:
        print("   No models configured in alarm-config-bedrock.yaml — skipping")
        return {'Resources': {}}

    print(f"   Configured models: {', '.join(m['model_id'] for m in models)}")

    resources = {}
    for model_entry in models:
        model_id = model_entry['model_id']
        for alarm_cfg in model_entry.get('alarms', []):
            for logical_id, alarm in build_alarm(model_id, alarm_cfg, tag_value):
                resources[logical_id] = alarm

    alarm_count = len(resources)
    print(f"   Total alarms to deploy: {alarm_count}")

    return {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Description': f'Bedrock CloudWatch Alarms - {tag_value}',
        'Parameters': {
            'SNSTopicArn': {
                'Type': 'String',
                'Description': '告警通知的SNS主题ARN',
                'AllowedPattern': 'arn:aws:sns:[a-z0-9-]+:[0-9]{12}:.+',
                'ConstraintDescription': '必须是有效的SNS主题ARN'
            }
        },
        'Resources': resources,
        'Outputs': {
            'AlarmCount': {
                'Description': 'Bedrock告警总数',
                'Value': str(alarm_count)
            },
            'MonitoredModels': {
                'Description': '监控的模型数量',
                'Value': str(len(models))
            }
        }
    }


def dump_template(template: dict) -> str:
    return yaml.dump(template, default_flow_style=False, allow_unicode=True,
                     sort_keys=False, Dumper=_NoAliasDumper)
