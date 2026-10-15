"""Prepare an ECR + CodeBuild + ECS Fargate deployment. Mutations are explicit.

Default: generate reviewable CloudFormation templates locally. --plan is read-only.
Run each creation/build action only after the deployment costs are approved.
"""
import argparse
import base64
import json
from pathlib import Path
import re
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.deploy_aws import aws, prepare as prepare_source, REPO, REVISION, ROOT

OUT = ROOT / 'output/aws-ecr'
STATE = ROOT / 'artifacts/results/aws_ecr_deployment.json'


def ref(name):
    return {'Ref': name}


def sub(value):
    return {'Fn::Sub': value}


def attr(name, field):
    return {'Fn::GetAtt': [name, field]}


def role(service, statements, condition=None):
    trust = {'Effect': 'Allow', 'Principal': {'Service': service}, 'Action': 'sts:AssumeRole'}
    if condition:
        trust['Condition'] = condition
    return {'Type': 'AWS::IAM::Role', 'Properties': {
        'AssumeRolePolicyDocument': {'Version': '2012-10-17', 'Statement': [trust]},
        'Policies': [{'PolicyName': 'BatteryTwinScopedAccess',
                      'PolicyDocument': {'Version': '2012-10-17', 'Statement': statements}}]}}


def templates(name):
    user_data, _ = prepare_source()
    downloader = user_data.split("python3 - <<'BATTERYTWIN_DOWNLOAD'\n", 1)[1].split('\nBATTERYTWIN_DOWNLOAD', 1)[0]
    # CodeBuild's build directory replaces the Lightsail server's application path.
    downloader = downloader.replace("Path('/opt/batterytwin')", "Path.cwd()")
    encoded = base64.b64encode(downloader.encode()).decode()
    buildspec = {'version': '0.2', 'env': {'shell': 'bash'}, 'phases': {
        'pre_build': {'commands': [
            'set -euo pipefail',
            f"python3 -c \"import base64; exec(base64.b64decode('{encoded}'))\"",
            'aws ecr get-login-password --region "$AWS_DEFAULT_REGION" | docker login --username AWS --password-stdin "$REPOSITORY_URI"']},
        'build': {'commands': [
            'set -euo pipefail',
            'docker build --tag "$REPOSITORY_URI:$IMAGE_TAG" .',
            'docker run --rm --entrypoint python "$REPOSITORY_URI:$IMAGE_TAG" scripts/smoke_inference.py',
            'docker run --detach --name batterytwin-verify --publish 127.0.0.1:17860:7860 "$REPOSITORY_URI:$IMAGE_TAG"',
            'ready=0; for attempt in $(seq 1 60); do if curl --fail --silent http://127.0.0.1:17860/_stcore/health; then ready=1; break; fi; sleep 5; done; docker logs --tail 50 batterytwin-verify; test "$ready" = 1',
            'docker stop batterytwin-verify',
            'docker push "$REPOSITORY_URI:$IMAGE_TAG"']}}}
    log_name = f'/aws/codebuild/{name}'
    build = {'AWSTemplateFormatVersion': '2010-09-09',
             'Description': 'BatteryTwin private ECR repository and remote Docker build', 'Resources': {}}
    r = build['Resources']
    r['Repository'] = {'Type': 'AWS::ECR::Repository', 'DeletionPolicy': 'Retain',
                       'UpdateReplacePolicy': 'Retain', 'Properties': {
                           'RepositoryName': name, 'ImageTagMutability': 'IMMUTABLE',
                           'ImageScanningConfiguration': {'ScanOnPush': True},
                           'EncryptionConfiguration': {'EncryptionType': 'AES256'}}}
    r['BuildLogs'] = {'Type': 'AWS::Logs::LogGroup', 'Properties': {'LogGroupName': log_name, 'RetentionInDays': 7}}
    r['BuildRole'] = role('codebuild.amazonaws.com', [
        {'Effect': 'Allow', 'Action': ['ecr:GetAuthorizationToken'], 'Resource': '*'},
        {'Effect': 'Allow', 'Action': ['ecr:BatchCheckLayerAvailability', 'ecr:InitiateLayerUpload',
            'ecr:UploadLayerPart', 'ecr:CompleteLayerUpload', 'ecr:PutImage',
            'ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'], 'Resource': attr('Repository', 'Arn')},
        {'Effect': 'Allow', 'Action': ['logs:CreateLogStream', 'logs:PutLogEvents'],
         'Resource': sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:' + log_name + ':*')}
    ], {'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')},
        'ArnEquals': {'aws:SourceArn': sub('arn:${AWS::Partition}:codebuild:${AWS::Region}:${AWS::AccountId}:project/' + name)}})
    r['BuildProject'] = {'Type': 'AWS::CodeBuild::Project', 'DependsOn': 'BuildLogs', 'Properties': {
        'Name': name, 'ServiceRole': attr('BuildRole', 'Arn'), 'TimeoutInMinutes': 30,
        'QueuedTimeoutInMinutes': 30, 'ConcurrentBuildLimit': 1,
        'Artifacts': {'Type': 'NO_ARTIFACTS'},
        'Source': {'Type': 'NO_SOURCE', 'BuildSpec': yaml.safe_dump(buildspec, sort_keys=False)},
        'Environment': {'Type': 'LINUX_CONTAINER', 'ComputeType': 'BUILD_GENERAL1_MEDIUM',
                        'Image': 'aws/codebuild/standard:7.0', 'PrivilegedMode': True,
                        'EnvironmentVariables': [{'Name': 'REPOSITORY_URI', 'Value': attr('Repository', 'RepositoryUri')},
                                                 {'Name': 'IMAGE_TAG', 'Value': REVISION[:12]}]},
        'LogsConfig': {'CloudWatchLogs': {'Status': 'ENABLED', 'GroupName': ref('BuildLogs')}}}}
    build['Outputs'] = {'RepositoryUri': {'Value': attr('Repository', 'RepositoryUri')},
                        'RepositoryArn': {'Value': attr('Repository', 'Arn')},
                        'BuildProject': {'Value': ref('BuildProject')}}

    app = {'AWSTemplateFormatVersion': '2010-09-09', 'Description': 'BatteryTwin public research demo on ECS Fargate',
           'Parameters': {'ImageUri': {'Type': 'String', 'AllowedPattern': r'.+@sha256:[a-f0-9]{64}'},
                          'RepositoryArn': {'Type': 'String'}}, 'Resources': {}}
    r = app['Resources']
    r['VPC'] = {'Type': 'AWS::EC2::VPC', 'Properties': {'CidrBlock': '10.72.0.0/24', 'EnableDnsSupport': True, 'EnableDnsHostnames': True}}
    r['InternetGateway'] = {'Type': 'AWS::EC2::InternetGateway'}
    r['GatewayAttachment'] = {'Type': 'AWS::EC2::VPCGatewayAttachment', 'Properties': {'VpcId': ref('VPC'), 'InternetGatewayId': ref('InternetGateway')}}
    r['Subnet'] = {'Type': 'AWS::EC2::Subnet', 'Properties': {'VpcId': ref('VPC'), 'CidrBlock': '10.72.0.0/25', 'MapPublicIpOnLaunch': True}}
    r['Routes'] = {'Type': 'AWS::EC2::RouteTable', 'Properties': {'VpcId': ref('VPC')}}
    r['DefaultRoute'] = {'Type': 'AWS::EC2::Route', 'DependsOn': 'GatewayAttachment', 'Properties': {'RouteTableId': ref('Routes'), 'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': ref('InternetGateway')}}
    r['SubnetRoutes'] = {'Type': 'AWS::EC2::SubnetRouteTableAssociation', 'Properties': {'RouteTableId': ref('Routes'), 'SubnetId': ref('Subnet')}}
    r['SecurityGroup'] = {'Type': 'AWS::EC2::SecurityGroup', 'Properties': {'GroupDescription': 'BatteryTwin Streamlit demo', 'VpcId': ref('VPC'),
        'SecurityGroupIngress': [{'IpProtocol': 'tcp', 'FromPort': 7860, 'ToPort': 7860, 'CidrIp': '0.0.0.0/0'}]}}
    r['Cluster'] = {'Type': 'AWS::ECS::Cluster'}
    r['AppLogs'] = {'Type': 'AWS::Logs::LogGroup', 'Properties': {'RetentionInDays': 7}}
    r['ExecutionRole'] = role('ecs-tasks.amazonaws.com', [
        {'Effect': 'Allow', 'Action': ['ecr:GetAuthorizationToken'], 'Resource': '*'},
        {'Effect': 'Allow', 'Action': ['ecr:BatchCheckLayerAvailability', 'ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'], 'Resource': ref('RepositoryArn')},
        {'Effect': 'Allow', 'Action': ['logs:CreateLogStream', 'logs:PutLogEvents'], 'Resource': attr('AppLogs', 'Arn')}
    ], {'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')},
        'ArnLike': {'aws:SourceArn': sub('arn:${AWS::Partition}:ecs:${AWS::Region}:${AWS::AccountId}:*')}})
    r['TaskDefinition'] = {'Type': 'AWS::ECS::TaskDefinition', 'Properties': {
        'Cpu': '512', 'Memory': '4096', 'NetworkMode': 'awsvpc', 'RequiresCompatibilities': ['FARGATE'],
        'RuntimePlatform': {'CpuArchitecture': 'X86_64', 'OperatingSystemFamily': 'LINUX'},
        'ExecutionRoleArn': attr('ExecutionRole', 'Arn'),
        'ContainerDefinitions': [{'Name': 'batterytwin', 'Image': ref('ImageUri'), 'Essential': True,
            'PortMappings': [{'ContainerPort': 7860, 'Protocol': 'tcp'}],
            'Environment': [{'Name': 'OMP_NUM_THREADS', 'Value': '1'}, {'Name': 'MKL_NUM_THREADS', 'Value': '1'}],
            'HealthCheck': {'Command': ['CMD-SHELL', 'python -c "import urllib.request; urllib.request.urlopen(\'http://127.0.0.1:7860/_stcore/health\')"'],
                            'Interval': 30, 'Timeout': 10, 'Retries': 3, 'StartPeriod': 180},
            'LogConfiguration': {'LogDriver': 'awslogs', 'Options': {'awslogs-group': ref('AppLogs'), 'awslogs-region': ref('AWS::Region'), 'awslogs-stream-prefix': 'streamlit'}}}]}}
    r['Service'] = {'Type': 'AWS::ECS::Service', 'DependsOn': ['DefaultRoute', 'SubnetRoutes'], 'Properties': {
        'Cluster': ref('Cluster'), 'TaskDefinition': ref('TaskDefinition'), 'LaunchType': 'FARGATE',
        'PlatformVersion': 'LATEST', 'DesiredCount': 1,
        'DeploymentConfiguration': {'MaximumPercent': 100, 'MinimumHealthyPercent': 0,
                                     'DeploymentCircuitBreaker': {'Enable': True, 'Rollback': True}},
        'NetworkConfiguration': {'AwsvpcConfiguration': {'AssignPublicIp': 'ENABLED', 'Subnets': [ref('Subnet')], 'SecurityGroups': [ref('SecurityGroup')]}}}}
    app['Outputs'] = {'Cluster': {'Value': ref('Cluster')}, 'Service': {'Value': attr('Service', 'Name')}, 'LogGroup': {'Value': ref('AppLogs')}}
    return build, app


