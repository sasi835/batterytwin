"""Acquire a pinned public mirror of NASA PCoE MAT data; reuse verified cache."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = '5301bd7e469dc8a1320b55719629571f2c02b6fc'
BATTERIES = ['B0005', 'B0006', 'B0007', 'B0018']

def download() -> dict:
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = raw / 'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest = {'dataset': 'NASA PCoE Li-ion Battery Aging', 'revision': REVISION,
                'primary_source': 'https://catalog.data.gov/dataset/li-ion-battery-aging-datasets', 'files': {}}
    for battery in BATTERIES:
        path = raw / f'{battery}.mat'
        url = f'https://raw.githubusercontent.com/changyeon99/Battery-Data-Set/{REVISION}/{battery}.mat'
        if not path.exists():
            with urlopen(url, timeout=120) as response:
                content = response.read()
            if not content.startswith(b'MATLAB 5.0 MAT-file'):
                raise ValueError(f'{battery}: expected MATLAB file, received invalid content')
            tmp = path.with_suffix('.part')
            tmp.write_bytes(content)
            tmp.replace(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = previous.get('files', {}).get(battery, {}).get('sha256')
        if expected and digest != expected:
            raise ValueError(f'{battery}: cached file checksum changed')
        manifest['files'][battery] = {'url': url, 'sha256': digest, 'bytes': path.stat().st_size}
        print(f'{battery}: {path.stat().st_size:,} bytes SHA256 {digest}')
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest

if __name__ == '__main__':
    download()
