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


class _NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that disables aliases — CloudFormation doesn't support them."""
    def ignore_aliases(self, data):
        return True

# Service configuration
# Tag-based: EC2, NAT Gateway, VPN (deployed via cloudformation-tag-based-alarms.yaml)
# Resource-based: Kafka, ACM, ALB, Direct Connect (generated per-resource by resource_alarm_builder)
TAG_BASED_SERVICES = ['ec2', 'nat-gateway', 'vpn']
RESOURCE_BASED_SERVICES = ['kafka', 'acm', 'alb', 'directconnect']

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
        'resource_alarm_builder.py'
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
        
        # List all certificates
        paginator = client.get_paginator('list_certificates')
        all_certificates = []
        for page in paginator.paginate():
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


def discover_alb_load_balancers(region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover ALB load balancers filtered by tags"""
    
    print(f"🔍 Discovering ALB load balancers with tag {tag_key}={tag_value} in {region}...")
    
    try:
        client = boto3.client('elbv2', region_name=region)
        
        paginator = client.get_paginator('describe_load_balancers')
        all_lbs = []
        for page in paginator.paginate():
            all_lbs.extend(page.get('LoadBalancers', []))
        
        # Filter to ALBs only and get their ARNs
        alb_arns = [lb['LoadBalancerArn'] for lb in all_lbs if lb.get('Type') == 'application']
        
        if not alb_arns:
            print(f"   Found 0 ALB load balancer(s)")
            return []
        
        # Get tags for ALBs (up to 20 at a time)
        filtered_lbs = []
        for i in range(0, len(alb_arns), 20):
            batch = alb_arns[i:i+20]
            tags_response = client.describe_tags(ResourceArns=batch)
            for desc in tags_response.get('TagDescriptions', []):
                tags = {t['Key']: t['Value'] for t in desc.get('Tags', [])}
                if tags.get(tag_key) == tag_value:
                    # Extract the ALB identifier (app/name/id) from the ARN
                    arn = desc['ResourceArn']
                    # Format: arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id
                    parts = arn.split('loadbalancer/')
                    if len(parts) == 2:
                        filtered_lbs.append(parts[1])
                    else:
                        filtered_lbs.append(arn)
        
        print(f"   Found {len(filtered_lbs)} ALB load balancer(s) with tag {tag_key}={tag_value}")
        return filtered_lbs
    
    except Exception as e:
        print(f"✗ Error discovering ALB load balancers: {e}")
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


def discover_resources(service: str, region: str, tag_key: str, tag_value: str):
    """Discover resources of a service type filtered by tags.
    
    Returns List[str] for most services, or List[Dict] for directconnect
    (with 'connection_id' and 'bandwidth_bps' keys).
    """
    
    print(f"🔍 Discovering {service} resources with tag {tag_key}={tag_value} in {region}...")
    
    try:
        if service == 'kafka':
            client = boto3.client('kafka', region_name=region)
            response = client.list_clusters()
            all_clusters = response['ClusterInfoList']
            
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
        
        elif service == 'directconnect':
            return discover_dx_connections(region, tag_key, tag_value)
        
        else:
            raise ValueError(f"Unsupported service: {service}")
    
    except Exception as e:
        print(f"✗ Error discovering resources: {e}")
        return []


def generate_resource_based_template(service: str, resource_ids: List[str], tag_value: str, bandwidth: int = None) -> str:
    """Generate CloudFormation template for resource-based alarms"""
    
    print(f"🔧 Generating template for {service}...")
    
    template_dict = resource_alarm_builder.build_template(service, resource_ids, tag_value, bandwidth)
    template_body = yaml.dump(template_dict, default_flow_style=False, allow_unicode=True, sort_keys=False, Dumper=_NoAliasDumper)
    
    alarm_count = len(template_dict['Resources'])
    print(f"   Template generated: {alarm_count} alarm(s) for {len(resource_ids)} resource(s)")
    
    return template_body


def deploy_resource_based_alarms(service: str, resource_ids: List[str], 
                                 sns_topic: str, region: str, tag_value: str,
                                 bandwidth: int = None) -> DeploymentResult:
    """Deploy resource-based alarms for a service"""
    
    cfn = boto3.client('cloudformation', region_name=region)
    stack_name = f'{service}-alarms'
    
    print(f"📦 Deploying {service} alarms...")
    print(f"   Stack: {stack_name}")
    print(f"   Resources: {len(resource_ids)}")
    
    try:
        # Generate template
        template_body = generate_resource_based_template(service, resource_ids, tag_value, bandwidth)
        
        # Load service config to get alarm count
        with open('alarm-config-resource-based.yaml', 'r', encoding='utf-8', errors='ignore') as f:
            config = yaml.safe_load(f)
        alarm_count = len(resource_ids) * len(config['services'][service]['alarms'])
        
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
                        help='Service for resource-based mode')
    parser.add_argument('--tag-key', required=True,
                        help='Tag key to filter resources (REQUIRED)')
    parser.add_argument('--tag-value', required=True,
                        help='Tag value to filter resources (REQUIRED)')
    parser.add_argument('--resources', nargs='+',
                        help='List of resource IDs for resource-based mode')
    parser.add_argument('--discover-all', action='store_true',
                        help='Auto-discover all resources for resource-based mode')
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
        if args.resources and args.discover_all:
            parser.error("Cannot specify both --resources and --discover-all")
    
    print("🚀 CloudWatch Alarms Deployment")
    print(f"   Mode: {args.mode}")
    print(f"   Region: {args.region}")
    print("=" * 60)
    
    results = []
    
    # Deploy based on mode
    if args.mode == 'tag-based':
        # Deploy tag-based alarms (EC2, NAT Gateway, ALB, VPN)
        result = deploy_tag_based_alarms(
            args.tag_key,
            args.tag_value,
            args.sns_topic,
            args.region,
            args.stack_name
        )
        results.append(result)
    
    elif args.mode == 'resource-based':
        # Get resource IDs via tag-based discovery or manual list
        if args.resources:
            # Manual override - use specified resources
            resource_ids = args.resources
            print(f"   Using manually specified resources: {', '.join(resource_ids)}")
            bandwidth = None
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
        
        if not resource_ids:
            print(f"{RED}✗ No {args.service} resources found with tag {args.tag_key}={args.tag_value} — skipping{RESET}")
        else:
            result = deploy_resource_based_alarms(
                args.service,
                resource_ids,
                args.sns_topic,
                args.region,
                args.tag_value,
                bandwidth
            )
            results.append(result)
    
    elif args.mode == 'all':
        # Deploy tag-based first
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
        print("PHASE 2: Resource-Based Alarms (Kafka, ACM, ALB, Direct Connect)")
        print("=" * 60)
        
        for service in RESOURCE_BASED_SERVICES:
            print(f"\n--- {service.upper()} ---")
            discovered = discover_resources(service, args.region, args.tag_key, args.tag_value)
            
            # Direct Connect returns dicts with connection_id and bandwidth_bps
            if service == 'directconnect' and discovered and isinstance(discovered[0], dict):
                resource_ids = [d['connection_id'] for d in discovered]
                bandwidth = discovered[0]['bandwidth_bps']
                print(f"   Auto-detected bandwidth: {bandwidth:,} bps")
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
