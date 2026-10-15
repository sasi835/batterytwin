import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def payload(client):
    data=client.get('/batteries/B0006?through_cycle=60').json()
    return {'battery_id':data['battery_id'],'history':data['history']}

def test_ready_models_loaded(client):
    assert client.get('/health').status_code==200
    assert client.get('/model-info').json()['selected_model']

@pytest.mark.parametrize('endpoint',['/predict/soh','/predict/rul','/detect/anomaly','/analysis'])
def test_inference_endpoints(client,payload,endpoint):
    response=client.post(endpoint,json=payload)
    assert response.status_code==200,response.text
    assert response.json()

def test_predictions_respond_to_capacity(client,payload):
    a=client.post('/predict/soh',json=payload).json()
    for row in payload['history'][-5:]:
        row['capacity_ah']-=.25
    b=client.post('/predict/soh',json=payload).json()
    assert abs(a['predicted_soh']-b['predicted_soh'])>1
    assert a['sequence_predictions']

def test_local_explanation_adds_to_prediction(client,payload):
    data=client.post('/predict/soh',json=payload).json()
    explained=data['explanation']['base_value']+sum(x['contribution'] for x in data['explanation']['contributions'])
    assert explained==pytest.approx(data['predicted_soh'],abs=.01)

@pytest.mark.parametrize('field,value',[('voltage_mean',-1),('capacity_ah',0),('temperature_mean',150),('cycle',0)])
def test_invalid_sensor_rejected(client,payload,field,value):
    payload['history'][-1][field]=value
    assert client.post('/predict/soh',json=payload).status_code==422

def test_disordered_history_rejected(client,payload):
    payload['history'].reverse()
    assert client.post('/analysis',json=payload).status_code==422

def test_missing_models_returns_503(monkeypatch,tmp_path):
    monkeypatch.setenv('BATTERYTWIN_MODEL_DIR',str(tmp_path))
    with TestClient(app) as client:
        assert client.get('/health').status_code==503

def test_short_history_has_no_sequence_prediction(client,payload):
    payload['history']=payload['history'][:1]
    result=client.post('/predict/soh',json=payload).json()
    assert not result['sequence_predictions']
    assert result['input_warnings']

def test_eol_returns_zero(client,payload):
    payload['history'][-1]['capacity_ah']=1.2
    assert client.post('/predict/rul',json=payload).json()['predicted_remaining_cycles']==0

def test_capacity_recovery_does_not_reset_observed_eol(client,payload):
    payload['history'][-2]['capacity_ah']=1.2
    payload['history'][-1]['capacity_ah']=1.5
    assert client.post('/predict/rul',json=payload).json()['predicted_remaining_cycles']==0

def test_unknown_battery(client):
    assert client.get('/batteries/unknown').status_code==404

def test_production_api_aliases(client,payload):
    assert client.get('/api/health').status_code==200
    assert client.get('/api/batteries').status_code==200
    assert client.post('/api/analysis',json=payload).status_code==200
    assert client.get('/api/plots/soh.png').status_code==200
