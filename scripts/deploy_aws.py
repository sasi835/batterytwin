"""Prepare, launch and check the BatteryTwin Docker demo on AWS Lightsail.

Default mode is offline preparation. --plan reads AWS; --apply creates a billed
instance and requires approval of the printed account, region and monthly cap.
No AWS or Hugging Face credentials are copied to the server.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'aws'
STATE = ROOT / 'artifacts/results/aws_deployment.json'
REPO = 'sasi468896/aml_cat'
REVISION = 'ab5ba052e5779c10652fb32747324213a5895f23'


def aws(args, *command):
    result = subprocess.run(
        ['aws', '--profile', args.profile, '--region', args.region,
         '--no-cli-pager', '--output', 'json', '--cli-connect-timeout', '10',
         '--cli-read-timeout', '30', *command],
        capture_output=True, text=True, encoding='utf-8', timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout or '{}')


def prepare():
    manifest = json.loads((ROOT / 'artifacts/results/space_manifest.json').read_text(encoding='utf-8-sig'))
    files = sorted(manifest['files'])
    for name in files:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError(f'Invalid runtime path: {name}')
    downloader = f'''import json, time, urllib.request
from pathlib import Path
from urllib.parse import quote
files = json.loads({json.dumps(json.dumps(files))})
root = Path('/opt/batterytwin')
base = 'https://huggingface.co/spaces/{REPO}/resolve/{REVISION}/'
for name in files:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(base + quote(name, safe='/'), timeout=120) as response:
                with target.open('wb') as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    print('Downloaded:', name, flush=True)
'''
    user_data = '''#!/bin/bash
set -Eeuo pipefail
exec > >(tee -a /var/log/batterytwin-deploy.log) 2>&1
trap 'echo "BatteryTwin bootstrap failed at line $LINENO"' ERR
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends docker.io python3 ca-certificates
systemctl enable --now docker
mkdir -p /opt/batterytwin
python3 - <<'BATTERYTWIN_DOWNLOAD'
''' + downloader + '''BATTERYTWIN_DOWNLOAD
cd /opt/batterytwin
docker build --tag batterytwin:''' + REVISION[:12] + ''' .
docker run --detach --name batterytwin --restart unless-stopped \
  --memory 3g --cpus 2 --pids-limit 512 \
  --log-opt max-size=10m --log-opt max-file=3 \
  --publish 80:7860 batterytwin:''' + REVISION[:12] + '''
for attempt in $(seq 1 120); do
  status=$(docker inspect --format '{{.State.Health.Status}}' batterytwin)
  if [ "$status" = healthy ]; then
    docker exec batterytwin python scripts/smoke_inference.py | tee /opt/batterytwin-inference.json
    echo 'BatteryTwin Docker deployment and model inference verified.'
    exit 0
  fi
  sleep 10
done
docker logs --tail 100 batterytwin
exit 1
'''
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'user-data.sh').write_text(user_data, encoding='utf-8', newline='\n')
    plan = {'service': 'AWS Lightsail', 'region': 'us-east-1',
            'instance_name': 'batterytwin-streamlit', 'os': 'Ubuntu 24.04 LTS',
            'memory_gb': 4, 'minimum_vcpu': 2, 'monthly_usd_cap': 24,
            'public_ports': [80], 'ssh': 'AWS browser SSH address ranges only',
            'source_repo': REPO, 'source_revision': REVISION,
            'runtime_files': len(files), 'local_docker_required': False,
            'status': 'Prepared; AWS authentication and launch approval required',
            'pricing_source': 'https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html'}
    (OUT / 'deployment-plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    return user_data, plan


def remote_plan(args, plan):
    identity = aws(args, 'sts', 'get-caller-identity')
    bundles = aws(args, 'lightsail', 'get-bundles')['bundles']
    candidates = [b for b in bundles if b.get('isActive')
                  and b.get('ramSizeInGb') == 4 and b.get('cpuCount', 0) >= 2
                  and 'LINUX_UNIX' in b.get('supportedPlatforms', [])
                  and b.get('publicIpv4AddressCount', 1) >= 1
                  and 0 < b.get('price', 0) <= args.max_monthly_usd]
    if not candidates:
        raise RuntimeError('No active 4 GB Linux IPv4 bundle within the approved monthly cap.')
    bundle = min(candidates, key=lambda b: b['price'])
    blueprints = aws(args, 'lightsail', 'get-blueprints')['blueprints']
    ubuntu = [b for b in blueprints if b.get('isActive') and b.get('blueprintId') == 'ubuntu_24_04']
    if not ubuntu:
        raise RuntimeError('Ubuntu 24.04 blueprint unavailable; review another image before launching.')
    regions = aws(args, 'lightsail', 'get-regions', '--include-availability-zones')['regions']
    region = next(r for r in regions if r['name'] == args.region)
    zone = sorted(z['zoneName'] for z in region['availabilityZones'])[0]
    plan.update({'account': identity['Account'], 'region': args.region,
                 'instance_name': args.name, 'bundle_id': bundle['bundleId'],
                 'monthly_usd': bundle['price'], 'monthly_usd_cap': args.max_monthly_usd,
                 'disk_gb': bundle['diskSizeInGb'], 'blueprint_id': ubuntu[0]['blueprintId'],
                 'availability_zone': zone, 'status': 'AWS configuration checked; not launched'})
    (OUT / 'deployment-plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    return plan


def check(args):
    instance = aws(args, 'lightsail', 'get-instance', '--instance-name', args.name)['instance']
    record = {'service': 'Lightsail', 'region': args.region, 'instance_name': args.name,
              'instance_state': instance['state']['name'], 'live_verified': False}
    ip = instance.get('publicIpAddress')
    if ip:
        record['url'] = f'http://{ip}'
        try:
            with urllib.request.urlopen(record['url'] + '/_stcore/health', timeout=15) as response:
                record['http_health_ok'] = response.status == 200 and response.read().strip() == b'ok'
        except Exception as error:
            record['http_health_ok'] = False
            record['health_error'] = str(error)
    record['verification_note'] = 'Health alone is insufficient: verify UI and /opt/batterytwin-inference.json on server.'
    STATE.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='default')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--name', default='batterytwin-streamlit')
    parser.add_argument('--max-monthly-usd', type=float, default=24)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Read AWS identity, bundles and blueprints only')
    mode.add_argument('--apply', action='store_true', help='Create the approved billed Lightsail instance')
    mode.add_argument('--check', action='store_true', help='Check an existing instance and HTTP health')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{1,60}[a-zA-Z0-9]', args.name):
        parser.error('Use a simple alphanumeric instance name with optional hyphens.')
    if args.max_monthly_usd <= 0:
        parser.error('Monthly price cap must be positive.')
    if args.check:
        print(json.dumps(check(args), indent=2))
        return
    user_data, plan = prepare()
    if args.plan or args.apply:
        plan = remote_plan(args, plan)
    print(json.dumps(plan, indent=2), flush=True)
    if not args.apply:
        return
    existing = aws(args, 'lightsail', 'get-instances')['instances']
    if any(i['name'] == args.name for i in existing):
        raise RuntimeError('Instance name already exists. Use --check; no existing instance was modified.')
    create = {'instanceNames': [args.name], 'availabilityZone': plan['availability_zone'],
              'blueprintId': plan['blueprint_id'], 'bundleId': plan['bundle_id'],
              'ipAddressType': 'ipv4', 'userData': user_data,
              'tags': [{'key': 'Project', 'value': 'BatteryTwin'}, {'key': 'ManagedBy', 'value': 'BatteryTwin-deploy'}]}
    request = OUT / 'create-instance.json'
    request.write_text(json.dumps(create), encoding='utf-8')
    aws(args, 'lightsail', 'create-instances', '--cli-input-json', f'file://{request.as_posix()}')
    record = {**plan, 'status': 'Instance requested; build and live verification pending', 'live_verified': False}
    STATE.write_text(json.dumps(record, indent=2), encoding='utf-8')
    ports = [{'fromPort': 80, 'toPort': 80, 'protocol': 'tcp', 'cidrs': ['0.0.0.0/0']},
             {'fromPort': 22, 'toPort': 22, 'protocol': 'tcp', 'cidrListAliases': ['lightsail-connect']}]
    firewall = OUT / 'firewall.json'
    firewall.write_text(json.dumps(ports), encoding='utf-8')
    for attempt in range(24):
        current = aws(args, 'lightsail', 'get-instance', '--instance-name', args.name)['instance']
        if current['state']['name'] == 'running':
            aws(args, 'lightsail', 'put-instance-public-ports', '--instance-name', args.name,
                '--port-infos', f'file://{firewall.as_posix()}')
            print(json.dumps(check(args), indent=2), flush=True)
            print('Docker build runs on AWS. Check again in 5-15 minutes with --check.', flush=True)
            return
        time.sleep(10)
    raise RuntimeError('Instance requested but startup timed out; inspect Lightsail before retrying.')


if __name__ == '__main__':
    main()
