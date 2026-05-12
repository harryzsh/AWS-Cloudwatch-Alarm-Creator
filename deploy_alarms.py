#!/usr/bin/env python3
"""
Unified CloudWatch Alarms Deployment Script
Supports both tag-based and resource-based alarm deployment.

Tag-Based Services (3): EC2, NAT Gateway, VPN
Resource-Based Services (4): Kafka, ACM, ALB, Direct Connect
"""

import boto3
import yaml
import sys
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import resource_alarm_builder
import bedrock_alarm_builder


class _NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that disables aliases — CloudFormation doesn't support them."""
    def ignore_aliases(self, data):
        return True

# Service configuration
# Tag-based: EC2, NAT Gateway, VPN (deployed via cloudformation-tag-based-alarms.yaml)
# Resource-based: Kafka, ACM, ALB, Direct Connect (generated per-resource by resource_alarm_builder)
TAG_BASED_SERVICES = ['ec2', 'nat-gateway', 'vpn']
RESOURCE_BASED_SERVICES = ['ec2', 'kafka', 'acm', 'alb', 'nlb', 'directconnect', 'ebs', 'efs', 'bedrock']

# ANSI color codes for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

@dataclass
class DeploymentResult:
    service: str
    stack_name: str
    status: str  # 'created', 'updated', 'failed', 'no-change'
    alarm_count: int
    resource_count: int
    error_message: Optional[str] = None


def validate_prerequisites():
    """Validate all prerequisites before deployment"""
    
    print("🔍 Validating prerequisites...")
    errors = []
    
    # Check boto3
    try:
        import boto3
        print("   ✓ boto3 installed")
    except ImportError:
        errors.append("boto3 not installed. Run: pip install boto3")
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"   ✓ AWS credentials configured (Account: {identity['Account']})")
    except Exception as e:
        errors.append(f"AWS credentials not configured: {e}")
    
    # Check required files
    required_files = [
        'cloudformation-tag-based-alarms.yaml',
        'alarm-config-resource-based.yaml',
        'resource_alarm_builder.py',
        'bedrock_alarm_builder.py'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✓ {file} found")
        else:
            errors.append(f"Required file not found: {file}")
    
    if errors:
        print("\n❌ Prerequisites check failed:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    print("   ✓ All prerequisites met\n")


def upload_template_to_s3(template_body: str, template_name: str, region: str) -> str:
    """Upload large template to S3 and return URL"""
    
    s3 = boto3.client('s3', region_name=region)
    sts = boto3.client('sts', region_name=region)
    account_id = sts.get_caller_identity()['Account']
    
    # Create bucket name
    bucket_name = f'cloudformation-templates-{account_id}-{region}'
    
    try:
        # Create bucket if it doesn't exist
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"   Using existing S3 bucket: {bucket_name}")
        except:
            print(f"   Creating S3 bucket: {bucket_name}")
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            
            # Enable versioning
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
        
        # Upload template
        key = f'templates/{template_name}'
        print(f"   Uploading template to S3: s3://{bucket_name}/{key}")
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=template_body.encode('utf-8'),
            ContentType='text/yaml'
        )
        
        # Return URL
        template_url = f'https://{bucket_name}.s3.{region}.amazonaws.com/{key}'
        return template_url
    
    except Exception as e:
        print(f"✗ Error uploading to S3: {e}")
        raise


