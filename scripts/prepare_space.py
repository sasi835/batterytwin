"""Stage only approved project runtime assets for a public Hugging Face Docker Space."""
import json
import shutil
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.utils.config import ROOT

README='''---
title: BatteryTwin
emoji: 🔋
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
python_version: "3.12"
---

# BatteryTwin — AI-Based EV Battery Health Monitoring

Streamlit research dashboard served in a Docker container. Trained artifacts load at startup; there is no online retraining.

Includes NASA laboratory battery replay, next-cycle SOH, exploratory RUL, unsupervised novelty, derived discharge charge tracking, utilization scenarios, PCA/SHAP plots and honest benchmark comparisons.

Four laboratory cells are not an EV fleet validation. Charge targets are derived proxies, not measured BMS SOC. Unlabeled novelty is not fault diagnosis. Gaussian nominal 90% RUL ranges cover only 26.25% of held-out observations. Utilization planning does not establish lifetime gains.

Training: B0005 + B0007; validation: B0018; testing: B0006. SOH is capacity / 2 Ah × 100, with 70% EOL. Persistence outperforms learned SOH models in the primary benchmark.

The About page provides the academic report. The original FastAPI backend is retained in the project source; this public Space serves the Streamlit UI on port 7860.

Data source: [NASA Li-ion Battery Aging Datasets](https://catalog.data.gov/dataset/li-ion-battery-aging-datasets).
Reference adaptation: [supplied EV battery repository](https://github.com/ahmedmhb/AI-Based-Pedictive-Diagnosis-and-Lifetime-Optimization-for-EVs-Battery).
'''

def stage():
    destination=ROOT/'output/huggingface-space'
    destination.mkdir(parents=True,exist_ok=True)
    files=['Dockerfile','.dockerignore','streamlit_app.py','requirements-runtime.txt','requirements-streamlit.txt',
           'scripts/container_start.py','scripts/smoke_inference.py','output/pdf/BatteryTwin_IEEE_Report.pdf',
           'docs/REFERENCE_COMPARISON.md','docs/references.json','.streamlit/config.toml','configs/config.yaml']
    directories=['api','src','models','data/processed','artifacts/plots','artifacts/results']
    for directory in directories:
        files.extend(str(path.relative_to(ROOT)).replace('\\','/') for path in (ROOT/directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ['.pyc','.part'])
    for relative in sorted(set(files)):
        source=ROOT/relative
        if not source.exists():
            raise FileNotFoundError(relative)
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    (destination/'README.md').write_text(README,encoding='utf8')
    # Do not let old/unapproved files left in the staging directory be uploaded.
    approved=set(files)|{'README.md'}
    unexpected=[str(p.relative_to(destination)).replace('\\','/') for p in destination.rglob('*') if p.is_file() and str(p.relative_to(destination)).replace('\\','/') not in approved]
    if unexpected:
        raise RuntimeError(f'Unexpected staged files: {unexpected}; inspect manually before publishing')
    manifest={'files':sorted(approved),'bytes':sum((destination/p).stat().st_size for p in approved),
              'excluded':['credentials','.env','.venv','node_modules','raw data','temporary reference downloads','local logs','screenshots']}
    (ROOT/'artifacts/results/space_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(f'Staged {len(approved)} approved files ({manifest["bytes"]/1024/1024:.1f} MiB) at {destination}')
    return destination

if __name__=='__main__':
    stage()
