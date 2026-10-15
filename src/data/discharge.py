"""Measured NASA discharge traces and a derived coulomb-count charge reference."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid
from scipy.io import loadmat
from src.utils.config import ROOT

SOC_FEATURES=['voltage','current','temperature','time_seconds','discharged_ah']

def trace_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Integrate only past/current discharge current, with no future sensor samples."""
    required=['time_seconds','voltage','current','temperature']
    if frame.empty or not set(required).issubset(frame):
        raise ValueError('Discharge traces require time, voltage, current and temperature.')
    result=frame[required].copy()
    values=result.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (np.diff(result.time_seconds)<=0).any():
        raise ValueError('Trace readings must be finite and time strictly increasing.')
    result['discharged_ah']=cumulative_trapezoid(np.maximum(-result.current.to_numpy(),0),result.time_seconds.to_numpy(),initial=0)/3600
    return result

def load_discharge_traces(step: int = 15) -> pd.DataFrame:
    """Downsample measured sensor curves after integrating at original resolution.

    Derived relative charge = clip(100*(1-discharged_Ah/measured_cycle_capacity),0,100).
    The capacity is used only for an offline label; NASA contains no measured SOC field.
    """
    rows=[]
    for path in sorted((ROOT/'data/raw').glob('B*.mat')):
        count=0
        for cycle in loadmat(path,simplify_cells=True)[path.stem]['cycle']:
            if cycle['type']!='discharge':
                continue
            count+=1; data=cycle['data']
            frame=pd.DataFrame({name:np.asarray(data[source],dtype=float).reshape(-1) for name,source in
                [('time_seconds','Time'),('voltage','Voltage_measured'),('current','Current_measured'),('temperature','Temperature_measured')]})
            frame=frame.dropna().drop_duplicates('time_seconds').sort_values('time_seconds')
            frame['time_seconds']-=frame.time_seconds.iloc[0]
            frame=trace_features(frame)
            frame['relative_charge_percent']=np.clip(100*(1-frame.discharged_ah/float(data['Capacity'])),0,100)
            frame['battery_id']=path.stem; frame['cycle']=count
            selected=sorted(set(range(0,len(frame),step))|{len(frame)-1})
            rows.append(frame.iloc[selected])
    return pd.concat(rows,ignore_index=True)

def trace_sequences(frame: pd.DataFrame, scaled: np.ndarray, length: int = 6) -> tuple:
    """Each sequence stays inside one measured battery discharge cycle."""
    positions={index:i for i,index in enumerate(frame.index)}
    sequences,targets,ids=[],[],[]
    for _,group in frame.groupby(['battery_id','cycle'],sort=False):
        indices=group.index.to_list()
        for j in range(length-1,len(indices)):
            window=indices[j-length+1:j+1]
            sequences.append(scaled[[positions[x] for x in window]])
            targets.append(frame.loc[indices[j],'relative_charge_percent'])
            ids.append(indices[j])
    return np.asarray(sequences,dtype=np.float32),np.asarray(targets,dtype=np.float32),ids
