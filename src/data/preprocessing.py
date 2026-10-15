"""Battery-wise splitting; train-only imputers and scaling live in model pipelines."""
import numpy as np
import pandas as pd

def validate_cycles(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = ['battery_id','cycle','capacity_ah','voltage_mean','current_mean','temperature_mean','discharge_duration']
    missing = set(required)-set(frame)
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    duplicates = frame.duplicated(['battery_id','cycle'])
    if duplicates.any():
        raise ValueError('Duplicate battery/cycle identifiers; resolve source ambiguity.')
    invalid = ((frame.capacity_ah<=0)|(frame.capacity_ah>3)|(frame.voltage_mean<=0)|
               (frame.voltage_mean>5)|(frame.temperature_mean<-40)|(frame.temperature_mean>100)|
               (frame.discharge_duration<=0))
    if invalid.any():
        raise ValueError(f'{int(invalid.sum())} invalid sensor cycles')
    numeric = frame.select_dtypes('number')
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError('Infinite sensor measurements')
    report = {'rows':len(frame),'duplicates':int(duplicates.sum()),'invalid':int(invalid.sum()),
              'missing_values':frame.isna().sum().to_dict(),
              'outlier_policy':'IQR outliers are reported, retained because degradation is meaningful.',
              'iqr_outliers':{col:int(((numeric[col]<numeric[col].quantile(.25)-1.5*(numeric[col].quantile(.75)-numeric[col].quantile(.25)))|
                   (numeric[col]>numeric[col].quantile(.75)+1.5*(numeric[col].quantile(.75)-numeric[col].quantile(.25)))).sum()) for col in numeric}}
    return frame.sort_values(['battery_id','cycle']).reset_index(drop=True), report

def split_batteries(frame: pd.DataFrame, config: dict) -> dict:
    sets = {name:set(config['dataset'][f'{name}_batteries']) for name in ['train','validation','test']}
    if any(sets[a]&sets[b] for a,b in [('train','validation'),('train','test'),('validation','test')]):
        raise ValueError('Battery split overlap')
    return {name:frame[frame.battery_id.isin(ids)].copy() for name,ids in sets.items()}
