"""Inspect, validate, summarize and engineer the cached NASA dataset."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from src.data.loader import load_cycles
from src.data.preprocessing import validate_cycles
from src.data.feature_engineering import engineer
from src.utils.config import ROOT, load_config

def prepare():
    frame,report = validate_cycles(load_cycles())
    engineered = engineer(frame,load_config())
    frame.to_csv(ROOT/'data/processed/cycles.csv',index=False)
    engineered.to_csv(ROOT/'data/processed/features.csv',index=False)
    report['batteries'] = frame.groupby('battery_id').agg(cycles=('cycle','size'),initial_capacity=('capacity_ah','first'),last_capacity=('capacity_ah','last')).to_dict('index')
    report['eol_observed'] = engineered.groupby('battery_id').eol_observed.first().to_dict()
    (ROOT/'artifacts/results/data_quality.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report['batteries'],indent=2))
    print('Observed 70% EOL:',report['eol_observed'])
    return frame,engineered

if __name__=='__main__':
    prepare()
