"""Create a seven-page IEEE-style report from executed experiments and verified references."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import html
import pandas as pd
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Image,Table,TableStyle,FrameBreak,PageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY,TA_CENTER
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
from src.utils.config import ROOT

WIDTH,HEIGHT=A4
MARGIN=40
COL=(WIDTH-2*MARGIN-18)/2
BODY=ParagraphStyle('Body',fontName='Times-Roman',fontSize=9,leading=11.5,alignment=TA_JUSTIFY,spaceAfter=7)
HEAD=ParagraphStyle('Head',fontName='Times-Bold',fontSize=10.2,leading=13,spaceBefore=8,spaceAfter=7)
TITLE=ParagraphStyle('Title',fontName='Times-Bold',fontSize=15,leading=18,alignment=TA_CENTER,spaceAfter=12)
CAPTION=ParagraphStyle('Caption',fontName='Times-Italic',fontSize=7.5,leading=9,alignment=TA_CENTER,spaceAfter=8)
SMALL=ParagraphStyle('Small',parent=BODY,fontSize=7.8,leading=10)

def para(text,style=BODY):
    return Paragraph(text,style)

def fig(name,caption,height=145):
    path=ROOT/'artifacts/plots'/f'{name}.png'
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w,h=im.size
    scale=min(COL/w,height/h)
    return [Image(str(path),width=w*scale,height=h*scale),para(caption,CAPTION)]

def diagram():
    drawing=Drawing(COL,200)
    labels=['NASA measured discharge cycles','Validate schema and battery IDs','Causal lag / rolling features','Battery-held-out training + Optuna','Saved ML / LSTM / GRU models','SHAP + Streamlit / FastAPI interface']
    for i,label in enumerate(labels):
        y=170-i*31
        drawing.add(Rect(8,y,COL-16,24,fillColor=colors.HexColor('#eff5f1'),strokeColor=colors.HexColor('#9bb4a4'),radius=3))
        drawing.add(String(COL/2,y+9,label,textAnchor='middle',fontName='Times-Roman',fontSize=8.2))
        if i<len(labels)-1:
            drawing.add(Line(COL/2,y,COL/2,y-7,strokeColor=colors.HexColor('#52735f')))
    return drawing

def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#c9d5ca'));canvas.line(MARGIN,HEIGHT-29,WIDTH-MARGIN,HEIGHT-29)
    canvas.setFont('Times-Roman',7.5);canvas.setFillColor(colors.HexColor('#6c7b70'))
    canvas.drawString(MARGIN,HEIGHT-23,'BatteryTwin | 19MAM56 Advanced Machine Learning Lab CAT II')
    canvas.drawRightString(WIDTH-MARGIN,HEIGHT-23,'Academic research implementation')
    canvas.drawString(MARGIN,25,'NASA laboratory cells - next-cycle forecasting - anomaly detection')
    canvas.drawRightString(WIDTH-MARGIN,25,str(doc.page))
    canvas.restoreState()

def report():
    output=ROOT/'output/pdf/BatteryTwin_IEEE_Report.pdf'
    bench=pd.read_csv(ROOT/'artifacts/results/benchmark.csv')
    meta=json.loads((ROOT/'models/feature_schema.json').read_text())
    pca=json.loads((ROOT/'artifacts/results/pca.json').read_text())
    quality=json.loads((ROOT/'artifacts/results/data_quality.json').read_text())
    external=json.loads((ROOT/'artifacts/results/external_benchmark.json').read_text())
    params=json.loads((ROOT/'artifacts/best_params.json').read_text())
    refs=json.loads((ROOT/'docs/references.json').read_text())
    doc=BaseDocTemplate(str(output),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=42,bottomMargin=42,
                        title='BatteryTwin: AI-Based EV Battery Health Monitoring',author='Academic project')
    frames=[Frame(MARGIN,42,COL,HEIGHT-85,id='left',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),
            Frame(MARGIN+COL+18,42,COL,HEIGHT-85,id='right',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]
    doc.addPageTemplates(PageTemplate(id='paper',frames=frames,onPage=footer))
    pages=[]
    # Explicit column breaks keep the academic layout predictable and inspectable.
    pages.append(([
      para('BatteryTwin: AI-Based EV Battery Health Monitoring and Anomaly Detection',TITLE),
      para('M.Sc. Artificial Intelligence &amp; Machine Learning<br/>Advanced Machine Learning Lab - CAT II<br/>October 14, 2026',CAPTION),
      para('Abstract',HEAD),
      para('BatteryTwin implements an end-to-end battery-health research pipeline using 636 measured discharge cycles from four NASA laboratory lithium-ion cells. Causal cycle features support next-cycle state-of-health (SOH) forecasting with linear regression, Random Forest, XGBoost, LSTM and GRU models. Battery-held-out validation controls hyperparameter optimization and model selection. PCA, SHAP explanations, experiment logs and residual analysis make results inspectable. On 160 held-out B0006 forecasts, persistence achieves 0.720 percentage-point MAE, beating the learned models in the main benchmark. Random Forest, selected by validation MAE, yields 1.682 test MAE. An independently implemented two-lag linear baseline improves to 0.684 MAE. Exploratory remaining-useful-life models and unsupervised anomaly scores accompany the forecasts. A Streamlit dashboard and validated FastAPI backend load saved artifacts. Docker Space configuration is provided; public hosting awaits a permitted credential. The small cell sample, unlabeled anomalies and one uncensored RUL training cell limit generalization. The work demonstrates reproducible comparison rather than a claim of deep-learning superiority.'),
      para('Index Terms - battery degradation, SOH, RUL, LSTM, XGBoost, explainability, MLOps.',SMALL),
      para('I. INTRODUCTION',HEAD),
      para('Battery capacity changes with repeated use, making health monitoring and maintenance planning useful research tasks. Laboratory measurements allow reproducible experiments, but EV packs introduce different thermal, electrical and operational conditions. BatteryTwin therefore treats the EV setting as motivation and evaluates only laboratory-cell forecasting.'),
      para('The objectives are to engineer leakage-controlled time-series inputs, compare advanced models against simple baselines, quantify forecasting errors, provide model explanations, and expose working saved-model inference through a web application. Anomaly detection is kept distinct from physical fault diagnosis.')
    ],[
      para('II. LITERATURE AND RESEARCH GAP',HEAD),
      para('NASA provides run-to-failure battery measurements with capacity and sensor histories [1]. Tree boosting supplies a strong tabular modeling paradigm [2], while LSTM offers recurrent memory for sequence regression [3]. SHAP assigns additive feature contributions to explain model outputs [4]. These methods motivate an engineering comparison; their algorithm papers do not establish performance on this project split.'),
      para('A public NASA forecasting baseline [5] distinguishes one-step monitoring from recursive forecasting: observed lag values can improve short-horizon scores without supporting accurate autonomous long-horizon trajectories. Its split and SOH reference differ from BatteryTwin. This project addresses cross-cell evaluation, adds measured sensor summaries and directly tests whether complex models improve on persistence.'),
      para('III. METHODOLOGY OVERVIEW',HEAD),diagram(),
      para('Fig. 1. Executed BatteryTwin pipeline; training is offline and inference loads saved artifacts.',CAPTION),
      para('A. Dataset and target formulation',HEAD),
      para('The cached dataset contains B0005, B0006, B0007 and B0018. Only measured discharge records are used. Actual MATLAB field inspection is saved with provenance checksums. No resistance or charge-duration feature is inferred when unavailable.'),
      para('<b>SOH(t) = 100 C(t) / 2.0 Ah.</b><br/>The forecast estimates SOH(t) using completed cycles at or before t-1. Prior measured capacity is available; target-cycle capacity is excluded. EOL is the first observed C(t) &lt;= 1.4 Ah, matching the dataset experiment [1].')
    ]))
    pages.append(([
      para('IV. DATA ENGINEERING',HEAD),
      para('The loader maps Voltage_measured, Current_measured, Temperature_measured, Time and Capacity into standardized cycle summaries. It validates required fields and extracts finite measurements. The validation pipeline rejects ambiguous duplicate battery/cycle IDs and invalid capacities, voltage summaries, temperature or duration. Missing-value counts and IQR outlier counts are logged. Outliers are retained because degradation and capacity recovery are scientifically meaningful.'),
      para('The executed data contains 636 discharge cycles, with no duplicate cycle IDs or invalid summary rows. B0005, B0006 and B0007 each contribute 168 cycles; B0018 contributes 132. There are 632 one-step forecasting rows after dropping the first target per cell.'),
      *fig('capacity','Fig. 2. Measured discharge capacity by cell.',150),
      *fig('soh','Fig. 3. SOH relative to 2 Ah rated capacity.',150),
      para('A. Leakage-controlled features',HEAD),
      para('Fifteen inputs include forecast cycle number, previous capacity, previous-five-cycle capacity mean and standard deviation, previous capacity difference, and lagged voltage/current/temperature/duration summaries. Rolling windows include only completed cycles. Missing-value imputation and standardization are fitted on training data only.')
    ],[
      para('B. Battery-aware evaluation',HEAD),
      para('Training uses B0005 and B0007; validation uses B0018; test uses B0006. Entire cells are disjoint. An eight-step sequence never crosses a cell boundary. All primary SOH models are scored on the same 160 target cycles (9-168), preventing unequal warm-up samples. Test results do not influence model selection or Optuna objectives.'),
      para('V. DIMENSIONALITY REDUCTION',HEAD),
      para(f'PCA is fitted on training-scaled features. {pca["components_90"]} components explain at least 90% of variance and {pca["components_95"]} explain at least 95%. The PCA + Linear model supplies a quantitative comparison against uncompressed linear regression. Projection and correlations are exploratory descriptions, not evidence of fault separability.'),
      *fig('pca_projection','Fig. 4. Cell-wise feature projection using training-fitted PCA.',165),
      *fig('pca_variance','Fig. 5. Cumulative explained variance.',150),
      para('C. Input validation and units',HEAD),
      para('The API accepts ordered consecutive completed-cycle summaries in Ah, V, A, degrees Celsius and seconds. Voltage minimum/mean/maximum and temperature mean/maximum must be consistent. Schemas forbid extra fields, non-finite values and invalid units/ranges. These checks support reliable inference; they do not establish operational EV safety.')
    ]))
    pages.append(([
      para('VI. MODELS AND PIPELINES',HEAD),
      para('Linear regression supplies an interpretable baseline. Random Forest uses 180 trees with depth 8. XGBoost is optimized on validation MAE [2]. A persistence forecast directly carries forward previous measured capacity. PCA + Linear tests whether feature compression changes generalization.'),
      para('A. Sequence models',HEAD),
      para('The recurrent regressor uses an LSTM or GRU followed by dropout and a 16-unit ReLU dense layer and scalar output [3]. Width, layer count, dropout and sequence length are configurable. Targets are standardized from training labels only. Adam optimization, gradient clipping, ReduceLROnPlateau and early stopping save the lowest-validation-loss state.'),
      para('The reproducible configuration allows 120 epochs, patience 18 and a default eight-step window. GRU uses the LSTM-selected settings as a secondary architecture comparison, not an independently optimized exhaustive search.'),
      *fig('training_loss','Fig. 6. Standardized train/validation losses; target scales differ for SOH and RUL.',185),
      para('B. Reproducibility and tracking',HEAD),
      para('Seed 42 controls NumPy, Python, Torch and randomized estimators. The dataset mirror is pinned to a revision and validated by SHA256. Durable JSONL records store model parameters, measured metrics, dataset version, artifact path and training time. Optional MLflow logging activates if installed; the supplied run uses the documented custom fallback.'),
      para(f'Executed environment: Python {meta["versions"]["python"]}; scikit-learn {meta["versions"]["scikit-learn"]}; Torch {meta["versions"]["torch"]}; XGBoost {meta["versions"]["xgboost"]}. Platform and remaining versions are saved in artifacts/logs/environment.json.',SMALL)
    ],[
      para('VII. HYPERPARAMETER OPTIMIZATION',HEAD),
      para('Optuna performs eight XGBoost trials over tree count (80-240), depth (2-6), learning rate (0.02-0.15) and subsampling (0.65-1.0). Four LSTM trials vary hidden size (16/32/64), layers (1-2), dropout (0.05-0.30), learning rate (0.001-0.008) and batch size (16/32/64). Both studies minimize validation MAE with seeded TPE sampling. The modest budget is a reproducible demonstration, not proof of optimal architecture.'),
      para('Selected XGBoost parameters: '+html.escape(json.dumps(params['xgboost'])),SMALL),
      para('Selected LSTM parameters: '+html.escape(json.dumps(params['lstm'])),SMALL),
      *fig('optimization_history','Fig. 7. Executed validation objectives for each Optuna study.',180),
      para('VIII. EXPLAINABILITY',HEAD),
      para('Global forest feature importance is measured through mean absolute SHAP contributions [4]. Summary and dependence figures are saved. For each dashboard forecast, local additive contributions refer to the deployed Random Forest. The API test checks that base value plus contributions reconstructs the prediction within tolerance. Explanations describe model behavior, not electrochemical causality.'),
      *fig('shap_summary','Fig. 8. Random Forest global SHAP summary on held-out inputs.',185)
    ]))
    table=[['Model','Task','MAE','RMSE','R2']]
    for _,r in bench.iterrows():
        table.append([r['model'],r['task'],f'{r.mae:.3f}',f'{r.rmse:.3f}',f'{r.r2:.3f}'])
    result_table=Table(table,colWidths=[93,26,42,42,42],repeatRows=1)
    result_table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Times-Bold'),('FONTNAME',(0,1),(-1,-1),'Times-Roman'),('FONTSIZE',(0,0),(-1,-1),7),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf1ec')),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#cad6cc')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    error=pd.read_csv(ROOT/'artifacts/results/error_slices.csv')
    slices=error[(error.model=='Random Forest')&(error.task=='soh')]
    slice_text='; '.join(f'{r["slice"]}: n={int(r.n)}, MAE={r.mae:.3f}' for _,r in slices.iterrows())
    pages.append(([
      para('IX. RESULTS AND COMPARATIVE ANALYSIS',HEAD),
      para('Table I reports actual held-out metrics. SOH errors are percentage points; RUL errors are cycles. MAPE excludes zero targets and is secondary for RUL. No anomaly accuracy, F1 or ROC curve is reported because labeled faults are absent.'),
      para('TABLE I. B0006 HELD-OUT BENCHMARK (160 TARGETS)',CAPTION),result_table,Spacer(1,10),
      para('Random Forest is the deployed learned tabular model because validation MAE is 0.795, lower than Linear Regression (1.226) and XGBoost (1.031). PCA + Linear validation MAE is 2.673. This selection precedes test inspection.'),
      para('<b>Persistence beats all learned models in the primary SOH benchmark.</b> The reported results do not establish deep-learning superiority. LSTM (3.097 MAE) and GRU (8.747 MAE) underperform simpler methods under the current small-data configuration.'),
      *fig('prediction_actual','Fig. 9. Shared held-out targets permit fair model comparison.',170)
    ],[
      para('A. External benchmark context',HEAD),
      para('The public repository [5] reports one-step lag-linear MAE 0.0078 and RMSE 0.0105 in SOH fraction units, using a chronological 70/30 split inside each cell and first-capacity normalization. These are source-reported contextual results, not our experiments; direct numerical superiority comparisons are invalid because the protocols differ.'),
      para(f'An independent cycle + two-capacity-lag linear adaptation is evaluated on BatteryTwin\'s own split and target definition. It achieves {external["local_adaptation"]["metrics"]["mae"]:.3f} SOH-point MAE and {external["local_adaptation"]["metrics"]["rmse"]:.3f} RMSE. This strengthens the conclusion that well-specified simple lag baselines are competitive. It is a baseline-method adaptation, not a reproduction of the source repository\'s reported protocol.'),
      para('X. ERROR ANALYSIS',HEAD),
      para('Errors are grouped by early life (cycles &lt;= 50), near-EOL region (cycles &gt;= 90), and elevated previous-cycle maximum temperature (&gt;= 40 C). Slice membership is descriptive and fixed; repeated cycles within one test cell are correlated. Battery-wise tables contain only the held-out cell and do not imply four-cell independent testing.'),
      para('Random Forest SOH slices: '+html.escape(slice_text)+'.',SMALL),
      *fig('residual_cycle','Fig. 10. Forest residuals by life stage.',170),
      para('Large residuals and recovery cycles reveal that smooth temporal correlation alone cannot resolve all local behavior. Forest predictions also struggle when test degradation leaves the training response range. The error CSV files retain exact observations for review. Further evaluation should hold out additional cells and operating conditions.')
    ]))
    pages.append(([
      para('XI. REMAINING USEFUL LIFE',HEAD),
      para('For an observed first threshold-crossing cycle T, RUL(t) = max(T-t, 0). A future crossing is used to construct an offline supervised label, never an input feature. B0007 has no observed crossing and is right-censored; it is excluded from supervised RUL fitting. B0005 is consequently the only uncensored RUL training cell. B0018 provides validation, and B0006 provides test targets.'),
      para('A Random Forest regressor and a separate LSTM predict remaining cycles. The forest yields 6.429-cycle MAE and the LSTM 9.828-cycle MAE. The API returns zero once observed input history has reached the EOL threshold. A recent-20-cycle linear slope provides a separate descriptive extrapolation, unavailable for insufficient history or a nonnegative slope. It is not ground truth.'),
      *fig('rul_prediction','Fig. 11. Exploratory remaining-cycle predictions versus observed crossing-based labels.',185),
      para('The one-cell RUL training population substantially restricts reliability. Predictions beyond the data domain are not validated; no arbitrary confidence percentage is emitted. Future work should evaluate censored survival modeling and independently calibrated prediction intervals before maintenance decisions.'),
      para('XII. ANOMALY DETECTION',HEAD),
      para('Isolation Forest is fitted on all training feature patterns and measures novelty relative to those laboratory conditions. It is not explicitly a healthy-only detector. Validation score percentiles define warning and anomalous thresholds, and current inputs are evaluated against those frozen values.')
    ],[
      *fig('anomaly_scores','Fig. 12. Unsupervised score distributions; no physical fault labels exist.',190),
      para(f'Frozen thresholds: warning = {meta["anomaly_thresholds"]["warning"]:.4f}; anomalous = {meta["anomaly_thresholds"]["anomalous"]:.4f}. Values correspond to the 90th and 97.5th validation percentiles. A warning can result from operating-condition or degradation distribution shifts; it is not calibrated event probability.'),
      para('XIII. IMPLEMENTATION',HEAD),
      para('The modular repository separates data loading, causal feature generation, model fitting, evaluation, services and UI. FastAPI serves strict Pydantic request/response schemas. Saved scikit-learn pipelines and Torch state dictionaries load once during application startup; missing artifacts produce a clear 503 readiness error. No server request retrains a model.'),
      para('The primary Streamlit interface provides seven views for measured replay, custom predictions, derived charge, utilization planning, analytics, benchmarks and requirements. It shares Pydantic validation and BatteryService with the retained FastAPI/React interface. Cached resources load saved models; custom forms execute actual inference. Nine Streamlit UI tests and 28 data/API tests pass.'),
      para('A. API contract',HEAD),
      para('GET /health, /model-info, /batteries and measured history; POST /predict/soh, /predict/rul, /detect/anomaly and /analysis; GET /benchmark and /analytics. /api aliases support the same-origin built dashboard. /docs exposes the full input schema. Inputs must use completed-cycle summaries with an ordered consecutive history. At least eight cycles enable recurrent inference.',SMALL),
      para('B. Verification',HEAD),
      para('Automated tests verify real-data schema, invalid and duplicate readings, causal future-data invariance, battery separation, saved artifact loading, all inference endpoints, changing-input sensitivity, SHAP additivity, short-history behavior, EOL behavior, missing-model 503 and production API aliases. Frontend build and browser verification accompany the tests. The final verification record contains executed counts and deployment limitations.')
    ]))
    pages.append(([
      para('XIV. CONTAINERIZATION AND DEPLOYMENT',HEAD),
      para('The primary Dockerfile serves Streamlit from Python 3.12 on port 7860 as UID 1000. Saved-artifact preflight runs before launch; /_stcore/health checks server readiness. Trained models, processed examples, plots and the report are bundled. Raw data, credentials and virtual environments are excluded. Compose maps host port 8501. Dockerfile.api retains the original API container.'),
      para('A runtime allowlist and Docker Space README metadata are staged for the user-approved sassy69/batterytwin target. The authenticated Hugging Face API rejected Space creation with HTTP 403: the fine-grained credential lacks creation permission. No live deployment is claimed. Local Docker Desktop also lacks a running engine. Cloud publication awaits a permitted credential; verification records retain both blockers.'),
      para('XV. CONCLUSION AND FUTURE SCOPE',HEAD),
      para('BatteryTwin demonstrates a working advanced-ML lifecycle with genuine data, modular training, optimization, explainability, error analysis and saved-model serving. Its most useful empirical result is that temporal baselines outperform the deep sequence models in this small next-cycle experiment. This finding is retained rather than hidden behind a dashboard.'),
      para('The selected forest is a validation-selected learned-model example, not evidence of test superiority. RUL is exploratory and anomaly scores are unlabeled distribution novelty. The system does not certify EV pack safety or predict physical fault types.'),
      para('Future scope includes additional cells and operating regimes, repeated battery-held-out evaluation, recursive multi-horizon forecasting, domain adaptation to pack telemetry, censored RUL learning, independent uncertainty calibration, authenticated device ingestion and labeled-fault experiments.'),
      para('Submission status',HEAD),
      para('Source, configuration, fitted artifacts, plots, notebooks, tests and this report are included. Author/roll-number details, a verified public GitHub URL and a live deployment URL must be added before final academic submission. The PDF is a seven-page IEEE-style academic report; venue-specific IEEE templates are not claimed.')
    ],[
      para('REFERENCES',HEAD),
      *[para(f'[{r["id"]}] {html.escape(r["ieee"])}<br/><link href="{r["url"]}" color="#356648">{html.escape(r["url"])}</link>',SMALL) for r in refs],
      para('REPRODUCIBILITY RECORD',HEAD),
      para('Data hashes: data/raw/manifest.json.<br/>Actual schema: artifacts/results/source_schema.json.<br/>Configuration: configs/config.yaml.<br/>Main results: artifacts/results/benchmark.csv.<br/>External adaptation: external_benchmark.json.<br/>Errors: error_slices.csv and largest_errors.csv.<br/>Parameters: artifacts/best_params.json.<br/>Experiments: artifacts/logs/experiments.jsonl.<br/>Environment: artifacts/logs/environment.json.<br/>Tests: tests/.<br/>Serving: api/main.py.<br/>Deployment: docs/DEPLOYMENT.md.',SMALL),
      para('Interpretation boundaries',HEAD),
      para('SOH measures capacity relative to rated capacity. Next-cycle prediction conditions on measured history. RUL predicts threshold-crossing-based remaining cycles. Anomaly detection flags feature novelty. None of these outputs is a labeled physical fault diagnosis. Health display categories are project settings. No calibrated uncertainty, live sensor feed or external public hosting is fabricated.',SMALL)
    ]))
    gpr=json.loads((ROOT/'artifacts/results/gaussian_rul.json').read_text())
    charge=json.loads((ROOT/'artifacts/results/soc_benchmark.json').read_text())
    pages.insert(-1,([
      para('REFERENCE-DRIVEN EXTENSIONS',HEAD),
      para('The requested EV repository [6] motivates independent GRU charge-tracking and Gaussian-process RUL adaptations. Its vehicle charging telemetry and generated RUL labels differ from NASA laboratory discharges. The inspected pipeline uses nominal 145 Ah vehicle cells and an 80% EOL convention; the Gaussian script uses 65%. BatteryTwin retains NASA 2 Ah rated capacity and 70% EOL. Source scores are not directly comparable.'),
      para('A. Gaussian-process RUL',HEAD),
      para('A train-only median-imputation/scaling pipeline fits a Gaussian process with a Matern 2.5 kernel, signal scale and white noise. Five causal features include target cycle, prior capacity, rolling capacity, prior change and temperature. Targets use observed crossings rather than synthetic Wiener labels. B0005 is the only uncensored training cell.'),
      para(f'On 160 held-out forecasts, Gaussian RUL MAE is {gpr["mae"]:.3f} cycles, RMSE {gpr["rmse"]:.3f} and R-squared {gpr["r2"]:.3f}; the existing RUL forest remains stronger. Mean +/- 1.644854 posterior predictive standard deviations defines a nominal 90% model-conditional range. Empirical test coverage is only {100*gpr["predictive_range_90_test_coverage"]:.2f}%. This severe undercoverage prevents interpreting the range as calibrated confidence. Some optimized kernel parameters reached bounds.'),
      *fig('gpr_rul_range','Fig. 13. Gaussian RUL and inadequately covering model-conditional ranges.',175),
      para('B. Utilization planning',HEAD),
      para('The Life Planning view maps remaining cycle budget R and a positive usage rate u into estimated days R/u. Scenarios vary u to 75% and 125% while holding R fixed. This arithmetic excludes calendar aging, partial-cycle equivalence and intervention effects. It does not establish charging optimization or longer battery life.')
    ],[
      para('C. Derived discharge charge tracking',HEAD),
      para('NASA contains measured voltage, current, temperature and elapsed time but no measured SOC field. Cumulative discharge Ah is the trapezoidal integral of max(-I, 0)/3600, using only current/past sensor readings. The offline target is clip(100(1-discharged Ah / measured cycle capacity), 0, 100), assuming a full start. Cycle capacity enters the label denominator only; it is not accepted by the prediction API.'),
      para('Original-resolution integration precedes downsampling. Random Forest and a six-sample GRU predict this discharge-relative proxy from V/I/T/time and integrated Ah. Scaling uses training batteries only; sequences stay inside one battery discharge. Correlated sensor samples do not establish independent BMS SOC accuracy.'),
      para('Held-out B0006, 2,748 common samples: '+ '; '.join(f'{r["model"]}: MAE {r["mae"]:.3f}, RMSE {r["rmse"]:.3f} percentage points' for r in charge['metrics'])+'.',SMALL),
      *fig('soc_discharge','Fig. 14. Derived charge reference and trained predictions on a measured discharge.',155),
      para('D. Health-category diagnostics and coverage',HEAD),
      *fig('health_confusion_matrix','Fig. 15. Capacity-derived categories, not physical fault labels.',145),
      para('Confusion matrices and ROC/PR plots use measured-capacity-derived categories and continuous next-cycle SOH scores. They do not evaluate physical faults or calibrated class probabilities. Twenty-five analytical plots, extension API tests and a requirement evidence inventory accompany the project. Docker execution, public cloud/repository links and student identity remain pending.',SMALL)
    ]))
    story=[]
    for i,(left,right) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.extend(left); story.append(FrameBreak()); story.extend(right)
    doc.build(story)
    from pypdf import PdfReader
    count=len(PdfReader(str(output)).pages)
    if count>10:
        raise ValueError(f'Report exceeds guideline page limit: {count}')
    print(f'Report created: {output} ({count} pages)')
    return output

if __name__=='__main__':
    report()
