import numpy as np
import pytest
from src.data.loader import load_cycles
from src.data.preprocessing import validate_cycles, split_batteries
from src.data.feature_engineering import engineer, next_features, FEATURES, sequences
from src.utils.config import load_config

def test_real_dataset_schema_and_units():
    frame,report = validate_cycles(load_cycles())
    assert len(frame)==636
    assert report['invalid']==0
    assert set(frame.battery_id)=={'B0005','B0006','B0007','B0018'}

def test_future_capacity_cannot_change_current_features():
    config=load_config()
    frame=load_cycles().query("battery_id=='B0005'").reset_index(drop=True)
    first=engineer(frame,config)
    frame.loc[20:,'capacity_ah'] *= .5
    second=engineer(frame,config)
    np.testing.assert_allclose(first.loc[:19,FEATURES],second.loc[:19,FEATURES])

def test_duplicate_rejected():
    frame=load_cycles()
    import pandas as pd
    with pytest.raises(ValueError,match='Duplicate'):
        validate_cycles(pd.concat([frame,frame.iloc[:1]]))

def test_disjoint_splits_and_sequences():
    config=load_config()
    frame=engineer(load_cycles(),config)
    splits=split_batteries(frame,config)
    assert not set(splits['train'].battery_id)&set(splits['test'].battery_id)
    x,y,ids=sequences(splits['train'],splits['train'][FEATURES].to_numpy(),8)
    assert x.shape[1:]==(8,len(FEATURES))
    assert len(y)==len(ids)
    assert not frame.loc[frame.battery_id=='B0007','rul'].notna().any()
