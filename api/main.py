from contextlib import asynccontextmanager
from pathlib import Path
import json
import os
import logging
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from api.schemas import HistoryRequest,SOHResponse,RULResponse,AnomalyResponse,AnalysisResponse,CycleMeasurement,SOCRequest,PlanningRequest
from src.models.planning import utilization_plan
from api.services import BatteryService
from src.utils.config import ROOT

@asynccontextmanager
async def lifespan(app):
    app.state.service=None
    try:
        directory=Path(os.environ.get('BATTERYTWIN_MODEL_DIR',str(ROOT/'models')))
        app.state.service=BatteryService(directory)
    except (FileNotFoundError,ValueError,RuntimeError,KeyError) as exc:
        logging.exception('Model loading failed; run the training workflow before serving')
        app.state.model_error=str(exc)
    yield

app=FastAPI(title='BatteryTwin Battery Intelligence',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.environ.get('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type'])

def service(request: Request) -> BatteryService:
    result=request.app.state.service
    if result is None:
        raise HTTPException(503,'Trained artifacts unavailable. Run python scripts/train.py; inspect server logs.')
    return result

@app.get('/health')
def health(request: Request):
    service(request)
    return {'status':'ready','dataset':'NASA PCoE','mode':'saved-model inference'}

@app.get('/model-info')
def model_info(request: Request):
    return service(request).meta

@app.get('/batteries')
def batteries(request: Request):
    service(request)
    frame=pd.read_csv(ROOT/'data/processed/cycles.csv')
    return [{'battery_id':battery,'cycles':len(group),'last_capacity_ah':float(group.capacity_ah.iloc[-1]),
             'source':'NASA PCoE measured discharge data'} for battery,group in frame.groupby('battery_id')]

@app.get('/batteries/{battery_id}')
def battery_history(battery_id: str, request: Request, through_cycle: int | None = Query(None,ge=1)):
    service(request)
    frame=pd.read_csv(ROOT/'data/processed/cycles.csv')
    frame=frame[frame.battery_id==battery_id]
    if frame.empty:
        raise HTTPException(404,'Unknown dataset battery')
    if through_cycle is not None:
        if through_cycle>frame.cycle.max():
            raise HTTPException(422,'Requested cycle exceeds measured history')
        frame=frame[frame.cycle<=through_cycle]
    columns=list(CycleMeasurement.model_fields)
    return {'battery_id':battery_id,'history':frame[columns].to_dict('records'),'source':'NASA PCoE measured discharge data'}

@app.post('/predict/soh',response_model=SOHResponse)
def predict_soh(body: HistoryRequest,request: Request):
    return service(request).predict_soh(body)

@app.post('/predict/rul',response_model=RULResponse)
def predict_rul(body: HistoryRequest,request: Request):
    return service(request).predict_rul(body)

@app.post('/detect/anomaly',response_model=AnomalyResponse)
def anomaly(body: HistoryRequest,request: Request):
    return service(request).detect_anomaly(body)

@app.post('/analysis',response_model=AnalysisResponse)
def analyze(body: HistoryRequest,request: Request):
    engine=service(request)
    return {'soh':engine.predict_soh(body),'rul':engine.predict_rul(body),'anomaly':engine.detect_anomaly(body)}

@app.get('/benchmark')
def benchmark(request: Request):
    service(request)
    frame=pd.read_csv(ROOT/'artifacts/results/benchmark.csv')
    return json.loads(frame.to_json(orient='records'))

@app.get('/analytics')
def analytics(request: Request):
    service(request)
    return {key:json.loads((ROOT/path).read_text()) for key,path in {
        'pca':'artifacts/results/pca.json','quality':'artifacts/results/data_quality.json',
        'importance':'artifacts/results/feature_importance.json',
        'external':'artifacts/results/external_benchmark.json'}.items()}

@app.get('/reference-results')
def reference_results(request: Request):
    service(request)
    return {key:json.loads((ROOT/f'artifacts/results/{file}.json').read_text()) for key,file in
            {'gaussian':'gaussian_rul','charge':'soc_benchmark','health':'health_classification','requirements':'requirements_audit'}.items()}

@app.get('/batteries/{battery_id}/discharge')
def discharge(battery_id: str,request: Request,cycle: int = Query(60,ge=1)):
    service(request)
    path=ROOT/'data/processed/discharge_replay.csv'
    if not path.exists():
        raise HTTPException(503,'Train reference extensions first')
    frame=pd.read_csv(path)
    frame=frame[(frame.battery_id==battery_id)&(frame.cycle==cycle)]
    if frame.empty:
        raise HTTPException(404,'Unknown measured discharge')
    return {'battery_id':battery_id,'cycle':cycle,'samples':json.loads(frame.to_json(orient='records')),
            'source':'Measured NASA sensors; derived charge reference and cached trained-model predictions',
            'scope':'Discharge-relative charge proxy assuming a full start. Offline reference uses measured cycle capacity. No measured SOC or EV calibration.'}

@app.post('/predict/soc')
def charge(body: SOCRequest,request: Request):
    try:
        return service(request).predict_charge(body)
    except FileNotFoundError as exc:
        raise HTTPException(503,str(exc)) from exc

@app.post('/plan/lifetime')
def lifetime_plan(body: PlanningRequest,request: Request):
    prediction=service(request).predict_rul(body)
    return {**utilization_plan(prediction['predicted_remaining_cycles'],body.cycles_per_day),
            'rul':prediction,'battery_id':body.battery_id}

# The production dashboard and Vite development proxy share /api URLs.
for route in list(app.routes):
    if isinstance(route,APIRoute):
        app.add_api_route('/api'+route.path,route.endpoint,methods=list(route.methods),response_model=route.response_model,include_in_schema=False)
app.mount('/api/plots',StaticFiles(directory=ROOT/'artifacts/plots'),name='api-plots')
app.mount('/plots',StaticFiles(directory=ROOT/'artifacts/plots'),name='plots')
if (ROOT/'frontend/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True),name='dashboard')
else:
    @app.get('/')
    def root():
        return {'project':'BatteryTwin','dashboard':'Run npm run dev in frontend, or build it to serve here','api_docs':'/docs'}
