#!/usr/bin/env python3
"""
Bedrock CloudWatch Alarm Builder

Auto-discovers active Bedrock ModelIds from CloudWatch, merges with
alarm-config-bedrock.yaml overrides, and generates a CloudFormation template.

Logic:
- Auto-discover all ModelIds that have CloudWatch data in AWS/Bedrock namespace
- Load per-model overrides from alarm-config-bedrock.yaml
- For models in overrides: use override alarms (drop from auto-discovered list)
- For remaining auto-discovered models: use default alarms
- Result: no duplicates, overrides always win
"""
import yaml
import hashlib
import boto3
from typing import List, Dict, Tuple


CONFIG_FILE = 'alarm-config-bedrock.yaml'
NAMESPACE = 'AWS/Bedrock'


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _model_logical_id(model_id: str, metric: str, severity: str) -> str:
    """Stable CloudFormation logical ID from model_id + metric + severity."""
    h = hashlib.md5(model_id.encode()).hexdigest()[:8]
    metric_clean = metric.replace('.', '').replace('_', '')
    # Shorten model_id to last segment for readability: anthropic.claude-... → Claude
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


def discover_active_models(region: str) -> List[str]:
    """Discover ModelIds that have active CloudWatch metrics in AWS/Bedrock."""
    print(f"🔍 Auto-discovering active Bedrock models in {region}...")
    cw = boto3.client('cloudwatch', region_name=region)
    paginator = cw.get_paginator('list_metrics')

    model_ids = set()
    for page in paginator.paginate(Namespace=NAMESPACE, Dimensions=[{'Name': 'ModelId'}]):
        for metric in page['Metrics']:
            for dim in metric.get('Dimensions', []):
                if dim['Name'] == 'ModelId':
                    model_ids.add(dim['Value'])

    models = sorted(model_ids)
    print(f"   Found {len(models)} active model(s): {', '.join(models) if models else 'none'}")
    return models


def load_config() -> dict:
    """Load alarm-config-bedrock.yaml."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠ {CONFIG_FILE} not found, using built-in defaults only")
        return {'defaults': [], 'overrides': []}


def build_alarm(model_id: str, alarm_cfg: dict, tag_value: str) -> List[Tuple[str, dict]]:
    """Generate one or two CloudWatch alarm resources for a model+metric."""
    metric = alarm_cfg['metric']
    operator = alarm_cfg['operator']
    description = alarm_cfg.get('description', f'Bedrock {metric} alarm')
    period = alarm_cfg.get('period', 300)
    eval_periods = alarm_cfg.get('evaluation_periods', 2)

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
                'Statistic': 'Sum' if metric in ('Invocations', 'InvocationClientErrors', 'InvocationServerErrors',
                                                  'InputTokenCount', 'OutputTokenCount',
                                                  'EstimatedTPMQuotaUsage') else 'Average',                'Period': period,
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
    """
    Build CloudFormation template for Bedrock alarms.

    Merge logic:
    1. Auto-discover active ModelIds
    2. Load overrides from config
    3. Override models replace auto-discovered ones (no duplicates)
    4. Remaining auto-discovered models get default alarms
    """
    config = load_config()
    defaults = config.get('defaults', [])
    overrides = config.get('overrides') or []

    # Build set of model_ids that have explicit overrides
    override_model_ids = {o['model_id'] for o in overrides}

    # Auto-discover, then remove any that have overrides (override wins)
    discovered = discover_active_models(region)
    auto_models = [m for m in discovered if m not in override_model_ids]

    if override_model_ids:
        print(f"   Override models (yaml): {', '.join(sorted(override_model_ids))}")
    if auto_models:
        print(f"   Auto-discovered models (defaults): {', '.join(auto_models)}")

    resources = {}

    # Auto-discovered models → use defaults
    for model_id in auto_models:
        for alarm_cfg in defaults:
            for logical_id, alarm in build_alarm(model_id, alarm_cfg, tag_value):
                resources[logical_id] = alarm

    # Override models → use their specific alarms
    for override in overrides:
        model_id = override['model_id']
        for alarm_cfg in override.get('alarms', []):
            for logical_id, alarm in build_alarm(model_id, alarm_cfg, tag_value):
                resources[logical_id] = alarm

    alarm_count = len(resources)
    print(f"   Total alarms to deploy: {alarm_count}")

    template = {
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
                'Value': str(len(auto_models) + len(override_model_ids))
            }
        }
    }

    return template


def dump_template(template: dict) -> str:
    return yaml.dump(template, default_flow_style=False, allow_unicode=True,
                     sort_keys=False, Dumper=_NoAliasDumper)