def deploy_tag_based_alarms(tag_key: str, tag_value: str, sns_topic: str, 
                            region: str, stack_name: str = None) -> DeploymentResult:
    """Deploy unified tag-based alarms stack"""
    
    cfn = boto3.client('cloudformation', region_name=region)
    
    if not stack_name:
        stack_name = f'tag-based-alarms-{tag_value.lower()}'
    
    template_file = 'cloudformation-tag-based-alarms.yaml'
    
    print(f"📦 Deploying tag-based alarms...")
    print(f"   Stack: {stack_name}")
    print(f"   Tag Filter: {tag_key}={tag_value}")
    
    try:
        # Read template
        with open(template_file, 'r', encoding='utf-8', errors='ignore') as f:
            template_body = f.read()
        
        # Check template size
        template_size = len(template_body.encode('utf-8'))
        print(f"   Template size: {template_size:,} bytes")
        
        # Use S3 if template is too large (> 51,200 bytes)
        use_s3 = template_size > 51200
        
        if use_s3:
            print(f"   Template exceeds 51KB limit, uploading to S3...")
            template_url = upload_template_to_s3(
                template_body, 
                f'{stack_name}.yaml',
                region
            )
        
        # Build parameters (all required)
        parameters = [
            {'ParameterKey': 'TagKey', 'ParameterValue': tag_key},
            {'ParameterKey': 'TagValue', 'ParameterValue': tag_value},
            {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
        ]
        
        # Prepare stack arguments
        stack_args = {
            'StackName': stack_name,
            'Parameters': parameters
        }
        
        if use_s3:
            stack_args['TemplateURL'] = template_url
        else:
            stack_args['TemplateBody'] = template_body
        
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=stack_name)
            print(f"   Stack exists, updating...")
            
            try:
                cfn.update_stack(**stack_args)
                print(f"✓ Stack update initiated")
                return DeploymentResult(
                    service='tag-based',
                    stack_name=stack_name,
                    status='updated',
                    alarm_count=10,
                    resource_count=4
                )
            except cfn.exceptions.ClientError as e:
                if 'No updates are to be performed' in str(e):
                    print(f"  No changes needed")
                    return DeploymentResult(
                        service='tag-based',
                        stack_name=stack_name,
                        status='no-change',
                        alarm_count=10,
                        resource_count=4
                    )
                raise
        
        except cfn.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                print(f"   Creating new stack...")
                cfn.create_stack(**stack_args)
                print(f"✓ Stack creation initiated")
                return DeploymentResult(
                    service='tag-based',
                    stack_name=stack_name,
                    status='created',
                    alarm_count=10,
                    resource_count=4
                )
            raise
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return DeploymentResult(
            service='tag-based',
            stack_name=stack_name,
            status='failed',
            alarm_count=0,
            resource_count=0,
            error_message=str(e)
        )


