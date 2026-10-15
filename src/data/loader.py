"""Inspect actual NASA MATLAB structures, then extract discharge-cycle summaries."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from scipy.io import loadmat
from src.utils.config import ROOT

SENSOR_MAP = {'Voltage_measured':'voltage','Current_measured':'current',
              'Temperature_measured':'temperature','Time':'time'}

def load_cycles(raw: PathLike = None) -> pd.DataFrame:
    """Validate source fields and preserve measurements without inventing sensors."""
    raw = ROOT/'data/raw' if raw is None else raw
    rows, schemas = [], {}
    for path in sorted(raw.glob('B*.mat')):
        battery = path.stem
        mat = loadmat(path, simplify_cells=True)
        if battery not in mat or 'cycle' not in mat[battery]:
            raise ValueError(f'{battery}: missing cycle structure')
        count = 0
        for cycle in mat[battery]['cycle']:
            if cycle['type'] != 'discharge':
                continue
            count += 1
            data = cycle['data']
            missing = set(SENSOR_MAP).union({'Capacity'}) - set(data)
            if missing:
                raise ValueError(f'{battery}: missing required fields {missing}')
            schemas[battery] = {k: {'type':type(v).__name__, 'shape':list(np.shape(v))} for k,v in data.items()}
            row = {'battery_id':battery, 'cycle':count, 'capacity_ah':float(data['Capacity']),
                   'ambient_temperature':float(cycle['ambient_temperature'])}
            for source, name in SENSOR_MAP.items():
                values = np.asarray(data[source], dtype=float).reshape(-1)
                values = values[np.isfinite(values)]
                if not len(values):
                    raise ValueError(f'{battery} cycle {count}: empty {source}')
                if name == 'time':
                    row['discharge_duration'] = float(values.max()-values.min())
                else:
                    for stat, fun in [('mean',np.mean),('min',np.min),('max',np.max),('std',np.std)]:
                        row[f'{name}_{stat}'] = float(fun(values))
            rows.append(row)
    if not rows:
        raise FileNotFoundError('No NASA MAT files. Run python scripts/download_data.py first.')
    (ROOT/'artifacts/results/source_schema.json').write_text(json.dumps(schemas, indent=2))
    return pd.DataFrame(rows)

# A forward-compatible path alias keeps the API documented without platform coupling.
from pathlib import Path
PathLike = Path
