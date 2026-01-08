#!/usr/bin/env python3
"""Check if DocumentDB and ALB resources can be discovered by tags"""

import boto3

region = 'us-east-1'
tag_key = 'businessTag'
tag_value = 'EM-SNC-CLOUD'

print('=' * 60)
print('Checking DocumentDB clusters...')
print('=' * 60)
try:
    docdb = boto3.client('docdb', region_name=region)
    response = docdb.describe_db_clusters()
    print(f'Total DocumentDB clusters: {len(response["DBClusters"])}')
    
    matched = 0
    for cluster in response['DBClusters']:
        cluster_id = cluster['DBClusterIdentifier']
        cluster_arn = cluster['DBClusterArn']
        try:
            tags_response = docdb.list_tags_for_resource(ResourceName=cluster_arn)
            tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
            has_tag = tags.get(tag_key) == tag_value
            if has_tag:
                matched += 1
            status = '✓ HAS TAG' if has_tag else '✗ no tag'
            print(f'  - {cluster_id}: {status}')
            if tags:
                print(f'    Tags: {tags}')
        except Exception as e:
            print(f'  - {cluster_id}: Error getting tags - {e}')
    
    print(f'\nMatched DocumentDB clusters: {matched}')
except Exception as e:
    print(f'Error: {e}')

print('\n' + '=' * 60)
print('Checking Application Load Balancers...')
print('=' * 60)
try:
    elbv2 = boto3.client('elbv2', region_name=region)
    response = elbv2.describe_load_balancers()
    albs = [lb for lb in response['LoadBalancers'] if lb['Type'] == 'application']
    print(f'Total ALBs: {len(albs)}')
    
    matched = 0
    for lb in albs:
        lb_name = lb['LoadBalancerName']
        lb_arn = lb['LoadBalancerArn']
        try:
            tags_response = elbv2.describe_tags(ResourceArns=[lb_arn])
            tags = {}
            if tags_response['TagDescriptions']:
                tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0].get('Tags', [])}
            has_tag = tags.get(tag_key) == tag_value
            if has_tag:
                matched += 1
            status = '✓ HAS TAG' if has_tag else '✗ no tag'
            lb_dimension = lb_arn.split(':loadbalancer/')[1]
            print(f'  - {lb_name}: {status}')
            print(f'    Dimension: {lb_dimension}')
            if tags:
                print(f'    Tags: {tags}')
        except Exception as e:
            print(f'  - {lb_name}: Error getting tags - {e}')
    
    print(f'\nMatched ALBs: {matched}')
except Exception as e:
    print(f'Error: {e}')

print('\n' + '=' * 60)
print('Summary')
print('=' * 60)
print(f'Tag filter: {tag_key}={tag_value}')
print(f'Region: {region}')
