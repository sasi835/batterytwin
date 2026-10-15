"""ECR deployment checks use mocked AWS responses and never create resources."""
import base64
import json
import re
import sys

import pytest
import yaml

from scripts import deploy_ecr as deploy


def test_cloud_build_shell_and_embedded_downloader(tmp_path):
    build, _ = deploy.templates('batterytwin')
    spec = yaml.safe_load(build['Resources']['BuildProject']['Properties']['Source']['BuildSpec'])
    command = spec['phases']['pre_build']['commands'][1]
    code = base64.b64decode(re.search(r"b64decode\('([^']+)'\)", command).group(1)).decode()
    compile(code, '<downloader>', 'exec')
    commands = spec['phases']['build']['commands']
    assert next(i for i, c in enumerate(commands) if 'smoke_inference' in c) < next(i for i, c in enumerate(commands) if 'docker push' in c)
    for name, phase in spec['phases'].items():
        (tmp_path / (name + '.sh')).write_text('\n'.join(phase['commands']) + '\n', encoding='utf-8')


def test_deploy_app_refuses_failed_build_before_any_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, 'OUT', tmp_path)
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'build_id': 'failed-build'}))
    monkeypatch.setattr(deploy, 'STATE', state)
    monkeypatch.setattr(sys, 'argv', ['deploy_ecr.py', '--deploy-app'])
    calls = []
    def fake_aws(_args, *command):
        calls.append(command)
        if command[:2] == ('sts', 'get-caller-identity'):
            return {'Account': '000000000000'}
        if command[:2] == ('cloudformation', 'describe-stacks'):
            return {'Stacks': [{'StackStatus': 'CREATE_COMPLETE', 'Outputs': [{'OutputKey': 'BuildProject', 'OutputValue': 'batterytwin'}]}]}
        if command[:2] == ('codebuild', 'batch-get-builds'):
            return {'builds': [{'buildStatus': 'FAILED', 'projectName': 'batterytwin'}]}
        raise AssertionError(f'Unexpected AWS mutation: {command}')
    monkeypatch.setattr(deploy, 'aws', fake_aws)
    with pytest.raises(RuntimeError, match='successful Docker/model-inference build'):
        deploy.main()
    assert not any('create-stack' in call for call in calls)


def test_ecr_source_is_private_and_runtime_image_requires_digest():
    build, app = deploy.templates('batterytwin')
    assert build['Resources']['Repository']['Properties']['ImageTagMutability'] == 'IMMUTABLE'
    assert 'RepositoryPolicyText' not in build['Resources']['Repository']['Properties']
    assert '@sha256:' in app['Parameters']['ImageUri']['AllowedPattern']
    resources = app['Resources']
    assert resources['Service']['Properties']['DesiredCount'] == 1
    assert resources['TaskDefinition']['Properties']['Memory'] == '4096'
    assert all(r['Type'] not in ['AWS::EC2::NatGateway', 'AWS::ElasticLoadBalancingV2::LoadBalancer'] for r in resources.values())


def test_check_records_healthy_task_without_claiming_browser_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, 'OUT', tmp_path)
    state = tmp_path / 'state.json'
    monkeypatch.setattr(deploy, 'STATE', state)
    monkeypatch.setattr(sys, 'argv', ['deploy_ecr.py', '--check'])
    def fake_aws(_args, *command):
        return {
            'get-caller-identity': {'Account': '000000000000'},
            'describe-stacks': {'Stacks': [{'StackStatus': 'CREATE_COMPLETE', 'Outputs': [
                {'OutputKey': 'Cluster', 'OutputValue': 'cluster'}, {'OutputKey': 'Service', 'OutputValue': 'service'}]}]},
            'list-tasks': {'taskArns': ['task']},
            'describe-tasks': {'tasks': [{'taskArn': 'task', 'lastStatus': 'RUNNING', 'healthStatus': 'HEALTHY',
                'attachments': [{'type': 'ElasticNetworkInterface', 'details': [{'name': 'networkInterfaceId', 'value': 'eni'}]}]}]},
            'describe-network-interfaces': {'NetworkInterfaces': [{'Association': {'PublicIp': '192.0.2.1'}}]},
        }[command[1]]
    monkeypatch.setattr(deploy, 'aws', fake_aws)
    deploy.main()
    result = json.loads(state.read_text())
    assert result['task_status'] == 'RUNNING'
    assert result['url'] == 'http://192.0.2.1:7860'
    assert result['live_verified'] is False
