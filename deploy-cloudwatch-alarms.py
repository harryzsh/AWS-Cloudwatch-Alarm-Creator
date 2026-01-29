#!/usr/bin/env python3
"""
Unified CloudWatch Alarms Deployment Script
Supports both tag-based and resource-based alarm deployment.

Tag-Based Services (7): EC2, RDS MySQL/PG, Redis, DocumentDB, EFS, ALB
Resource-Based Services (4): OpenSearch, Kafka, RabbitMQ, WAF
"""

import boto3
import yaml
import sys
import subprocess
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

# Service configuration
TAG_BASED_SERVICES = ['ec2', 'rds-mysql', 'rds-postgres', 'redis', 'efs']
RESOURCE_BASED_SERVICES = ['opensearch', 'kafka', 'rabbitmq', 'waf', 'docdb', 'alb']
EKS_EC2_ALARM_COUNT = 11  # Number of alarms in cloudformation-eks-ec2-alarms.yaml

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
        'cloudformation-eks-ec2-alarms.yaml',
        'alarm-config-resource-based.yaml',
        'generate-resource-based-template.py'
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
                    alarm_count=89,
                    resource_count=6
                )
            except cfn.exceptions.ClientError as e:
                if 'No updates are to be performed' in str(e):
                    print(f"  No changes needed")
                    return DeploymentResult(
                        service='tag-based',
                        stack_name=stack_name,
                        status='no-change',
                        alarm_count=89,
                        resource_count=6
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
                    alarm_count=89,
                    resource_count=6
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


def discover_resources(service: str, region: str, tag_key: str, tag_value: str) -> List[str]:
    """Discover resources of a service type filtered by tags"""
    
    print(f"🔍 Discovering {service} resources with tag {tag_key}={tag_value} in {region}...")
    
    try:
        if service == 'eks':
            # Discover EKS clusters with the business tag
            client = boto3.client('eks', region_name=region)
            response = client.list_clusters()
            all_clusters = response.get('clusters', [])
            
            # Filter by tags
            filtered_clusters = []
            for cluster_name in all_clusters:
                try:
                    cluster_info = client.describe_cluster(name=cluster_name)
                    tags = cluster_info.get('cluster', {}).get('tags', {})
                    
                    if tags.get(tag_key) == tag_value:
                        filtered_clusters.append(cluster_name)
                except Exception as e:
                    print(f"   Warning: Could not get tags for EKS cluster {cluster_name}: {e}")
            
            resources = filtered_clusters
        
        elif service == 'opensearch':
            client = boto3.client('opensearch', region_name=region)
            sts = boto3.client('sts', region_name=region)
            account_id = sts.get_caller_identity()['Account']
            
            response = client.list_domain_names()
            all_domains = [domain['DomainName'] for domain in response['DomainNames']]
            
            # Filter by tags
            filtered_domains = []
            for domain_name in all_domains:
                domain_arn = f'arn:aws:es:{region}:{account_id}:domain/{domain_name}'
                try:
                    tags_response = client.list_tags(ARN=domain_arn)
                    tags = tags_response.get('TagList', [])
                    
                    # Check if domain has matching tag
                    if any(tag['Key'] == tag_key and tag['Value'] == tag_value for tag in tags):
                        filtered_domains.append(domain_name)
                except Exception as e:
                    print(f"   Warning: Could not get tags for {domain_name}: {e}")
            
            resources = filtered_domains
        
        elif service == 'kafka':
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
        
        elif service == 'rabbitmq':
            client = boto3.client('mq', region_name=region)
            response = client.list_brokers()
            all_brokers = response['BrokerSummaries']
            
            # Filter by tags (need to describe each broker for tags)
            filtered_brokers = []
            for broker in all_brokers:
                try:
                    broker_details = client.describe_broker(BrokerId=broker['BrokerId'])
                    tags = broker_details.get('Tags', {})
                    if tags.get(tag_key) == tag_value:
                        filtered_brokers.append(broker['BrokerId'])
                except Exception as e:
                    print(f"   Warning: Could not get tags for {broker['BrokerId']}: {e}")
            
            resources = filtered_brokers
        
        elif service == 'waf':
            client = boto3.client('wafv2', region_name=region)
            response = client.list_web_acls(Scope='REGIONAL')
            all_acls = response['WebACLs']
            
            # Filter by tags
            filtered_acls = []
            for acl in all_acls:
                try:
                    acl_arn = acl['ARN']
                    tags_response = client.list_tags_for_resource(ResourceARN=acl_arn)
                    tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagInfoForResource', {}).get('TagList', [])}
                    
                    if tags.get(tag_key) == tag_value:
                        filtered_acls.append(acl['Name'])  # Just the name, not tuple
                except Exception as e:
                    print(f"   Warning: Could not get tags for {acl['Name']}: {e}")
            
            resources = filtered_acls
        
        elif service == 'docdb':
            client = boto3.client('docdb', region_name=region)
            response = client.describe_db_clusters()
            all_clusters = response['DBClusters']
            
            # Filter by tags
            filtered_clusters = []
            for cluster in all_clusters:
                try:
                    cluster_arn = cluster['DBClusterArn']
                    tags_response = client.list_tags_for_resource(ResourceName=cluster_arn)
                    tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                    
                    if tags.get(tag_key) == tag_value:
                        filtered_clusters.append(cluster['DBClusterIdentifier'])
                except Exception as e:
                    print(f"   Warning: Could not get tags for {cluster['DBClusterIdentifier']}: {e}")
            
            resources = filtered_clusters
        
        elif service == 'alb':
            client = boto3.client('elbv2', region_name=region)
            response = client.describe_load_balancers()
            all_lbs = response['LoadBalancers']
            
            # Filter by tags and type (application load balancers only)
            filtered_lbs = []
            for lb in all_lbs:
                if lb['Type'] != 'application':
                    continue
                    
                try:
                    lb_arn = lb['LoadBalancerArn']
                    tags_response = client.describe_tags(ResourceArns=[lb_arn])
                    tags = {}
                    if tags_response['TagDescriptions']:
                        tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0].get('Tags', [])}
                    
                    if tags.get(tag_key) == tag_value:
                        # Extract LoadBalancer dimension format: app/name/id
                        lb_name = lb['LoadBalancerArn'].split(':loadbalancer/')[1]
                        filtered_lbs.append(lb_name)
                except Exception as e:
                    print(f"   Warning: Could not get tags for {lb['LoadBalancerName']}: {e}")
            
            resources = filtered_lbs
        
        else:
            raise ValueError(f"Unsupported service: {service}")
        
        print(f"   Found {len(resources)} {service} resource(s) with tag {tag_key}={tag_value}")
        return resources
    
    except Exception as e:
        print(f"✗ Error discovering resources: {e}")
        return []


