"""BatteryTwin Streamlit UI: measured replay and validated saved-model inference."""
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from pydantic import ValidationError
from api.schemas import HistoryRequest, CycleMeasurement, SOCRequest
from api.services import BatteryService
from src.models.planning import utilization_plan
from src.utils.config import ROOT

st.set_page_config(page_title='BatteryTwin | Battery Intelligence',page_icon='🔋',layout='wide')

@st.cache_resource
def engine():
    return BatteryService(Path(os.environ.get('BATTERYTWIN_MODEL_DIR',str(ROOT/'models'))))

@st.cache_data
def csv(path):
    return pd.read_csv(ROOT/path)

@st.cache_data
def read_result(name):
    return json.loads((ROOT/'artifacts/results'/f'{name}.json').read_text(encoding='utf8'))

@st.cache_data(max_entries=128)
def analyze(payload_json):
    body=HistoryRequest.model_validate_json(payload_json)
    service=engine()
    return {'soh':service.predict_soh(body),'rul':service.predict_rul(body),'anomaly':service.detect_anomaly(body)}

def show_metrics(result):
    soh,rul,anomaly=result['soh'],result['rul'],result['anomaly']
    columns=st.columns(4)
    columns[0].metric('Measured health',f"{soh['current_measured_soh']:.1f}%",help=soh['status'])
    columns[1].metric('Next-cycle SOH',f"{soh['predicted_soh']:.1f}%",help=f"Cycle {soh['forecast_cycle']} · {soh['model']}")
    columns[2].metric('Remaining cycles',f"{rul['predicted_remaining_cycles']:.0f}",help='Exploratory estimate to 70% rated capacity')
    columns[3].metric('Pattern status',anomaly['status'],help=f"Novelty score: {anomaly['score']:.4f}")

def show_rul(rul):
    comparison={'Random Forest':rul['predicted_remaining_cycles'],'RUL LSTM':rul['sequence_remaining_cycles'],
                'Gaussian Process':rul['gaussian_remaining_cycles'],'Recent linear trend':rul['trend_cycles']}
    st.dataframe(pd.DataFrame([{'Method':k,'Remaining cycles':v} for k,v in comparison.items()]),hide_index=True,width='stretch')
    st.warning(rul['limitations'])
    interval=rul['gaussian_predictive_range']
    if interval:
        st.caption(f"Gaussian nominal 90% range: {interval['lower']:.1f}–{interval['upper']:.1f} cycles. {interval['scope']}")

def plot(name,caption):
    path=ROOT/'artifacts/plots'/f'{name}.png'
    if path.exists():
        st.image(str(path),caption=caption,width='stretch')

def dashboard(history,result):
    show_metrics(result)
    history=history.copy()
    history['SOH (%)']=history.capacity_ah/engine().meta['rated_capacity_ah']*100
    st.subheader('Every cycle tells a story')
    st.caption('Measured history; the next-cycle forecast is displayed separately above.')
    st.line_chart(history.set_index('cycle')[['SOH (%)']],x_label='Completed discharge cycle',y_label='Measured SOH (%)')
    left,right=st.columns(2)
    with left:
        st.subheader('Capacity degradation')
        st.line_chart(history.set_index('cycle')[['capacity_ah']],y_label='Capacity (Ah)')
    with right:
        st.subheader('Discharge temperature')
        st.line_chart(history.set_index('cycle')[['temperature_mean']],y_label='Temperature (°C)')
    st.subheader('What drives the forecast?')
    contributions=pd.DataFrame(result['soh']['explanation']['contributions'])
    st.bar_chart(contributions.head(8).set_index('feature')[['contribution']],horizontal=True)
    st.caption('SHAP contributions explain the selected model output, not physical causality.')
    st.info(result['anomaly']['interpretation'])
    st.download_button('Download analysis',json.dumps(result,indent=2),file_name='batterytwin-analysis.json',mime='application/json')