def discover_acm_certificates(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover ACM certificates filtered by tags"""
    
    print(f"🔍 Discovering ACM certificates with tag {tag_key}={tag_value} in {region}...")
    
    try:
        client = boto3.client('acm', region_name=region)
        
        # List all certificates — must include all key types or ACM only returns RSA_1024
        paginator = client.get_paginator('list_certificates')
        all_certificates = []
        for page in paginator.paginate(
            Includes={
                'keyTypes': [
                    'RSA_1024', 'RSA_2048', 'RSA_3072', 'RSA_4096',
                    'EC_prime256v1', 'EC_secp384r1', 'EC_secp521r1'
                ]
            }
        ):
            all_certificates.extend(page.get('CertificateSummaryList', []))
        
        # Filter by tags
        filtered_certificates = []
        for cert in all_certificates:
            cert_arn = cert['CertificateArn']
            try:
                tags_response = client.list_tags_for_certificate(CertificateArn=cert_arn)
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('Tags', [])}
                
                if tags.get(tag_key) == tag_value:
                    filtered_certificates.append(cert_arn)
            except Exception as e:
                print(f"   Warning: Could not get tags for certificate {cert_arn}: {e}")
        
        print(f"   Found {len(filtered_certificates)} ACM certificate(s) with tag {tag_key}={tag_value}")
        return filtered_certificates
    
    except Exception as e:
        print(f"✗ Error discovering ACM certificates: {e}")
        return []


def parse_dx_bandwidth(bandwidth_str: str) -> int:
    """Parse Direct Connect bandwidth string (e.g., '1Gbps', '10Gbps', '100Mbps') to bps"""
    bw = bandwidth_str.strip().lower()
    if bw.endswith('gbps'):
        return int(float(bw.replace('gbps', '')) * 1_000_000_000)
    elif bw.endswith('mbps'):
        return int(float(bw.replace('mbps', '')) * 1_000_000)
    else:
        raise ValueError(f"Cannot parse bandwidth: '{bandwidth_str}'. Expected format like '1Gbps' or '100Mbps'")


def _discover_elbv2_load_balancers(region: str, tag_key: str, tag_value: str, lb_type: str) -> List[str]:
    """Discover ELBv2 load balancers of a specific type ('application' or 'network'), filtered by tags."""

    label = 'ALB' if lb_type == 'application' else 'NLB'
    print(f"🔍 Discovering {label} load balancers with tag {tag_key}={tag_value} in {region}...")

    try:
        client = boto3.client('elbv2', region_name=region)

        paginator = client.get_paginator('describe_load_balancers')
        all_lbs = []
        for page in paginator.paginate():
            all_lbs.extend(page.get('LoadBalancers', []))

        lb_arns = [lb['LoadBalancerArn'] for lb in all_lbs if lb.get('Type') == lb_type]

        if not lb_arns:
            print(f"   Found 0 {label} load balancer(s)")
            return []

        filtered_lbs = []
        for i in range(0, len(lb_arns), 20):
            batch = lb_arns[i:i+20]
            tags_response = client.describe_tags(ResourceArns=batch)
            for desc in tags_response.get('TagDescriptions', []):
                tags = {t['Key']: t['Value'] for t in desc.get('Tags', [])}
                if tags.get(tag_key) == tag_value:
                    arn = desc['ResourceArn']
                    # Format: arn:aws:elasticloadbalancing:region:account:loadbalancer/<type-prefix>/name/id
                    parts = arn.split('loadbalancer/')
                    if len(parts) == 2:
                        filtered_lbs.append(parts[1])
                    else:
                        filtered_lbs.append(arn)

        print(f"   Found {len(filtered_lbs)} {label} load balancer(s) with tag {tag_key}={tag_value}")
        return filtered_lbs

    except Exception as e:
        print(f"✗ Error discovering {label} load balancers: {e}")
        return []


def discover_alb_load_balancers(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover ALB (application) load balancers filtered by tags."""
    return _discover_elbv2_load_balancers(region, tag_key, tag_value, 'application')


def discover_nlb_load_balancers(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover NLB (network) load balancers filtered by tags."""
    return _discover_elbv2_load_balancers(region, tag_key, tag_value, 'network')


def discover_efs_filesystems(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover EFS file systems filtered by tags."""

    print(f"🔍 Discovering EFS file systems with tag {tag_key}={tag_value} in {region}...")

    try:
        client = boto3.client('efs', region_name=region)

        paginator = client.get_paginator('describe_file_systems')
        filtered_fs = []
        for page in paginator.paginate():
            for fs in page.get('FileSystems', []):
                tags = {t['Key']: t['Value'] for t in fs.get('Tags', [])}
                if tags.get(tag_key) == tag_value:
                    filtered_fs.append(fs['FileSystemId'])

        print(f"   Found {len(filtered_fs)} EFS file system(s) with tag {tag_key}={tag_value}")
        return filtered_fs

    except Exception as e:
        print(f"✗ Error discovering EFS file systems: {e}")
        return []


def discover_dx_connections(region: str, tag_key: str, tag_value: str) -> List[Dict]:
    """Discover Direct Connect connections filtered by tags.
    
    Returns list of dicts with 'connection_id' and 'bandwidth_bps' keys.
    Bandwidth is auto-detected from the describe_connections API.
    """
    
    print(f"🔍 Discovering Direct Connect connections with tag {tag_key}={tag_value} in {region}...")
    
    try:
        client = boto3.client('directconnect', region_name=region)
        sts = boto3.client('sts', region_name=region)
        account_id = sts.get_caller_identity()['Account']
        
        # List all connections
        response = client.describe_connections()
        all_connections = response.get('connections', [])
        
        # Filter by tags
        filtered_connections = []
        for conn in all_connections:
            conn_id = conn['connectionId']
            try:
                # describe_tags expects full ARNs, not connection IDs
                conn_arn = f"arn:aws:directconnect:{region}:{account_id}:dxcon/{conn_id}"
                tags_response = client.describe_tags(resourceArns=[conn_arn])
                tags = {}
                if tags_response.get('resourceTags'):
                    tags = {tag['key']: tag['value'] for tag in tags_response['resourceTags'][0].get('tags', [])}
                
                if tags.get(tag_key) == tag_value:
                    bandwidth_bps = parse_dx_bandwidth(conn.get('bandwidth', '0Gbps'))
                    print(f"   Found connection {conn_id} (bandwidth: {conn.get('bandwidth', 'unknown')} = {bandwidth_bps:,} bps)")
                    filtered_connections.append({
                        'connection_id': conn_id,
                        'bandwidth_bps': bandwidth_bps
                    })
            except Exception as e:
                print(f"   Warning: Could not get tags for connection {conn_id}: {e}")
        
        print(f"   Found {len(filtered_connections)} Direct Connect connection(s) with tag {tag_key}={tag_value}")
        return filtered_connections
    
    except Exception as e:
        print(f"✗ Error discovering Direct Connect connections: {e}")
        return []


def discover_ec2_instances(region: str, tag_key: str, tag_value: str) -> List[Dict]:
    """Discover EC2 instances filtered by tags, then verify CWAgent is publishing metrics.
    
    Returns list of dicts with 'instance_id' and 'name' keys.
    Only returns instances that have published mem_used_percent to CWAgent namespace.
    """
    
    print(f"🔍 Discovering EC2 instances with tag {tag_key}={tag_value} in {region}...")
    
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        cw_client = boto3.client('cloudwatch', region_name=region)
        
        # Step 1: Find tagged EC2 instances
        paginator = ec2_client.get_paginator('describe_instances')
        all_instances = []
        for page in paginator.paginate(
            Filters=[
                {'Name': f'tag:{tag_key}', 'Values': [tag_value]},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        ):
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance['InstanceId']
                    name = instance_id
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                            break
                    all_instances.append({'instance_id': instance_id, 'name': name})
        
        if not all_instances:
            print(f"   Found 0 EC2 instances with tag {tag_key}={tag_value}")
            return []
        
        print(f"   Found {len(all_instances)} EC2 instance(s) — checking for CWAgent metrics...")
        
        # Step 2: Filter to instances that have CWAgent mem_used_percent data
        cwagent_instances = []
        for inst in all_instances:
            result = cw_client.list_metrics(
                Namespace='CWAgent',
                MetricName='mem_used_percent',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst['instance_id']}]
            )
            if result.get('Metrics'):
                cwagent_instances.append(inst)
            else:
                print(f"   ⚠ {inst['name']} ({inst['instance_id']}) — no CWAgent data, skipping")
        
        print(f"   Found {len(cwagent_instances)} instance(s) with CWAgent enabled")
        return cwagent_instances
    
    except Exception as e:
        print(f"✗ Error discovering EC2 instances: {e}")
        return []


def discover_ebs_volumes(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover EBS volumes attached to tagged EC2 instances.
    
    Finds EC2 instances with the specified tag, then collects all attached
    EBS volumes. Only returns volumes in 'in-use' state.
    """
    
    print(f"🔍 Discovering EBS volumes attached to EC2 instances with tag {tag_key}={tag_value} in {region}...")
    
    try:
        client = boto3.client('ec2', region_name=region)
        
        # Step 1: Find tagged EC2 instances
        paginator = client.get_paginator('describe_instances')
        instance_ids = []
        for page in paginator.paginate(
            Filters=[
                {'Name': f'tag:{tag_key}', 'Values': [tag_value]},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        ):
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_ids.append(instance['InstanceId'])
        
        if not instance_ids:
            print(f"   Found 0 EC2 instances with tag {tag_key}={tag_value}")
            return []
        
        print(f"   Found {len(instance_ids)} EC2 instance(s) with tag {tag_key}={tag_value}")
        
        # Step 2: Get all EBS volumes attached to those instances
        volume_ids = []
        for page in client.get_paginator('describe_volumes').paginate(
            Filters=[
                {'Name': 'attachment.instance-id', 'Values': instance_ids},
                {'Name': 'status', 'Values': ['in-use']}
            ]
        ):
            for volume in page.get('Volumes', []):
                volume_ids.append(volume['VolumeId'])
        
        print(f"   Found {len(volume_ids)} EBS volume(s) attached to tagged instances")
        return volume_ids
    
    except Exception as e:
        print(f"✗ Error discovering EBS volumes: {e}")
        return []


def discover_resources(service: str, region: str, tag_key: str, tag_value: str):
    """Discover resources of a service type filtered by tags.
    
    Returns List[str] for most services, or List[Dict] for directconnect
    (with 'connection_id' and 'bandwidth_bps' keys).
    """
    
    print(f"🔍 Discovering {service} resources with tag {tag_key}={tag_value} in {region}...")
    
    try:
        if service == 'ec2':
            return discover_ec2_instances(region, tag_key, tag_value)        
        elif service == 'kafka':
            client = boto3.client('kafka', region_name=region)
            # list_clusters (v1) returns only PROVISIONED clusters — Serverless is intentionally excluded.
            # Paginate to handle accounts with >100 clusters.
            paginator = client.get_paginator('list_clusters')
            all_clusters = []
            for page in paginator.paginate():
                all_clusters.extend(page.get('ClusterInfoList', []))

            # Filter by tags
            filtered_clusters = []
            for cluster in all_clusters:
                tags = cluster.get('Tags', {})
                if tags.get(tag_key) == tag_value:
                    filtered_clusters.append(cluster['ClusterName'])

            resources = filtered_clusters
            print(f"   Found {len(resources)} {service} resource(s) with tag {tag_key}={tag_value}")
            return resources
        
        elif service == 'acm':
            return discover_acm_certificates(region, tag_key, tag_value)
        
        elif service == 'alb':
            return discover_alb_load_balancers(region, tag_key, tag_value)

        elif service == 'nlb':
            return discover_nlb_load_balancers(region, tag_key, tag_value)

        elif service == 'efs':
            return discover_efs_filesystems(region, tag_key, tag_value)

        elif service == 'directconnect':
            return discover_dx_connections(region, tag_key, tag_value)

        elif service == 'ebs':
            return discover_ebs_volumes(region, tag_key, tag_value)
        
        else:
            raise ValueError(f"Unsupported service: {service}")
    
    except Exception as e:
        print(f"✗ Error discovering resources: {e}")
        return []


def generate_resource_based_template(service: str, resource_ids: List[str], tag_value: str, bandwidth: int = None):
    """Generate CloudFormation template for resource-based alarms.

    Returns (template_body_yaml, alarm_count) tuple so callers can use the
    exact number of alarms actually generated (dual-threshold configs emit 2
    alarms each, so multiplying config entries × resources under-counts).
    """
    print(f"🔧 Generating template for {service}...")

    template_dict = resource_alarm_builder.build_template(service, resource_ids, tag_value, bandwidth)
    template_body = yaml.dump(template_dict, default_flow_style=False, allow_unicode=True, sort_keys=False, Dumper=_NoAliasDumper)

    alarm_count = len(template_dict['Resources'])
    print(f"   Template generated: {alarm_count} alarm(s) for {len(resource_ids)} resource(s)")

    return template_body, alarm_count


def deploy_resource_based_alarms(service: str, resource_ids: List[str], 
                                 sns_topic: str, region: str, tag_value: str,
                                 bandwidth: int = None,
                                 stack_name: str = None) -> DeploymentResult:
    """Deploy resource-based alarms for a service"""
    
    cfn = boto3.client('cloudformation', region_name=region)
    if not stack_name:
        stack_name = f'{service}-alarms'
    
    print(f"📦 Deploying {service} alarms...")
    print(f"   Stack: {stack_name}")
    print(f"   Resources: {len(resource_ids)}")
    
    try:
        # Generate template (returns real alarm count — dual-threshold entries emit 2 alarms)
        template_body, alarm_count = generate_resource_based_template(
            service, resource_ids, tag_value, bandwidth
        )

        # Check CloudFormation limit
        if alarm_count > 500:
            raise ValueError(
                f"Stack would have {alarm_count} alarms, exceeding CloudFormation's 500 resource limit. "
                f"Consider splitting resources into multiple stacks or using tag-based alarms if supported."
            )
        
        # Check template size — use S3 if over 51,200 bytes
        template_size = len(template_body.encode('utf-8'))
        print(f"   Template size: {template_size:,} bytes")
        
        use_s3 = template_size > 51200
        template_url = None
        if use_s3:
            print(f"   Template exceeds 51KB limit, uploading to S3...")
            template_url = upload_template_to_s3(
                template_body,
                f'{stack_name}.yaml',
                region
            )
        
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=stack_name)
            print(f"   Stack exists, updating...")
            
            stack_args = {
                'StackName': stack_name,
                'Parameters': [
                    {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
                ]
            }
            if use_s3:
                stack_args['TemplateURL'] = template_url
            else:
                stack_args['TemplateBody'] = template_body
            
            try:
                cfn.update_stack(**stack_args)
                print(f"✓ Stack update initiated")
                return DeploymentResult(
                    service=service,
                    stack_name=stack_name,
                    status='updated',
                    alarm_count=alarm_count,
                    resource_count=len(resource_ids)
                )
            except cfn.exceptions.ClientError as e:
                if 'No updates are to be performed' in str(e):
                    print(f"  No changes needed")
                    return DeploymentResult(
                        service=service,
                        stack_name=stack_name,
                        status='no-change',
                        alarm_count=alarm_count,
                        resource_count=len(resource_ids)
                    )
                raise
        
        except cfn.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                print(f"   Creating new stack...")
                create_args = {
                    'StackName': stack_name,
                    'Parameters': [
                        {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
                    ]
                }
                if use_s3:
                    create_args['TemplateURL'] = template_url
                else:
                    create_args['TemplateBody'] = template_body
                
                cfn.create_stack(**create_args)
                print(f"✓ Stack creation initiated")
                return DeploymentResult(
                    service=service,
                    stack_name=stack_name,
                    status='created',
                    alarm_count=alarm_count,
                    resource_count=len(resource_ids)
                )
            raise
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return DeploymentResult(
            service=service,
            stack_name=stack_name,
            status='failed',
            alarm_count=0,
            resource_count=0,
            error_message=str(e)
        )


def deploy_bedrock_alarms(sns_topic: str, region: str, tag_value: str,
                          stack_name: str = None) -> DeploymentResult:
    """Deploy Bedrock CloudWatch alarms (auto-discover + yaml overrides)."""
    cfn = boto3.client('cloudformation', region_name=region)
    if not stack_name:
        stack_name = 'bedrock-alarms'

    print(f"📦 Deploying Bedrock alarms...")
    print(f"   Stack: {stack_name}")

    try:
        template = bedrock_alarm_builder.build_template(tag_value, region)
        alarm_count = len(template.get('Resources', {}))

        if alarm_count == 0:
            print(f"  No Bedrock models found and no overrides configured — skipping")
            return DeploymentResult(
                service='bedrock', stack_name=stack_name,
                status='no-change', alarm_count=0, resource_count=0
            )

        template_body = bedrock_alarm_builder.dump_template(template)
        template_size = len(template_body.encode('utf-8'))
        print(f"   Template size: {template_size:,} bytes")

        use_s3 = template_size > 51200
        template_url = None
        if use_s3:
            print(f"   Template exceeds 51KB, uploading to S3...")
            template_url = upload_template_to_s3(template_body, f'{stack_name}.yaml', region)

        stack_args = {
            'StackName': stack_name,
            'Parameters': [{'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}]
        }
        if use_s3:
            stack_args['TemplateURL'] = template_url
        else:
            stack_args['TemplateBody'] = template_body

        try:
            cfn.describe_stacks(StackName=stack_name)
            print(f"   Stack exists, updating...")
            try:
                cfn.update_stack(**stack_args)
                print(f"✓ Stack update initiated")
                return DeploymentResult(service='bedrock', stack_name=stack_name,
                                        status='updated', alarm_count=alarm_count, resource_count=alarm_count)
            except cfn.exceptions.ClientError as e:
                if 'No updates are to be performed' in str(e):
                    print(f"  No changes needed")
                    return DeploymentResult(service='bedrock', stack_name=stack_name,
                                            status='no-change', alarm_count=alarm_count, resource_count=alarm_count)
                raise
        except cfn.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                print(f"   Creating new stack...")
                cfn.create_stack(**stack_args)
                print(f"✓ Stack creation initiated")
                return DeploymentResult(service='bedrock', stack_name=stack_name,
                                        status='created', alarm_count=alarm_count, resource_count=alarm_count)
            raise

    except Exception as e:
        print(f"✗ Error: {e}")
        return DeploymentResult(service='bedrock', stack_name=stack_name,
                                status='failed', alarm_count=0, resource_count=0, error_message=str(e))


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deploy CloudWatch alarms (tag-based or resource-based)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy tag-based alarms for Production (EC2, NAT Gateway, VPN - 10 alarms)
  python deploy_alarms.py --mode tag-based --tag-key Environment --tag-value Production

  # Deploy resource-based alarms for Kafka (auto-discover)
  python deploy_alarms.py --mode resource-based --service kafka --tag-key Environment --tag-value Production

  # Deploy resource-based alarms for specific ACM certificates
  python deploy_alarms.py --mode resource-based --service acm --tag-key Environment --tag-value Production --resources arn:aws:acm:us-east-1:123456789:certificate/abc

  # Deploy resource-based alarms for Direct Connect
  python deploy_alarms.py --mode resource-based --service directconnect --tag-key Environment --tag-value Production

  # Deploy everything (tag-based + resource-based)
  python deploy_alarms.py --mode all --tag-key Environment --tag-value Production
        """
    )
    
    parser.add_argument('--mode', required=True,
                        choices=['tag-based', 'resource-based', 'all'],
                        help='Deployment mode')
    parser.add_argument('--service',
                        choices=RESOURCE_BASED_SERVICES,
                        help='Service for resource-based mode (kafka, acm, alb, directconnect, ebs)')
    parser.add_argument('--tag-key', required=True,
                        help='Tag key to filter resources (REQUIRED)')
    parser.add_argument('--tag-value', required=True,
                        help='Tag value to filter resources (REQUIRED)')
    parser.add_argument('--resources', nargs='+',
                        help='List of resource IDs for resource-based mode')
    parser.add_argument('--bandwidth',
                        help='Direct Connect bandwidth (e.g., "1Gbps", "10Gbps"). '
                             'Required only for --service directconnect with --resources. '
                             'Auto-detected when discovering by tag.')

    parser.add_argument('--region', default='us-east-1',
                        help='AWS region (default: us-east-1)')
    parser.add_argument('--sns-topic', required=True,
                        help='SNS topic ARN for notifications (REQUIRED)')
    parser.add_argument('--stack-name',
                        help='Custom stack name (optional)')
    
    args = parser.parse_args()
    
    # Validate prerequisites
    validate_prerequisites()
    
    # Validation
    if args.mode == 'resource-based':
        if not args.service:
            parser.error("--service is required for resource-based mode")
        # Manual resource list is optional (for override)

    if args.stack_name and args.mode == 'all':
        parser.error(
            "--stack-name cannot be used with --mode all "
            "(would cause multiple services to share one CloudFormation stack name). "
            "Use it with --mode tag-based or --mode resource-based --service <one>."
        )
    
    print("🚀 CloudWatch Alarms Deployment")
    print(f"   Mode: {args.mode}")
    print(f"   Region: {args.region}")
    print("=" * 60)
    
    results = []
    
    # Deploy based on mode
    if args.mode == 'tag-based':
        # Deploy tag-based alarms (EC2, NAT Gateway, VPN)
        result = deploy_tag_based_alarms(
            args.tag_key,
            args.tag_value,
            args.sns_topic,
            args.region,
            args.stack_name
        )
        results.append(result)
        
        # Always also deploy EC2 resource-based alarms (CWAgent metrics)
        print(f"\n--- EC2 (CWAgent) ---")
        ec2_instances = discover_resources('ec2', args.region, args.tag_key, args.tag_value)
        if ec2_instances:
            # EC2 returns dicts with instance_id and name
            resource_ids = [f"{d['name']}|{d['instance_id']}" for d in ec2_instances]
            result = deploy_resource_based_alarms(
                'ec2', resource_ids, args.sns_topic, args.region, args.tag_value
            )
            results.append(result)
        else:
            print(f"{RED}  No EC2 instances found with tag {args.tag_key}={args.tag_value} — skipping{RESET}")
    
    elif args.mode == 'resource-based':
        # Bedrock has its own discovery logic
        if args.service == 'bedrock':
            result = deploy_bedrock_alarms(args.sns_topic, args.region, args.tag_value,
                                           stack_name=args.stack_name)
            results.append(result)
        # Get resource IDs via tag-based discovery or manual list
        elif args.resources:
            # Manual override — use specified resources
            resource_ids = args.resources
            print(f"   Using manually specified resources: {', '.join(resource_ids)}")
            bandwidth = None

            # Direct Connect needs bandwidth for math expressions.
            # Prefer --bandwidth flag; otherwise auto-detect via describe_connections.
            if args.service == 'directconnect':
                if args.bandwidth:
                    bandwidth = parse_dx_bandwidth(args.bandwidth)
                    print(f"   Using bandwidth from --bandwidth: {bandwidth:,} bps")
                else:
                    try:
                        dx = boto3.client('directconnect', region_name=args.region)
                        detected = {c['connectionId']: c.get('bandwidth') for c in dx.describe_connections().get('connections', [])}
                        missing = [r for r in resource_ids if r not in detected]
                        if missing:
                            parser.error(
                                f"Direct Connect connection(s) not found in {args.region}: {', '.join(missing)}. "
                                f"Check the connection ID(s) or pass --bandwidth explicitly."
                            )
                        # Use the first connection's bandwidth (DX math expressions take a single bandwidth parameter)
                        first_bw = detected[resource_ids[0]]
                        bandwidth = parse_dx_bandwidth(first_bw)
                        print(f"   Auto-detected bandwidth for {resource_ids[0]}: {first_bw} ({bandwidth:,} bps)")
                        if len(resource_ids) > 1:
                            distinct = {detected[r] for r in resource_ids}
                            if len(distinct) > 1:
                                print(f"   ⚠ Connections have differing bandwidths {distinct}; "
                                      f"using {first_bw} for all. Deploy each in a separate stack if percentages need to be accurate.")
                    except Exception as e:
                        parser.error(
                            f"Could not auto-detect Direct Connect bandwidth: {e}. "
                            f"Pass --bandwidth (e.g., --bandwidth 1Gbps)."
                        )
        else:
            # Tag-based discovery (default)
            discovered = discover_resources(args.service, args.region, args.tag_key, args.tag_value)
            
            # Direct Connect returns dicts with connection_id and bandwidth_bps
            if args.service == 'directconnect' and discovered and isinstance(discovered[0], dict):
                resource_ids = [d['connection_id'] for d in discovered]
                # Use the first connection's bandwidth (all connections on same port typically share bandwidth)
                bandwidth = discovered[0]['bandwidth_bps']
                print(f"   Auto-detected bandwidth: {bandwidth:,} bps")
            else:
                resource_ids = discovered
                bandwidth = None
        
        if args.service != 'bedrock':
            if not resource_ids:
                print(f"{RED}✗ No {args.service} resources found with tag {args.tag_key}={args.tag_value} — skipping{RESET}")
            else:
                result = deploy_resource_based_alarms(
                    args.service,
                    resource_ids,
                    args.sns_topic,
                    args.region,
                    args.tag_value,
                    bandwidth,
                    stack_name=args.stack_name
                )
                results.append(result)

    elif args.mode == 'all':
        print("\n" + "=" * 60)
        print("PHASE 1: Tag-Based Alarms (EC2, NAT Gateway, VPN)")
        print("=" * 60)
        result = deploy_tag_based_alarms(
            args.tag_key,
            args.tag_value,
            args.sns_topic,
            args.region
        )
        results.append(result)
        
        # Deploy resource-based for each service
        print("\n" + "=" * 60)
        print("PHASE 2: Resource-Based Alarms (EC2 CWAgent, Kafka, ACM, ALB, Direct Connect, EBS)")
        print("=" * 60)
        
        for service in RESOURCE_BASED_SERVICES:
            if service == 'bedrock':
                continue  # handled separately in PHASE 3
            print(f"\n--- {service.upper()} ---")
            discovered = discover_resources(service, args.region, args.tag_key, args.tag_value)
            
            # Direct Connect returns dicts with connection_id and bandwidth_bps
            # EC2 returns dicts with instance_id and name
            if service == 'directconnect' and discovered and isinstance(discovered[0], dict):
                resource_ids = [d['connection_id'] for d in discovered]
                bandwidth = discovered[0]['bandwidth_bps']
                print(f"   Auto-detected bandwidth: {bandwidth:,} bps")
            elif service == 'ec2' and discovered and isinstance(discovered[0], dict):
                resource_ids = [f"{d['name']}|{d['instance_id']}" for d in discovered]
                bandwidth = None
            else:
                resource_ids = discovered
                bandwidth = None
            
            if resource_ids:
                result = deploy_resource_based_alarms(
                    service,
                    resource_ids,
                    args.sns_topic,
                    args.region,
                    args.tag_value,
                    bandwidth
                )
                results.append(result)
            else:
                print(f"{RED}  No {service} resources found with tag {args.tag_key}={args.tag_value} — skipping{RESET}")

        # Deploy Bedrock alarms (auto-discover + yaml overrides)
        print("\n" + "=" * 60)
        print("PHASE 3: Bedrock Alarms (Auto-discover + YAML overrides)")
        print("=" * 60)
        result = deploy_bedrock_alarms(args.sns_topic, args.region, args.tag_value)
        results.append(result)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Deployment Summary")
    print("=" * 60)
    
    created = sum(1 for r in results if r.status == 'created')
    updated = sum(1 for r in results if r.status == 'updated')
    no_change = sum(1 for r in results if r.status == 'no-change')
    failed = sum(1 for r in results if r.status == 'failed')
    
    total_alarms = sum(r.alarm_count for r in results if r.status != 'failed')
    total_stacks = len(results)
    
    print(f"✓ Created: {created} stack(s)")
    print(f"✓ Updated: {updated} stack(s)")
    print(f"  No Change: {no_change} stack(s)")
    print(f"✗ Failed: {failed} stack(s)")
    print(f"\nTotal Stacks: {total_stacks}")
    print(f"Total Alarms: {total_alarms}")
    
    # Print successful deployments in green
    successful = [r for r in results if r.status in ('created', 'updated', 'no-change')]
    if successful:
        print(f"\n{GREEN}✓ Successfully deployed services:{RESET}")
        for r in successful:
            print(f"{GREEN}  ✓ {r.service} ({r.stack_name}) — {r.status}, {r.alarm_count} alarm(s){RESET}")
    
    if failed > 0:
        print(f"\n{RED}⚠️  Failed Deployments:{RESET}")
        for r in results:
            if r.status == 'failed':
                print(f"{RED}  ✗ {r.service}: {r.error_message}{RESET}")
    
    print("\n✅ Deployment complete!")
    
    # Exit with error code if any failures
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
