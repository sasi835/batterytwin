import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from api.main import app
from src.data.discharge import trace_features,trace_sequences
from src.models.planning import utilization_plan

def readings():
    return [{'time_seconds':t,'voltage':4-t*.0001,'current':-2,'temperature':25} for t in range(0,700,100)]

def test_current_integration_is_causal():
    frame=pd.DataFrame(readings())
    prefix=trace_features(frame.iloc[:4])
    frame.loc[4:,'current']=-9
    full=trace_features(frame)
    np.testing.assert_allclose(prefix.discharged_ah,full.discharged_ah.iloc[:4])
    assert prefix.discharged_ah.iloc[-1]==pytest.approx(2*300/3600)

def test_sequences_never_cross_discharge_or_battery():
    frames=[]
    for b,c in [('A',1),('A',2),('B',1)]:
        df=pd.DataFrame(readings());df['battery_id']=b;df['cycle']=c;df['relative_charge_percent']=100
        frames.append(df)
    frame=pd.concat(frames,ignore_index=True)
    scaled=np.repeat(np.repeat([1,2,3],7)[:,None],5,axis=1)
    xs,_,_=trace_sequences(frame,scaled,6)
    assert len(xs)==6
    assert all(np.unique(x).size==1 for x in xs)

def test_planning_changes_days_not_cycle_life():
    slow=utilization_plan(100,.5);fast=utilization_plan(100,2)
    assert slow['remaining_cycle_budget']==fast['remaining_cycle_budget']==100
    assert slow['estimated_days']==4*fast['estimated_days']
    assert utilization_plan(100,1,eol_observed=True)['estimated_days']==0

def test_charge_contract_and_saved_inference():
    with TestClient(app) as client:
        result=client.post('/api/predict/soc',json={'trace':readings()})
        assert result.status_code==200,result.text
        data=result.json()
        assert 0<=data['relative_charge_percent']<=100
        assert 0<=data['gru_relative_charge_percent']<=100
        assert data['discharged_ah']==pytest.approx(2*600/3600)
        assert 'proxy' in data['scope']
        bad=readings();bad[2]['time_seconds']=100
        assert client.post('/predict/soc',json={'trace':bad}).status_code==422
        assert client.post('/predict/soc',json={'trace':readings(),'capacity_ah':2}).status_code==422
        assert client.post('/predict/soc',json={'trace':readings()[1:]}).status_code==422

def test_reference_replay_and_eol_override():
    with TestClient(app) as client:
        replay=client.get('/api/batteries/B0006/discharge?cycle=60')
        assert replay.status_code==200,replay.text
        assert replay.json()['samples'][0]['gru_prediction'] is None
        assert client.get('/batteries/INVALID/discharge?cycle=60').status_code==404
        history=client.get('/batteries/B0006?through_cycle=60').json()['history']
        history[-2]['capacity_ah']=1.2;history[-1]['capacity_ah']=1.5
        body={'battery_id':'B0006','history':history,'cycles_per_day':1}
        plan=client.post('/api/plan/lifetime',json=body).json()
        assert plan['estimated_days']==0
        assert plan['rul']['gaussian_remaining_cycles']==0
        assert plan['rul']['gaussian_predictive_range']['upper']==0
        body['cycles_per_day']=0
        assert client.post('/plan/lifetime',json=body).status_code==422

def test_reference_metrics_and_audit_are_accessible():
    with TestClient(app) as client:
        response=client.get('/api/reference-results')
        assert response.status_code==200,response.text
        data=response.json()
        assert data['requirements']['plot_count']>=5
        assert data['gaussian']['n_test']==160
        assert data['charge']['metrics'][0]['n_test']==data['charge']['metrics'][1]['n_test']