def prediction(payload,result):
    st.subheader('Analyze your completed-cycle measurements')
    st.caption('Edit the latest measurements or upload a full JSON history. Units: Ah, V, A, °C, seconds.')
    with st.form('measurement_form'):
        left,right=st.columns(2)
        capacity=left.number_input('Latest measured capacity (Ah)',min_value=.001,max_value=3.,value=float(payload['history'][-1]['capacity_ah']),step=.01)
        temperature=right.number_input('Latest mean temperature (°C)',min_value=-40.,max_value=100.,value=float(payload['history'][-1]['temperature_mean']),step=.5)
        submitted=st.form_submit_button('Run battery analysis')
    upload=st.file_uploader('Upload completed-cycle history JSON',type=['json'])
    if submitted or upload is not None:
        try:
            body=json.loads(upload.getvalue()) if upload is not None else json.loads(json.dumps(payload))
            if upload is None:
                body['history'][-1]['capacity_ah']=capacity
                body['history'][-1]['temperature_mean']=temperature
                body['history'][-1]['temperature_max']=max(temperature,body['history'][-1]['temperature_max'])
            validated=HistoryRequest.model_validate(body)
            result=analyze(validated.model_dump_json())
            st.success('Saved-model inference completed.')
        except (ValidationError,ValueError,TypeError,KeyError) as exc:
            st.error(f'Invalid history: {exc}')
            return
    show_metrics(result)
    st.subheader('Remaining useful cycles')
    show_rul(result['rul'])
    for warning in result['soh']['input_warnings']:
        st.warning(warning)
    with st.expander('Sequence SOH models and input format'):
        st.json(result['soh']['sequence_predictions'])
        st.code(json.dumps(payload,indent=2),language='json')
    st.download_button('Download prediction',json.dumps(result,indent=2),file_name='batterytwin-prediction.json',mime='application/json')

