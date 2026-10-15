"""Stage an explicit BatteryTwin runtime package for Vercel Container Runtime."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'output/vercel/batterytwin'


def stage():
    manifest = json.loads((ROOT / 'artifacts/results/space_manifest.json').read_text(encoding='utf-8-sig'))
    excluded = {'README.md', 'artifacts/results/huggingface_deployment.json',
                'artifacts/results/space_manifest.json'}
    files = set(manifest['files']) - excluded
    files.update({'Dockerfile.vercel', 'vercel.json'})
    for name in sorted(files):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Invalid runtime path: {name}')
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    unexpected = [str(p.relative_to(DESTINATION)) for p in DESTINATION.rglob('*')
                  if p.is_file() and '.vercel' not in p.relative_to(DESTINATION).parts
                  and p.relative_to(DESTINATION).as_posix() not in files]
    if unexpected:
        raise RuntimeError(f'Unexpected staged files; inspect before upload: {unexpected}')
    record = {'files': sorted(files), 'bytes': sum((DESTINATION / p).stat().st_size for p in files),
              'destination': str(DESTINATION), 'runtime': 'Vercel Container Runtime beta',
              'excluded': ['credentials', '.env', '.venv', 'node_modules', 'raw data',
                           'personal lab records', 'local logs', 'screenshots'],
              'status': 'Prepared; Vercel login, deployment and live verification pending'}
    (ROOT / 'artifacts/results/vercel_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(f'Staged {len(files)} runtime files ({record["bytes"]/1024/1024:.1f} MiB) at {DESTINATION}')
    return DESTINATION


if __name__ == '__main__':
    stage()
