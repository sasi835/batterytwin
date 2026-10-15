"""Train real models, optimize on validation cells, evaluate one untouched test cell."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import time
import random
import joblib
import numpy as np
import pandas as pd
import torch
import optuna
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from src.utils.config import ROOT,load_config
from src.utils.tracking import log_run,versions
from src.data.feature_engineering import FEATURES,sequences
from src.data.preprocessing import split_batteries
from src.models.baseline import baseline_models
from src.models.boosting import boosting_model
from src.models.lstm import fit_sequence,predict_sequence
from src.models.anomaly import fit_anomaly
from src.evaluation.metrics import regression_metrics
from src.evaluation.explainability import tree_explanations
from src.evaluation.benchmark import eda,result_plots
from scripts.prepare_data import prepare

def train():
    cfg=load_config(); seed=cfg['seed']; random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    cycles,features=prepare(); splits=split_batteries(features,cfg)
    tr,va,te=[splits[x] for x in ['train','validation','test']]
    scaler=make_pipeline(SimpleImputer(strategy='median'),StandardScaler()).fit(tr[FEATURES])
    joblib.dump(scaler,ROOT/'models/scaler.pkl')
    scaled={k:scaler.transform(v[FEATURES]) for k,v in splits.items()}
    length=cfg['training']['sequence_length']
    sequence_sets={k:sequences(v,scaled[k],length) for k,v in splits.items()}
    common_ids=sequence_sets['test'][2]
    pca=PCA().fit(scaled['train']); joblib.dump(pca,ROOT/'models/pca.pkl')
    ratios=pca.explained_variance_ratio_
    pca_info={'explained_variance_ratio':ratios.tolist(),'cumulative':np.cumsum(ratios).tolist(),
              'components_90':int(np.searchsorted(np.cumsum(ratios),.9)+1),'components_95':int(np.searchsorted(np.cumsum(ratios),.95)+1)}
    (ROOT/'artifacts/results/pca.json').write_text(json.dumps(pca_info,indent=2))
    eda(cycles,features,pca,scaler.transform(features[FEATURES]))
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    def objective(trial):
        params={'n_estimators':trial.suggest_int('n_estimators',80,240,step=40),'max_depth':trial.suggest_int('max_depth',2,6),
                'learning_rate':trial.suggest_float('learning_rate',.02,.15,log=True),'subsample':trial.suggest_float('subsample',.65,1)}
        model=boosting_model(params,seed); model.fit(tr[FEATURES],tr.soh)
        return regression_metrics(va.soh,model.predict(va[FEATURES]))['mae']
    study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective,n_trials=cfg['optuna']['tree_trials'])
    models=baseline_models(seed); models['XGBoost']=boosting_model(study.best_params,seed)
    rows,predictions,histories=[],[],{}
    selection={}
    def record(name,task,actual,predicted,indices,duration,inference,params,path,validation_mae=None):
        metrics=regression_metrics(actual,predicted)
        row={'model':name,'task':task,**metrics,'training_seconds':duration,'inference_ms_per_row':inference/len(indices)*1000,
             'n_test':len(indices),'validation_mae':validation_mae}
        rows.append(row)
        for idx,a,p in zip(indices,actual,predicted):
            predictions.append({'model':name,'task':task,'battery_id':te.loc[idx,'battery_id'],'cycle':int(te.loc[idx,'cycle']),
                                'actual':float(a),'predicted':float(p),'temperature':float(te.loc[idx,'lag_temperature_mean'])})
        log_run(name,params,metrics|{'training_seconds':duration},str(path),'lstm_models' if name in ['LSTM','GRU','RUL LSTM'] else 'baseline_models')
    for name,model in models.items():
        start=time.perf_counter(); model.fit(tr[FEATURES],tr.soh); duration=time.perf_counter()-start
        validation=regression_metrics(va.soh,model.predict(va[FEATURES]))['mae']; selection[name]=validation
        start=time.perf_counter(); pred=model.predict(te.loc[common_ids,FEATURES]); inference=time.perf_counter()-start
        path=ROOT/'models'/f"{name.lower().replace(' ','_').replace('+','plus')}.pkl"; joblib.dump(model,path)
        record(name,'soh',te.loc[common_ids,'soh'],pred,common_ids,duration,inference,model.get_params(deep=False),path,validation)
    # Persistence is a rigorous next-cycle baseline, not a fabricated ML result.
    record('Persistence','soh',te.loc[common_ids,'soh'],te.loc[common_ids,'lag_capacity_ah']/cfg['dataset']['rated_capacity_ah']*100,
           common_ids,0,0,{},ROOT/'configs/config.yaml')
    sx,sy,_=sequence_sets['train']; vx,vy,_=sequence_sets['validation']; tx,ty,tids=sequence_sets['test']
    def sequence_objective(trial):
        params=cfg['training']|{'hidden_size':trial.suggest_categorical('hidden_size',[16,32,64]),
             'layers':trial.suggest_int('layers',1,2),'dropout':trial.suggest_float('dropout',.05,.3),
             'learning_rate':trial.suggest_float('learning_rate',.001,.008,log=True),
             'batch_size':trial.suggest_categorical('batch_size',[16,32,64])}
        model,meta,_=fit_sequence(sx,sy,vx,vy,params,seed)
        return regression_metrics(vy,predict_sequence(model,vx,meta))['mae']
    lstm_study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=seed))
    lstm_study.optimize(sequence_objective,n_trials=cfg['optuna']['lstm_trials'])
    for kind in ['LSTM','GRU']:
        params=cfg['training']|lstm_study.best_params
        start=time.perf_counter(); model,meta,history=fit_sequence(sx,sy,vx,vy,params,seed,kind); duration=time.perf_counter()-start
        meta['sequence_length']=length
        path=ROOT/'models'/f'{kind.lower()}_model.pt'; torch.save({'state_dict':model.state_dict(),'metadata':meta},path)
        start=time.perf_counter(); pred=predict_sequence(model,tx,meta); inference=time.perf_counter()-start
        validation=regression_metrics(vy,predict_sequence(model,vx,meta))['mae']
        record(kind,'soh',ty,pred,tids,duration,inference,params,path,validation); histories[kind]=history
    # Supervised RUL excludes the right-censored B0007, using observed crossings only.
    rul_train=tr.dropna(subset=['rul']); rul_val=va.dropna(subset=['rul']); rul_test=te.loc[common_ids].dropna(subset=['rul'])
    rul=make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(n_estimators=180,max_depth=8,random_state=seed,n_jobs=2))
    start=time.perf_counter(); rul.fit(rul_train[FEATURES],rul_train.rul); duration=time.perf_counter()-start
    path=ROOT/'models/rul_model.pkl'; joblib.dump(rul,path)
    start=time.perf_counter(); pred=rul.predict(rul_test[FEATURES]); inference=time.perf_counter()-start
    record('RUL Random Forest','rul',rul_test.rul,pred,rul_test.index,duration,inference,{},path)
    rx,ry,_=sequences(tr,scaled['train'],length,'rul'); rvx,rvy,_=sequences(va,scaled['validation'],length,'rul'); rtx,rty,rids=sequences(te,scaled['test'],length,'rul')
    start=time.perf_counter(); rmodel,rmeta,rhistory=fit_sequence(rx,ry,rvx,rvy,cfg['training'],seed); duration=time.perf_counter()-start
    rmeta['sequence_length']=length; path=ROOT/'models/rul_lstm.pt'; torch.save({'state_dict':rmodel.state_dict(),'metadata':rmeta},path)
    start=time.perf_counter(); pred=np.maximum(0,predict_sequence(rmodel,rtx,rmeta)); inference=time.perf_counter()-start
    record('RUL LSTM','rul',rty,pred,rids,duration,inference,cfg['training'],path); histories['RUL LSTM']=rhistory
    start=time.perf_counter(); anomaly,thresholds=fit_anomaly(tr[FEATURES],va[FEATURES],cfg)
    joblib.dump(anomaly,ROOT/'models/anomaly_model.pkl')
    log_run('Isolation Forest',cfg['anomaly'],{'training_seconds':time.perf_counter()-start},str(ROOT/'models/anomaly_model.pkl'),'anomaly_models')
    # Choose the deployed tabular model solely by validation MAE. Sequence forecasts remain available separately.
    eligible={k:v for k,v in selection.items() if k!='PCA + Linear'}
    best=min(eligible,key=eligible.get); joblib.dump(models[best],ROOT/'models/soh_model.pkl')
    importance=tree_explanations(models['Random Forest'],te.loc[common_ids,FEATURES],ROOT/'artifacts/plots')
    (ROOT/'artifacts/results/feature_importance.json').write_text(json.dumps(importance,indent=2))
    benchmark=pd.DataFrame(rows); predicted=pd.DataFrame(predictions)
    benchmark.to_csv(ROOT/'artifacts/results/benchmark.csv',index=False); predicted.to_csv(ROOT/'artifacts/results/test_predictions.csv',index=False)
    optimization=pd.concat([study.trials_dataframe().assign(study='XGBoost'),lstm_study.trials_dataframe().assign(study='LSTM')],ignore_index=True)
    optimization.to_csv(ROOT/'artifacts/optimization_history.csv',index=False)
    (ROOT/'artifacts/best_params.json').write_text(json.dumps({'xgboost':study.best_params,'lstm':lstm_study.best_params},indent=2))
    result_plots(predicted,histories,optimization,{k:-anomaly.score_samples(v[FEATURES]) for k,v in splits.items()})
    (ROOT/'artifacts/results/training_history.json').write_text(json.dumps(histories,indent=2))
    metadata={'selected_model':best,'selection_rule':'Lowest tabular validation MAE; no test-based selection',
              'features':FEATURES,'target':'Next discharge cycle SOH = measured capacity / 2.0 Ah * 100',
              'sequence_length':length,'anomaly_thresholds':thresholds,'eol_soh':cfg['dataset']['eol_soh'],
              'rated_capacity_ah':cfg['dataset']['rated_capacity_ah'],'config':cfg,'versions':versions(),
              'split':cfg['dataset'],'data_provenance':json.loads((ROOT/'data/raw/manifest.json').read_text()),
              'limitations':['Four laboratory cells; no EV pack validation','No physical fault labels',
                             'RUL learns from only one training cell with observed EOL','No calibrated confidence interval',
                             'Repeated observations within each cell are correlated']}
    (ROOT/'models/feature_schema.json').write_text(json.dumps(metadata,indent=2))
    (ROOT/'artifacts/logs/environment.json').write_text(json.dumps(versions(),indent=2))
    print(benchmark.to_string(index=False)); print('Deployed SOH model:',best)

if __name__=='__main__':
    train()