def save_state(**updates):
    previous = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    previous.update(updates)
    STATE.write_text(json.dumps(previous, indent=2), encoding='utf-8')


def stack_outputs(args, stack):
    description = aws(args, 'cloudformation', 'describe-stacks', '--stack-name', stack)['Stacks'][0]
    if description['StackStatus'] not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
        raise RuntimeError(f"Stack {stack}: {description['StackStatus']}; inspect events before continuing.")
    return {o['OutputKey']: o['OutputValue'] for o in description['Outputs']}


def create_stack(args, suffix, file, parameters=None):
    command = ['cloudformation', 'create-stack', '--stack-name', f'{args.name}-{suffix}',
               '--template-body', f'file://{file.as_posix()}', '--capabilities', 'CAPABILITY_IAM',
               '--tags', 'Key=Project,Value=BatteryTwin']
    if parameters:
        parameter_file = OUT / f'{suffix}-parameters.json'
        parameter_file.write_text(json.dumps([{'ParameterKey': k, 'ParameterValue': v} for k, v in parameters.items()]), encoding='utf-8')
        command += ['--parameters', f'file://{parameter_file.as_posix()}']
    print(json.dumps(aws(args, *command), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='default')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--name', default='batterytwin')
    modes = parser.add_mutually_exclusive_group()
    for action in ['plan', 'create-build', 'start-build', 'build-status', 'deploy-app', 'check']:
        modes.add_argument('--' + action, action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,30}', args.name):
        parser.error('Name must be a short lowercase AWS resource name.')
    OUT.mkdir(parents=True, exist_ok=True)
    build, app = templates(args.name)
    for name, template in [('build', build), ('app', app)]:
        (OUT / f'{name}.json').write_text(json.dumps(template, indent=2), encoding='utf-8')
    if not any([args.plan, args.create_build, args.start_build, args.build_status, args.deploy_app, args.check]):
        print(f'Prepared ECR/CodeBuild and ECS templates in {OUT}. No AWS requests or resource creation.')
        return
    identity = aws(args, 'sts', 'get-caller-identity')
    print(json.dumps({'account': identity['Account'], 'region': args.region, 'name': args.name}))
    if args.plan:
        for name in ['build', 'app']:
            aws(args, 'cloudformation', 'validate-template', '--template-body', f'file://{(OUT / (name + ".json")).as_posix()}')
        print('Both templates validated by AWS. No resources created.')
    elif args.create_build:
        create_stack(args, 'build', OUT / 'build.json')
        save_state(account=identity['Account'], region=args.region, build_stack=f'{args.name}-build', resources_created=True, status='ECR/build stack requested; no successful build claimed', live_verified=False)
    elif args.start_build:
        outputs = stack_outputs(args, f'{args.name}-build')
        response = aws(args, 'codebuild', 'start-build', '--project-name', outputs['BuildProject'])['build']
        save_state(build_id=response['id'], repository_uri=outputs['RepositoryUri'], status='Docker build requested; not yet verified')
        print(json.dumps({'build_id': response['id'], 'status': response['buildStatus']}))
    elif args.build_status:
        state = json.loads(STATE.read_text(encoding='utf-8'))
        build = aws(args, 'codebuild', 'batch-get-builds', '--ids', state['build_id'])['builds'][0]
        save_state(build_status=build['buildStatus'], build_logs=build.get('logs', {}))
        print(json.dumps({k: build.get(k) for k in ['id', 'buildStatus', 'currentPhase', 'logs', 'phases']}, indent=2))
    elif args.deploy_app:
        outputs = stack_outputs(args, f'{args.name}-build')
        state = json.loads(STATE.read_text(encoding='utf-8'))
        build = aws(args, 'codebuild', 'batch-get-builds', '--ids', state['build_id'])['builds'][0]
        if build['buildStatus'] != 'SUCCEEDED' or build['projectName'] != outputs['BuildProject']:
            raise RuntimeError('A successful Docker/model-inference build for this project is required.')
        image = aws(args, 'ecr', 'describe-images', '--repository-name', args.name, '--image-ids', 'imageTag=' + REVISION[:12])['imageDetails'][0]
        image_uri = outputs['RepositoryUri'] + '@' + image['imageDigest']
        create_stack(args, 'app', OUT / 'app.json', {'ImageUri': image_uri, 'RepositoryArn': outputs['RepositoryArn']})
        save_state(app_stack=f'{args.name}-app', image_uri=image_uri, build_status='SUCCEEDED', docker_build_verified=True, status='ECS service requested; live app verification pending', live_verified=False)
    elif args.check:
        outputs = stack_outputs(args, f'{args.name}-app')
        task_ids = aws(args, 'ecs', 'list-tasks', '--cluster', outputs['Cluster'], '--service-name', outputs['Service'])['taskArns']
        if not task_ids:
            print('No running service tasks. Inspect ECS service events and CloudWatch logs.')
            return
        tasks = aws(args, 'ecs', 'describe-tasks', '--cluster', outputs['Cluster'], '--tasks', *task_ids)['tasks']
        for task in tasks:
            record = {'task': task['taskArn'], 'task_status': task['lastStatus'], 'health': task.get('healthStatus')}
            for attachment in task.get('attachments', []):
                if attachment['type'] == 'ElasticNetworkInterface':
                    details = {d['name']: d['value'] for d in attachment['details']}
                    interface = aws(args, 'ec2', 'describe-network-interfaces', '--network-interface-ids', details['networkInterfaceId'])['NetworkInterfaces'][0]
                    ip = interface.get('Association', {}).get('PublicIp')
                    if ip:
                        record['url'] = f'http://{ip}:7860'
            print(json.dumps(record, indent=2))
            previous = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
            verified = bool(previous.get('live_verified') and previous.get('task') == record['task']
                            and record['task_status'] == 'RUNNING' and record['health'] == 'HEALTHY')
            save_state(**record, live_verified=verified,
                       status='Live application verified' if verified else 'Task inspected; browser and inference verification still required')


if __name__ == '__main__':
    main()
