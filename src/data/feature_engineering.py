"""Forecast cycle t using only completed cycles <=t-1; targets never enter features."""
import numpy as np
import pandas as pd

SENSORS = ['voltage_mean','voltage_min','voltage_max','voltage_std','current_mean','current_std',
           'temperature_mean','temperature_max','temperature_std','discharge_duration']
FEATURES = ['cycle','lag_capacity_ah','rolling_capacity_mean','rolling_capacity_std','capacity_change'] + [f'lag_{x}' for x in SENSORS]

def next_features(history: pd.DataFrame, window: int = 5) -> dict:
    """Build a single next-cycle forecast input using a completed ordered history."""
    history = history.sort_values('cycle')
    if history.empty:
        raise ValueError('At least one completed cycle is required')
    last = history.iloc[-1]
    caps = history.capacity_ah.tail(window)
    result = {'cycle':float(last.cycle+1),'lag_capacity_ah':float(last.capacity_ah),
              'rolling_capacity_mean':float(caps.mean()),'rolling_capacity_std':float(caps.std(ddof=0)),
              'capacity_change':float(history.capacity_ah.iloc[-1]-history.capacity_ah.iloc[-2]) if len(history)>1 else 0.0}
    result.update({f'lag_{x}':float(last[x]) for x in SENSORS})
    return result

def engineer(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    nominal, threshold = config['dataset']['rated_capacity_ah'], config['dataset']['eol_soh']
    for battery, group in frame.groupby('battery_id', sort=False):
        group = group.sort_values('cycle').reset_index(drop=True)
        crossings = group.loc[group.capacity_ah/nominal*100<=threshold,'cycle']
        eol = int(crossings.iloc[0]) if len(crossings) else None
        for i in range(1,len(group)):
            row = next_features(group.iloc[:i],config['features']['rolling_window'])
            target = group.iloc[i]
            row.update({'battery_id':battery,'soh':float(target.capacity_ah/nominal*100),
                        'capacity_ah':float(target.capacity_ah),'rul':max(eol-int(target.cycle),0) if eol else np.nan,
                        'eol_observed':eol is not None})
            rows.append(row)
    return pd.DataFrame(rows)

def sequences(frame: pd.DataFrame, transformed: np.ndarray, length: int, target: str = 'soh') -> tuple:
    """Construct sequences within one cell; return target indices for fair comparison."""
    xs, ys, indices = [], [], []
    position = {index:i for i,index in enumerate(frame.index)}
    for _, group in frame.groupby('battery_id',sort=False):
        ordered = group.sort_values('cycle').index.to_list()
        for j in range(length-1,len(ordered)):
            idx = ordered[j]
            if pd.isna(frame.loc[idx,target]):
                continue
            xs.append(transformed[[position[x] for x in ordered[j-length+1:j+1]]])
            ys.append(frame.loc[idx,target])
            indices.append(idx)
    return np.asarray(xs,dtype=np.float32),np.asarray(ys,dtype=np.float32),indices