def generate_resource_based_template(service: str, resource_ids: List[str], tag_value: str) -> str:
    """Generate CloudFormation template for resource-based alarms"""
    
    print(f"🔧 Generating template for {service}...")
    
    # Use simple YAML generator (no CDK required)
    cmd = [
        'python', 'generate-resource-alarms-simple.py',
        '--service', service,
        '--tag-value', tag_value,
        '--resources'] + resource_ids
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"   Template generated successfully")
        
        # Read generated template
        template_file = f'cloudformation-{service}-alarms-generated.yaml'
        with open(template_file, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    except subprocess.CalledProcessError as e:
        print(f"✗ Template generation failed: {e.stderr}")
        raise
    except FileNotFoundError:
        print(f"✗ Generated template not found")
        raise


def deploy_eks_ec2_alarms(eks_cluster_name: str, sns_topic: str, region: str, 
                          tag_value: str) -> DeploymentResult:
    """Deploy EKS EC2 node alarms for a specific EKS cluster"""
    
    cfn = boto3.client('cloudformation', region_name=region)
    stack_name = f'eks-ec2-alarms-{eks_cluster_name}'
    template_file = 'cloudformation-eks-ec2-alarms.yaml'
    
    print(f"📦 Deploying EKS EC2 alarms for cluster: {eks_cluster_name}...")
    print(f"   Stack: {stack_name}")
    print(f"   Tag filter: eks:cluster-name={eks_cluster_name}")
    
    try:
        # Read template
        with open(template_file, 'r', encoding='utf-8', errors='ignore') as f:
            template_body = f.read()
        
        # Build parameters
        parameters = [
            {'ParameterKey': 'EKSClusterName', 'ParameterValue': eks_cluster_name},
            {'ParameterKey': 'BusinessTagValue', 'ParameterValue': tag_value},
            {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
        ]
        
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=stack_name)
            print(f"   Stack exists, updating...")
            
            try:
                cfn.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters
                )
                print(f"✓ Stack update initiated")
                return DeploymentResult(
                    service=f'eks-ec2-{eks_cluster_name}',
                    stack_name=stack_name,
                    status='updated',
                    alarm_count=EKS_EC2_ALARM_COUNT,
                    resource_count=1
                )
            except cfn.exceptions.ClientError as e:
                if 'No updates are to be performed' in str(e):
                    print(f"  No changes needed")
                    return DeploymentResult(
                        service=f'eks-ec2-{eks_cluster_name}',
                        stack_name=stack_name,
                        status='no-change',
                        alarm_count=EKS_EC2_ALARM_COUNT,
                        resource_count=1
                    )
                raise
        
        except cfn.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                print(f"   Creating new stack...")
                cfn.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters
                )
                print(f"✓ Stack creation initiated")
                return DeploymentResult(
                    service=f'eks-ec2-{eks_cluster_name}',
                    stack_name=stack_name,
                    status='created',
                    alarm_count=EKS_EC2_ALARM_COUNT,
                    resource_count=1
                )
            raise
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return DeploymentResult(
            service=f'eks-ec2-{eks_cluster_name}',
            stack_name=stack_name,
            status='failed',
            alarm_count=0,
            resource_count=0,
            error_message=str(e)
        )


