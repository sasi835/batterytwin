"""Exercise saved-model inference without a web browser or training."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
from api.schemas import HistoryRequest,CycleMeasurement
from api.services import BatteryService
from src.utils.config import ROOT

data=pd.read_csv(ROOT/'data/processed/cycles.csv')
history=data[(data.battery_id=='B0006')&(data.cycle<=60)][list(CycleMeasurement.model_fields)].to_dict('records')
request=HistoryRequest(battery_id='B0006',history=history)
service=BatteryService(ROOT/'models')
soh=service.predict_soh(request);rul=service.predict_rul(request)
assert soh['forecast_cycle']==61 and 0<soh['predicted_soh']<110
assert rul['predicted_remaining_cycles']>=0
print(json.dumps({'forecast_cycle':61,'predicted_soh':soh['predicted_soh'],'remaining_cycles':rul['predicted_remaining_cycles']}))
