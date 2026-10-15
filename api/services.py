"""Load saved artifacts only. Training is never called by the API."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
from src.utils.config import ROOT
from src.data.feature_engineering import FEATURES,next_features,engineer
from src.models.lstm import SequenceRegressor,predict_sequence
from src.models.rul import trend_rul
from src.evaluation.explainability import local_explanation
from src.models.gaussian_rul import gaussian_prediction
from src.data.discharge import SOC_FEATURES,trace_features

class BatteryService:
    def __init__(self, directory: Path):
        self.meta=json.loads((directory/'feature_schema.json').read_text())
        self.soh=joblib.load(directory/'soh_model.pkl')
        self.rul=joblib.load(directory/'rul_model.pkl')
        self.anomaly=joblib.load(directory/'anomaly_model.pkl')
        self.scaler=joblib.load(directory/'scaler.pkl')
        self.recurrent={}
        torch.set_num_threads(2)
        for name,file in [('LSTM','lstm_model.pt'),('GRU','gru_model.pt'),('RUL LSTM','rul_lstm.pt')]:
            saved=torch.load(directory/file,map_location='cpu',weights_only=True)
            meta=saved['metadata']
            model=SequenceRegressor(meta['features'],meta['hidden_size'],meta['layers'],meta['dropout'],meta['kind'])
            model.load_state_dict(saved['state_dict']); model.eval()
            self.recurrent[name]=(model,meta)
        self.gpr=joblib.load(directory/'rul_gpr.pkl') if (directory/'rul_gpr.pkl').exists() else None
        self.soc=None
        if (directory/'soc_schema.json').exists():
            saved=torch.load(directory/'soc_gru.pt',map_location='cpu',weights_only=True)
            meta=saved['metadata']
            model=SequenceRegressor(meta['features'],meta['hidden_size'],meta['layers'],meta['dropout'],meta['kind'])
            model.load_state_dict(saved['state_dict']); model.eval()
            self.soc=(joblib.load(directory/'soc_forest.pkl'),joblib.load(directory/'soc_scaler.pkl'),model,meta,
                      json.loads((directory/'soc_schema.json').read_text()))

    def inputs(self, request):
        frame=pd.DataFrame([row.model_dump() for row in request.history])
        frame['battery_id']=request.battery_id
        values=next_features(frame,self.meta['config']['features']['rolling_window'])
        x=pd.DataFrame([values],columns=FEATURES)
        sequence=None
        length=self.meta['sequence_length']
        if len(frame)>=length:
            completed=engineer(frame,self.meta['config'])[FEATURES]
            sequence=self.scaler.transform(pd.concat([completed,x],ignore_index=True).tail(length)).astype(np.float32)[None]
        return frame,x,sequence

    def status(self, soh: float) -> str:
        limits=self.meta['config']['health_thresholds']
        return 'Healthy' if soh>=limits['healthy'] else 'Moderate degradation' if soh>=limits['moderate'] else 'Degraded' if soh>=limits['degraded'] else 'Below EOL'

    def predict_soh(self, request) -> dict:
        frame,x,sequence=self.inputs(request)
        predicted=float(self.soh.predict(x)[0])
        measured=float(frame.capacity_ah.iloc[-1]/self.meta['rated_capacity_ah']*100)
        seq_predictions={}
        if sequence is not None:
            seq_predictions={name:float(predict_sequence(model,sequence,meta)[0]) for name,(model,meta) in self.recurrent.items() if name!='RUL LSTM'}
        warnings=[]
        if len(frame)<self.meta['sequence_length']:
            warnings.append(f"Sequence models need at least {self.meta['sequence_length']} consecutive completed cycles.")
        if x.lag_current_mean.iloc[0]>0:
            warnings.append('NASA uses discharge summaries with negative measured current; this input may be outside the training domain.')
        if x.lag_temperature_mean.iloc[0]>50 or x.lag_temperature_mean.iloc[0]<15:
            warnings.append('Temperature may be outside the laboratory training domain.')
        if predicted<0 or predicted>110:
            warnings.append('Unbounded regressor output falls outside plausible laboratory SOH. Review input domain.')
        return {'forecast_cycle':int(x.cycle.iloc[0]),'predicted_soh':predicted,'current_measured_soh':measured,
                'status':self.status(measured),'model':self.meta['selected_model'],'sequence_predictions':seq_predictions,
                'explanation':local_explanation(self.soh,x),'uncertainty':'No calibrated confidence interval is available.',
                'input_warnings':warnings}

    def predict_rul(self, request) -> dict:
        frame,x,sequence=self.inputs(request)
        below_eol=bool((frame.capacity_ah/self.meta['rated_capacity_ah']*100<=self.meta['eol_soh']).any())
        tree=max(0,float(self.rul.predict(x)[0])); recurrent=None
        if sequence is not None:
            model,meta=self.recurrent['RUL LSTM']; recurrent=max(0,float(predict_sequence(model,sequence,meta)[0]))
        if below_eol:
            tree=0.; recurrent=0. if recurrent is not None else None
        gaussian=None; interval=None
        if self.gpr is not None:
            mean,std=gaussian_prediction(self.gpr,x)
            gaussian=0. if below_eol else float(mean[0])
            interval={'lower':0. if below_eol else max(0.,gaussian-1.644854*float(std[0])),
                      'upper':0. if below_eol else gaussian+1.644854*float(std[0]),'nominal_level':.9,
                      'scope':'Observed EOL override' if below_eol else 'Gaussian model-conditional range, not calibrated. Held-out coverage: 26.25% on one battery.'}
        return {'forecast_cycle':int(x.cycle.iloc[0]),'predicted_remaining_cycles':tree,'sequence_remaining_cycles':recurrent,
                'gaussian_remaining_cycles':gaussian,'gaussian_predictive_range':interval,
                **trend_rul(frame,self.meta['rated_capacity_ah'],self.meta['eol_soh']),
                'eol_soh':self.meta['eol_soh'],'model':'Random Forest; zero after observed threshold crossing',
                'limitations':'Exploratory estimate: only one training cell has observed EOL. Not pack life or safety certification.'}

    def predict_charge(self, request) -> dict:
        if self.soc is None:
            raise FileNotFoundError('Run scripts/reference_extensions.py to train charge models')
        forest,scaler,model,meta,schema=self.soc
        frame=trace_features(pd.DataFrame([x.model_dump() for x in request.trace]))
        values=frame[SOC_FEATURES]
        forest_values=np.clip(forest.predict(values),0,100)
        gru=None
        length=schema['sequence_length']
        if len(frame)>=length:
            sequence=scaler.transform(values.tail(length)).astype(np.float32)[None]
            gru=float(np.clip(predict_sequence(model,sequence,meta)[0],0,100))
        return {'relative_charge_percent':float(forest_values[-1]),'gru_relative_charge_percent':gru,
                'discharged_ah':float(frame.discharged_ah.iloc[-1]),
                'model':'Random Forest / GRU; saved inference',
                'scope':'Derived discharge-relative charge proxy, not measured or calibrated EV SOC. Assumes discharge starts full. No future capacity is accepted as input.',
                'trace':[{'time_seconds':float(t),'forest_charge_percent':float(p)} for t,p in zip(frame.time_seconds,forest_values)]}

    def detect_anomaly(self, request) -> dict:
        _,x,_=self.inputs(request)
        score=float(-self.anomaly.score_samples(x)[0]); thresholds=self.meta['anomaly_thresholds']
        status='Anomalous' if score>=thresholds['anomalous'] else 'Warning' if score>=thresholds['warning'] else 'Normal'
        return {'score':score,'status':status,'thresholds':thresholds,
                'interpretation':'Feature-distribution novelty; validation percentiles, no labeled physical faults or calibrated fault probability.'}