def deploy_resource_based_alarms(service: str, resource_ids: List[str], 
                                 sns_topic: str, region: str, tag_value: str) -> DeploymentResult:
    """Deploy resource-based alarms for a service"""
    
    cfn = boto3.client('cloudformation', region_name=region)
    stack_name = f'{service}-alarms'
    
    print(f"📦 Deploying {service} alarms...")
    print(f"   Stack: {stack_name}")
    print(f"   Resources: {len(resource_ids)}")
    
    try:
        # Generate template
        template_body = generate_resource_based_template(service, resource_ids, tag_value)
        
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
        
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=stack_name)
            print(f"   Stack exists, updating...")
            
            try:
                cfn.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=[
                        {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
                    ]
                )
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
                cfn.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=[
                        {'ParameterKey': 'SNSTopicArn', 'ParameterValue': sns_topic}
                    ]
                )
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
  # Deploy tag-based alarms for Production (includes EKS EC2 nodes)
  python deploy-cloudwatch-alarms.py --mode tag-based --tag-key Environment --tag-value Production

  # Deploy resource-based alarms for OpenSearch (auto-discover)
  python deploy-cloudwatch-alarms.py --mode resource-based --service opensearch

  # Deploy resource-based alarms for specific Kafka clusters
  python deploy-cloudwatch-alarms.py --mode resource-based --service kafka --resources cluster-1 cluster-2

  # Deploy everything (tag-based + EKS EC2 + resource-based)
  python deploy-cloudwatch-alarms.py --mode all --tag-key Environment --tag-value Production
        """
    )
    
    parser.add_argument('--mode', required=True,
                        choices=['tag-based', 'resource-based', 'all'],
                        help='Deployment mode')
    parser.add_argument('--service',
                        choices=RESOURCE_BASED_SERVICES,
                        help='Service for resource-based mode')
    parser.add_argument('--tag-key', default='Environment',
                        help='Tag key for tag-based mode (default: Environment)')
    parser.add_argument('--tag-value', default='Production',
                        help='Tag value for tag-based mode (default: Production)')
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
        # Tag-based discovery is now the default - require tag-key and tag-value
        if not args.tag_key or not args.tag_value:
            parser.error("--tag-key and --tag-value are required for resource-based mode (for tag-based discovery)")
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
        # Deploy regular tag-based alarms
        result = deploy_tag_based_alarms(
            args.tag_key,
            args.tag_value,
            args.sns_topic,
            args.region,
            args.stack_name
        )
        results.append(result)
        
        # Also deploy EKS EC2 node alarms (for EC2 instances belonging to EKS clusters)
        print("\n" + "-" * 60)
        print("🔍 Checking for EKS clusters with business tag...")
        eks_clusters = discover_resources('eks', args.region, args.tag_key, args.tag_value)
        
        if eks_clusters:
            print(f"   Found {len(eks_clusters)} EKS cluster(s): {', '.join(eks_clusters)}")
            for cluster_name in eks_clusters:
                print(f"\n--- EKS EC2 Nodes: {cluster_name} ---")
                result = deploy_eks_ec2_alarms(
                    cluster_name,
                    args.sns_topic,
                    args.region,
                    args.tag_value
                )
                results.append(result)
        else:
            print(f"   No EKS clusters found with tag {args.tag_key}={args.tag_value}, skipping EKS EC2 alarms")
    
    elif args.mode == 'resource-based':
        # Get resource IDs via tag-based discovery or manual list
        if args.resources:
            # Manual override - use specified resources
            resource_ids = args.resources
            print(f"   Using manually specified resources: {', '.join(resource_ids)}")
        else:
            # Tag-based discovery (default)
            resource_ids = discover_resources(args.service, args.region, args.tag_key, args.tag_value)
        
        if not resource_ids:
            print(f"✗ No {args.service} resources found with tag {args.tag_key}={args.tag_value}")
            sys.exit(1)
        
        result = deploy_resource_based_alarms(
            args.service,
            resource_ids,
            args.sns_topic,
            args.region,
            args.tag_value
        )
        results.append(result)
    
    elif args.mode == 'all':
        # Deploy tag-based first
        print("\n" + "=" * 60)
        print("PHASE 1: Tag-Based Alarms")
        print("=" * 60)
        result = deploy_tag_based_alarms(
            args.tag_key,
            args.tag_value,
            args.sns_topic,
            args.region
        )
        results.append(result)
        
        # Deploy EKS EC2 alarms
        print("\n" + "=" * 60)
        print("PHASE 2: EKS EC2 Node Alarms")
        print("=" * 60)
        eks_clusters = discover_resources('eks', args.region, args.tag_key, args.tag_value)
        
        if eks_clusters:
            print(f"   Found {len(eks_clusters)} EKS cluster(s): {', '.join(eks_clusters)}")
            for cluster_name in eks_clusters:
                print(f"\n--- EKS Cluster: {cluster_name} ---")
                result = deploy_eks_ec2_alarms(
                    cluster_name,
                    args.sns_topic,
                    args.region,
                    args.tag_value
                )
                results.append(result)
        else:
            print(f"  No EKS clusters found with tag {args.tag_key}={args.tag_value}, skipping")
        
        # Deploy resource-based for each service
        print("\n" + "=" * 60)
        print("PHASE 3: Resource-Based Alarms")
        print("=" * 60)
        
        for service in RESOURCE_BASED_SERVICES:
            print(f"\n--- {service.upper()} ---")
            resource_ids = discover_resources(service, args.region, args.tag_key, args.tag_value)
            
            if resource_ids:
                result = deploy_resource_based_alarms(
                    service,
                    resource_ids,
                    args.sns_topic,
                    args.region,
                    args.tag_value
                )
                results.append(result)
            else:
                print(f"  No {service} resources found with tag {args.tag_key}={args.tag_value}, skipping")
    
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
    
    if failed > 0:
        print("\n⚠️  Failed Deployments:")
        for r in results:
            if r.status == 'failed':
                print(f"  - {r.service}: {r.error_message}")
    
    print("\n✅ Deployment complete!")
    
    # Exit with error code if any failures
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
