"""Re-evaluate saved models and produce error slices and an external-style baseline."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from src.utils.config import ROOT,load_config
from src.data.preprocessing import split_batteries
from src.data.feature_engineering import FEATURES
from src.evaluation.metrics import regression_metrics

def external_features(frame):
    return np.column_stack([frame.cycle,frame.lag_capacity_ah,frame.lag_capacity_ah-frame.capacity_change])

def evaluate():
    features=pd.read_csv(ROOT/'data/processed/features.csv')
    splits=split_batteries(features,load_config())
    predictions=pd.read_csv(ROOT/'artifacts/results/test_predictions.csv')
    actual_ids=splits['test'].query('cycle>=9').index
    model=joblib.load(ROOT/'models/soh_model.pkl')
    metrics=regression_metrics(splits['test'].loc[actual_ids,'soh'],model.predict(splits['test'].loc[actual_ids,FEATURES]))
    (ROOT/'artifacts/results/selected_model_metrics.json').write_text(json.dumps(metrics,indent=2))
    # Independently reimplement cycle + lag1 + lag2 linear baseline described in the cited open-source repository.
    started=time.perf_counter()
    baseline=LinearRegression().fit(external_features(splits['train']),splits['train'].soh)
    duration=time.perf_counter()-started
    started=time.perf_counter()
    external=baseline.predict(external_features(splits['test'].loc[actual_ids]))
    inference=time.perf_counter()-started
    comparison={'reference':'https://github.com/amirhossein-sadeghi2003/battery-health-forecasting-baselines',
                'external_reported':{'one_step_lag_linear_mae_fraction':.0078,'one_step_lag_linear_rmse_fraction':.0105,
                                     'protocol':'Chronological 70/30 within each of four batteries; SOH normalized by first capacity'},
                'local_adaptation':{'protocol':'BatteryTwin battery-held-out split; SOH normalized by 2 Ah rated capacity; cycles 9-168',
                                    'features':['cycle','previous_capacity','second_previous_capacity'],
                                    'metrics':regression_metrics(splits['test'].loc[actual_ids,'soh'],external),
                                    'training_seconds':duration,'inference_ms_per_row':inference/len(actual_ids)*1000,'n_test':len(actual_ids)},
                'interpretation':'Source-reported numbers have a different split and target reference; no direct superiority claim. Local adaptation shares our test targets.'}
    (ROOT/'artifacts/results/external_benchmark.json').write_text(json.dumps(comparison,indent=2))
    joblib.dump(baseline,ROOT/'models/external_lag_linear.pkl')
    predictions['temperature_max']=predictions.cycle.map(splits['test'].set_index('cycle').lag_temperature_max)
    slices=[]
    for name,group in predictions.groupby(['task','model']):
        for label,mask in [('all',np.ones(len(group),dtype=bool)),('early_life',group.cycle<=50),
                           ('near_EOL',group.cycle>=90),('high_temperature',group.temperature_max>=40)]:
            selected=group[mask]
            if len(selected)>1:
                slices.append({'task':name[0],'model':name[1],'slice':label,'battery_id':'B0006',
                               'n':len(selected),**regression_metrics(selected.actual,selected.predicted)})
    pd.DataFrame(slices).to_csv(ROOT/'artifacts/results/error_slices.csv',index=False)
    predictions.assign(absolute_error=(predictions.actual-predictions.predicted).abs()).sort_values('absolute_error',ascending=False).groupby('task').head(10).to_csv(ROOT/'artifacts/results/largest_errors.csv',index=False)
    pd.DataFrame(slices).query("slice=='all'").to_csv(ROOT/'artifacts/results/battery_wise_performance.csv',index=False)
    print('Selected model held-out metrics:',metrics)
    print('External-style lag linear adaptation:',comparison['local_adaptation']['metrics'])

if __name__=='__main__':
    evaluate()