def charge_tracking(battery,cycle):
    st.warning('NASA has no measured SOC field. This view estimates a derived discharge-relative charge proxy assuming a full start; it is not calibrated EV SOC.')
    replay=csv('data/processed/discharge_replay.csv')
    replay=replay[(replay.battery_id==battery)&(replay.cycle==cycle)]
    st.subheader('Measured discharge curve')
    curve=replay[['time_seconds','relative_charge_percent','forest_prediction','gru_prediction']].set_index('time_seconds')
    st.line_chart(curve,y_label='Relative charge (%)',x_label='Elapsed discharge time (seconds)')
    st.caption('Reference integration uses original sensor resolution before downsampling; capacity is used only to construct the offline reference.')
    with st.form('charge_form'):
        last=st.slider('Replay samples to include',min_value=2,max_value=len(replay),value=max(2,len(replay)//2))
        upload=st.file_uploader('Optional custom discharge trace JSON',type=['json'],key='charge_upload')
        submitted=st.form_submit_button('Estimate relative charge')
    if submitted:
        try:
            body=json.loads(upload.getvalue()) if upload is not None else {'trace':replay.head(last)[['time_seconds','voltage','current','temperature']].to_dict('records')}
            request=SOCRequest.model_validate(body)
            result=engine().predict_charge(request)
            cols=st.columns(3)
            cols[0].metric('Forest charge proxy',f"{result['relative_charge_percent']:.1f}%")
            cols[1].metric('GRU charge proxy',f"{result['gru_relative_charge_percent']:.1f}%" if result['gru_relative_charge_percent'] is not None else 'Needs 6 samples')
            cols[2].metric('Integrated discharge',f"{result['discharged_ah']:.3f} Ah")
            st.caption(result['scope'])
        except (ValidationError,ValueError,TypeError,KeyError) as exc:
            st.error(f'Invalid discharge trace: {exc}')
    st.subheader('Held-out derived-charge benchmark')
    st.dataframe(pd.DataFrame(read_result('soc_benchmark')['metrics']),hide_index=True,width='stretch')

def planning(result):
    st.info('Planning converts a fixed cycle budget into days. No charging intervention, calendar aging or lifetime improvement is modeled.')
    rate=st.number_input('Completed discharge cycles per day',min_value=.01,max_value=24.,value=1.,step=.1)
    plan=utilization_plan(result['rul']['predicted_remaining_cycles'],rate)
    st.metric('Estimated cycle-budget duration',f"{plan['estimated_days']:.1f} days")
    st.bar_chart(pd.DataFrame(plan['scenarios']).set_index('label')[['days_to_cycle_budget']],y_label='Days')
    st.caption(plan['scope'])
    show_rul(result['rul'])

def analytics():
    pca=read_result('pca');quality=read_result('data_quality')
    a,b,c=st.columns(3)
    a.metric('Measured discharge cycles',quality['rows'])
    b.metric('PCA components: 90% variance',pca['components_90'])
    c.metric('PCA components: 95% variance',pca['components_95'])
    figures=[('pca_projection','PCA fitted on training batteries'),('correlation','Causal feature correlations'),
             ('shap_summary','Global SHAP explanations'),('training_loss','Training and validation loss'),
             ('optimization_history','Optuna trial history'),('anomaly_scores','Unsupervised novelty scores'),
             ('health_confusion_matrix','Capacity-derived health categories; not physical fault labels'),
             ('eol_precision_recall','Below-EOL ranking; not physical fault diagnosis')]
    for i in range(0,len(figures),2):
        columns=st.columns(2)
        for column,(name,title) in zip(columns,figures[i:i+2]):
            with column:
                plot(name,title)

def benchmarks():
    st.warning('Persistence outperforms learned SOH models in the primary test benchmark. Model selection uses validation performance, not test results.')
    st.subheader('Held-out battery B0006')
    st.caption('160 common next-cycle targets. SOH errors are percentage points; RUL errors are cycles.')
    st.dataframe(csv('artifacts/results/benchmark.csv'),hide_index=True,width='stretch')
    external=read_result('external_benchmark')
    st.metric('Adapted lag-linear SOH MAE',f"{external['local_adaptation']['metrics']['mae']:.3f} points")
    st.caption(external['interpretation'])
    st.subheader('Errors by life stage and temperature')
    st.dataframe(csv('artifacts/results/error_slices.csv'),hide_index=True,width='stretch')
    st.subheader('Largest prediction errors')
    st.dataframe(csv('artifacts/results/largest_errors.csv'),hide_index=True,width='stretch')
    plot('gpr_rul_range','Gaussian model-conditional ranges have poor held-out coverage; no calibration guarantee.')

def about():
    st.subheader('BatteryTwin · Advanced Machine Learning Lab CAT II')
    st.write('Forecast next-cycle battery health, estimate remaining useful cycles, and flag unusual operating patterns using measured NASA laboratory data.')
    st.write('Training: B0005 + B0007. Validation: B0018. Test: B0006. SOH = capacity / 2 Ah × 100. EOL = first observed capacity at or below 1.4 Ah.')
    st.warning('Four laboratory cells do not establish EV pack safety. RUL has one uncensored training cell. Charge targets are derived; anomalies have no physical fault labels.')
    audit=read_result('requirements_audit')
    st.subheader('Course requirement evidence')
    st.dataframe(pd.DataFrame([{'Requirement':x['requirement'],'Recorded status':x['status'],'Evidence':', '.join(x['evidence'])} for x in audit['items']]),hide_index=True,width='stretch')
    st.caption('This is the packaged evidence record. Hosting status is verified separately after deployment; marks are determined by the evaluator.')
    report=ROOT/'output/pdf/BatteryTwin_IEEE_Report.pdf'
    if report.exists():
        st.download_button('Download academic report',report.read_bytes(),file_name=report.name,mime='application/pdf')
    st.link_button('View supplied EV reference','https://github.com/ahmedmhb/AI-Based-Pedictive-Diagnosis-and-Lifetime-Optimization-for-EVs-Battery')

def main():
    st.title('🔋 BatteryTwin')
    st.caption('Battery health, measured cycle by cycle · NASA laboratory data · Saved-model inference')
    try:
        service=engine()
        cycles=csv('data/processed/cycles.csv')
    except (FileNotFoundError,ValueError,RuntimeError,KeyError) as exc:
        st.error(f'Trained artifacts unavailable: {exc}')
        st.stop()
    with st.sidebar:
        st.header('Battery intelligence')
        page=st.radio('Explore',['Dashboard','Predictions','Charge Tracking','Life Planning','Analytics','Model Performance','About & Requirements'])
        ids=sorted(cycles.battery_id.unique())
        battery=st.selectbox('Battery',ids,index=ids.index('B0006'))
        data=cycles[cycles.battery_id==battery]
        cycle=st.slider('Completed discharge cycle',min_value=8,max_value=int(data.cycle.max()),value=60)
        st.caption('Dataset replay · No live sensors')
    history=data[data.cycle<=cycle]
    payload={'battery_id':battery,'history':history[list(CycleMeasurement.model_fields)].to_dict('records')}
    if page in ['Dashboard','Predictions','Life Planning']:
        with st.spinner('Reading saved models…'):
            result=analyze(json.dumps(payload))
        if page=='Dashboard': dashboard(history,result)
        elif page=='Predictions': prediction(payload,result)
        else: planning(result)
    elif page=='Charge Tracking': charge_tracking(battery,cycle)
    elif page=='Analytics': analytics()
    elif page=='Model Performance': benchmarks()
    else: about()
    st.divider()
    st.caption('BatteryTwin · Research demonstration. Forecasts and anomalies do not certify EV battery safety.')

if __name__=='__main__':
    main()
