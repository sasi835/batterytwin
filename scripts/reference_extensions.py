"""Execute independent, dataset-supported adaptations of the supplied EV repository."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json,time
import joblib
import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import confusion_matrix,ConfusionMatrixDisplay,roc_curve,roc_auc_score,precision_recall_curve,average_precision_score
from src.utils.config import ROOT,load_config
from src.utils.tracking import log_run
from src.data.preprocessing import split_batteries
from src.data.discharge import SOC_FEATURES,load_discharge_traces,trace_sequences
from src.models.gaussian_rul import fit_gaussian_rul,gaussian_prediction,GPR_FEATURES
from src.models.lstm import fit_sequence,predict_sequence
from src.evaluation.metrics import regression_metrics

REFERENCE='https://github.com/ahmedmhb/AI-Based-Pedictive-Diagnosis-and-Lifetime-Optimization-for-EVs-Battery'
REVISION='72fa7bff18b91b0b1c602c5cb3fadbbee51ef0a8'

def save(name,title,xlabel,ylabel):
    plt.title(title);plt.xlabel(xlabel);plt.ylabel(ylabel);plt.tight_layout()
    plt.savefig(ROOT/'artifacts/plots'/f'{name}.png',dpi=160,bbox_inches='tight');plt.close()

def run():
    cfg=load_config(); seed=cfg['seed']
    feature_frame=pd.read_csv(ROOT/'data/processed/features.csv')
    parts=split_batteries(feature_frame,cfg)
    test=parts['test'].query('cycle>=9').dropna(subset=['rul'])
    started=time.perf_counter();gpr=fit_gaussian_rul(parts['train'],seed);duration=time.perf_counter()-started
    joblib.dump(gpr,ROOT/'models/rul_gpr.pkl')
    started=time.perf_counter();mean,std=gaussian_prediction(gpr,test);inference=time.perf_counter()-started
    metrics=regression_metrics(test.rul,mean)
    interval_coverage=float(np.mean((test.rul>=np.maximum(0,mean-1.644854*std))&(test.rul<=mean+1.644854*std)))
    gpr_info={'model':'RUL Gaussian Process','task':'rul',**metrics,'training_seconds':duration,
              'inference_ms_per_row':inference/len(test)*1000,'n_test':len(test),'predictive_range_90_test_coverage':interval_coverage,
              'range_method':'Mean +/- 1.644854 posterior predictive standard deviations, lower bound floored at zero',
              'range_limitations':'Gaussian model-conditional range; empirical coverage from one correlated test battery. Not a calibrated fleet guarantee.',
              'training_cells_with_observed_eol':['B0005'],'reference':REFERENCE,'revision':REVISION}
    (ROOT/'artifacts/results/gaussian_rul.json').write_text(json.dumps(gpr_info,indent=2),encoding='utf8')
    log_run('RUL Gaussian Process',{'kernel':str(gpr[-1].kernel_)},metrics|{'training_seconds':duration},str(ROOT/'models/rul_gpr.pkl'),'reference_adaptations')
    comparison=pd.DataFrame({'cycle':test.cycle,'actual':test.rul,'predicted':mean,'std':std})
    comparison.to_csv(ROOT/'artifacts/results/gpr_predictions.csv',index=False)
    plt.plot(test.cycle,test.rul,'k--',label='Observed crossing target');plt.plot(test.cycle,mean,label='Gaussian Process')
    plt.fill_between(test.cycle,np.maximum(0,mean-1.644854*std),mean+1.644854*std,alpha=.2,label='Model-conditional 90% range')
    plt.legend(fontsize=8);save('gpr_rul_range','Held-out B0006: Gaussian-process RUL','Forecast cycle','Remaining cycles')
    benchmark=pd.read_csv(ROOT/'artifacts/results/benchmark.csv')
    benchmark=benchmark[benchmark.model!='RUL Gaussian Process']
    benchmark=pd.concat([benchmark,pd.DataFrame([{key:value for key,value in gpr_info.items() if key in benchmark.columns}])],ignore_index=True)
    benchmark.to_csv(ROOT/'artifacts/results/benchmark.csv',index=False)
    # Health-category diagnostics are labels derived from measured capacity, never physical faults.
    predictions=pd.read_csv(ROOT/'artifacts/results/test_predictions.csv').query("model=='Random Forest' and task=='soh'")
    def category(values):
        limits=cfg['health_thresholds']
        return np.select([values>=limits['healthy'],values>=limits['moderate'],values>=limits['degraded']],[0,1,2],default=3)
    categories=['Healthy','Moderate','Degraded','Below EOL']
    matrix=confusion_matrix(category(predictions.actual),category(predictions.predicted),labels=range(4))
    ConfusionMatrixDisplay(matrix,display_labels=categories).plot(cmap='Greens',colorbar=False,values_format='d')
    save('health_confusion_matrix','Derived health-category forecast (not fault labels)','Predicted health category','Measured health category')
    labels=(predictions.actual<=cfg['dataset']['eol_soh']).astype(int)
    score=-predictions.predicted
    fpr,tpr,_=roc_curve(labels,score);precision,recall,_=precision_recall_curve(labels,score)
    auc=float(roc_auc_score(labels,score));ap=float(average_precision_score(labels,score))
    plt.plot(fpr,tpr,label=f'AUC = {auc:.3f}');plt.plot([0,1],[0,1],'k--');plt.legend()
    save('eol_roc','Ranking future threshold crossing by SOH forecast','False positive rate','True positive rate')
    plt.plot(recall,precision,label=f'Average precision = {ap:.3f}');plt.legend()
    save('eol_precision_recall','Measured below-EOL targets; no physical fault diagnosis','Recall','Precision')
    (ROOT/'artifacts/results/health_classification.json').write_text(json.dumps({'categories':categories,'confusion_matrix':matrix.tolist(),
       'eol_auc':auc,'eol_average_precision':ap,'n_test':len(predictions),'positive_eol_samples':int(labels.sum()),
       'interpretation':'Derived measured-capacity categories; no fault labels or calibrated classification probabilities.'},indent=2),encoding='utf8')
    # SOC-reference adaptation uses measured discharge samples, not missing vehicle telemetry.
    traces=load_discharge_traces();traces.to_csv(ROOT/'data/processed/discharge_samples.csv',index=False)
    trace_parts=split_batteries(traces,cfg)
    scaler=make_pipeline(SimpleImputer(strategy='median'),StandardScaler()).fit(trace_parts['train'][SOC_FEATURES])
    joblib.dump(scaler,ROOT/'models/soc_scaler.pkl')
    sequence_sets={name:trace_sequences(frame,scaler.transform(frame[SOC_FEATURES]),6) for name,frame in trace_parts.items()}
    tx,ty,tids=sequence_sets['test'];sx,sy,_=sequence_sets['train'];vx,vy,_=sequence_sets['validation']
    forest=RandomForestRegressor(n_estimators=120,max_depth=12,n_jobs=2,random_state=seed)
    start=time.perf_counter();forest.fit(trace_parts['train'][SOC_FEATURES],trace_parts['train'].relative_charge_percent);rf_time=time.perf_counter()-start
    joblib.dump(forest,ROOT/'models/soc_forest.pkl')
    start=time.perf_counter();rf_pred=np.clip(forest.predict(traces.loc[tids,SOC_FEATURES]),0,100);rf_inference=time.perf_counter()-start
    params=cfg['training']|{'hidden_size':32,'layers':1,'dropout':.1,'batch_size':128,'epochs':60,'patience':10}
    start=time.perf_counter();gru,meta,history=fit_sequence(sx,sy,vx,vy,params,seed,'GRU');gru_time=time.perf_counter()-start
    meta['sequence_length']=6
    torch.save({'state_dict':gru.state_dict(),'metadata':meta},ROOT/'models/soc_gru.pt')
    start=time.perf_counter();gru_pred=np.clip(predict_sequence(gru,tx,meta),0,100);gru_inference=time.perf_counter()-start
    soc_rows=[]
    for name,predicted,duration,latency,path in [('SOC Random Forest',rf_pred,rf_time,rf_inference,'soc_forest.pkl'),('SOC GRU',gru_pred,gru_time,gru_inference,'soc_gru.pt')]:
        metrics=regression_metrics(ty,predicted)
        soc_rows.append({'model':name,'task':'derived_charge',**metrics,'n_test':len(ty),'training_seconds':duration,'inference_ms_per_row':latency/len(ty)*1000})
        log_run(name,params if name=='SOC GRU' else {'n_estimators':120,'max_depth':12},metrics,str(ROOT/'models'/path),'derived_charge_models')
    soc_info={'definition':'Relative discharge charge = clip(100*(1-integrated discharge Ah/measured cycle capacity),0,100)',
              'source':'NASA measured V/I/T/time; no measured SOC ground truth. Initial charge assumed 100%.',
              'evaluation_scope':'Models predict a derived coulomb-count proxy, not independently measured BMS SOC.',
              'features':SOC_FEATURES,'sequence_length':6,'metrics':soc_rows,'rows':len(traces),'reference':REFERENCE,'revision':REVISION}
    (ROOT/'models/soc_schema.json').write_text(json.dumps(soc_info,indent=2),encoding='utf8')
    (ROOT/'artifacts/results/soc_benchmark.json').write_text(json.dumps(soc_info,indent=2),encoding='utf8')
    pd.DataFrame(soc_rows).to_csv(ROOT/'artifacts/results/soc_benchmark.csv',index=False)
    # Precomputed replay values use saved models; online /predict/soc also evaluates supplied traces.
    traces['forest_prediction']=np.clip(forest.predict(traces[SOC_FEATURES]),0,100)
    traces['gru_prediction']=np.nan
    for name,frame in trace_parts.items():
        xs,_,ids=sequence_sets[name]
        traces.loc[ids,'gru_prediction']=np.clip(predict_sequence(gru,xs,meta),0,100)
    traces.to_csv(ROOT/'data/processed/discharge_replay.csv',index=False)
    sample=traces.query("battery_id=='B0006' and cycle==60")
    plt.plot(sample.time_seconds,sample.relative_charge_percent,'k--',label='Derived coulomb-count reference')
    plt.plot(sample.time_seconds,sample.forest_prediction,label='Random Forest');plt.plot(sample.time_seconds,sample.gru_prediction,label='GRU')
    plt.legend(fontsize=8);save('soc_discharge','B0006 cycle 60: derived relative charge tracking','Elapsed discharge time (s)','Relative charge (%)')
    plt.scatter(ty,gru_pred,s=5,alpha=.3);plt.plot([0,100],[0,100],'k--')
    save('soc_prediction_actual','Held-out SOC proxy: GRU versus derived reference','Derived reference (%)','Predicted relative charge (%)')
    plt.plot([x['epoch'] for x in history],[x['train_loss'] for x in history],label='Train')
    plt.plot([x['epoch'] for x in history],[x['validation_loss'] for x in history],label='Validation');plt.legend()
    save('soc_training_loss','Derived-charge GRU training','Epoch','Standardized MSE')
    print('Gaussian RUL:',gpr_info)
    print('Derived-charge benchmarks:',soc_rows)

if __name__=='__main__':
    run()
