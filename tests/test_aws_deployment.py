"""Deployment guard checks: no real AWS calls or billed resources."""
from argparse import Namespace
import ast
import json

import pytest

from scripts import deploy_aws as deploy


def args():
    return Namespace(profile='default', region='us-east-1', name='batterytwin-streamlit', max_monthly_usd=24)


def test_generated_bootstrap_has_valid_downloader_and_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, 'OUT', tmp_path)
    script, plan = deploy.prepare()
    embedded = script.split("python3 - <<'BATTERYTWIN_DOWNLOAD'\n", 1)[1].split('\nBATTERYTWIN_DOWNLOAD', 1)[0]
    ast.parse(embedded)
    assert len(script.encode()) < 16384
    assert deploy.REVISION in script
    assert 'docker exec batterytwin python scripts/smoke_inference.py' in script
    assert 'AWS_SECRET_ACCESS_KEY' not in script
    assert 'hf auth' not in script
    assert plan['local_docker_required'] is False


def test_remote_plan_rejects_price_above_cap_before_creation(tmp_path, monkeypatch):
    calls = []
    def fake_aws(_args, *command):
        calls.append(command)
        if command[0] == 'sts':
            return {'Account': '000000000000'}
        return {'bundles': [{'isActive': True, 'ramSizeInGb': 4, 'cpuCount': 2,
                             'supportedPlatforms': ['LINUX_UNIX'], 'price': 25}]}
    monkeypatch.setattr(deploy, 'aws', fake_aws)
    monkeypatch.setattr(deploy, 'OUT', tmp_path)
    with pytest.raises(RuntimeError, match='monthly cap'):
        deploy.remote_plan(args(), {})
    assert all('create-instances' not in command for command in calls)


def test_remote_plan_selects_only_compatible_ipv4_bundle(tmp_path, monkeypatch):
    base = {'isActive': True, 'ramSizeInGb': 4, 'cpuCount': 2,
            'supportedPlatforms': ['LINUX_UNIX'], 'diskSizeInGb': 80}
    def fake_aws(_args, *command):
        return {
            'get-caller-identity': {'Account': '000000000000'},
            'get-bundles': {'bundles': [dict(base, bundleId='ipv6', price=20, publicIpv4AddressCount=0),
                                        dict(base, bundleId='ipv4', price=24, publicIpv4AddressCount=1)]},
            'get-blueprints': {'blueprints': [{'isActive': True, 'blueprintId': 'ubuntu_24_04'}]},
            'get-regions': {'regions': [{'name': 'us-east-1', 'availabilityZones': [{'zoneName': 'us-east-1a'}]}]},
        }[command[1]]
    monkeypatch.setattr(deploy, 'aws', fake_aws)
    monkeypatch.setattr(deploy, 'OUT', tmp_path)
    plan = deploy.remote_plan(args(), {})
    assert plan['bundle_id'] == 'ipv4'
    assert plan['monthly_usd'] == 24
    assert plan['status'] == 'AWS configuration checked; not launched'


def test_manifest_path_cannot_escape_server_app(tmp_path, monkeypatch):
    result = tmp_path / 'artifacts/results'
    result.mkdir(parents=True)
    (result / 'space_manifest.json').write_text(json.dumps({'files': ['../../escape']}))
    monkeypatch.setattr(deploy, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='Invalid runtime path'):
        deploy.prepare()
