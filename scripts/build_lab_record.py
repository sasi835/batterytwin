"""Preserve the existing AML record; prepend supplied cover and append four project pages."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,Preformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from PIL import Image as PILImage
from src.utils.config import ROOT

SOURCE=Path(r'C:\Users\SriRamSasi\OneDrive\Desktop\AML LAB.pdf')
COVER=Path(r'C:\Users\SriRamSasi\OneDrive\Pictures\Screenshots\Screenshot 2026-10-14 163515.png')
TEMP=ROOT/'tmp/pdfs/lab-report'
OUTPUT=ROOT/'output/pdf/AML_Lab_Record_Final.pdf'
WIDTH,HEIGHT=A4
BODY=ParagraphStyle('Body',fontName='Times-Roman',fontSize=11,leading=15,spaceAfter=8)
HEAD=ParagraphStyle('Head',fontName='Times-Bold',fontSize=12,leading=16,spaceBefore=9,spaceAfter=7)
TITLE=ParagraphStyle('Title',fontName='Times-Bold',fontSize=14,leading=18,alignment=TA_CENTER,spaceAfter=10)
SMALL=ParagraphStyle('Small',parent=BODY,fontSize=9.5,leading=12.3,spaceAfter=6)
CODE=ParagraphStyle('Code',fontName='Courier',fontSize=8.2,leading=11,spaceAfter=8)

def p(text,style=BODY): return Paragraph(text,style)

def figure(filename,caption,max_height):
    path=ROOT/'artifacts/plots'/filename
    with PILImage.open(path) as im: w,h=im.size
    factor=min((WIDTH-118)/w,max_height/h)
    return [Image(str(path),width=w*factor,height=h*factor),p(caption,SMALL)]

def decorate(c,doc):
    c.saveState()
    c.setStrokeColor(colors.black);c.setLineWidth(.6)
    c.rect(24,24,WIDTH-48,HEIGHT-48)
    c.setFont('Times-Roman',10)
    c.drawCentredString(WIDTH/2,HEIGHT-39,str(79+doc.page))
    c.setFont('Times-Roman',8)
    c.drawString(55,38,'BatteryTwin - Advanced Machine Learning Lab - 19MAM56')
    c.restoreState()

def make_project():
    benchmark=pd.read_csv(ROOT/'artifacts/results/benchmark.csv')
    external=json.loads((ROOT/'artifacts/results/external_benchmark.json').read_text())
    verification=json.loads((ROOT/'artifacts/results/verification.json').read_text())
    story=[p('PROJECT REPORT',TITLE),p('BatteryTwin: AI-Based EV Battery Health Monitoring',TITLE),
        p('ABSTRACT:',HEAD),
        p('BatteryTwin is an AI-based battery-health monitoring project developed using 636 measured discharge cycles from four NASA laboratory cells. Causal capacity and sensor features support next-cycle SOH forecasts using regression, boosting and recurrent models. Battery-wise splitting, Optuna tuning, PCA, SHAP and error analysis support reproducible evaluation. On 160 held-out forecasts, persistence outperforms the learned SOH models. Exploratory RUL, novelty detection, derived charge tracking and utilization planning are presented through Streamlit. The local application passes 37 automated tests. Docker and cloud deployment packaging are prepared, while container execution and public hosting remain unverified. The small laboratory dataset does not establish real EV pack safety or physical fault diagnosis.'),
        p('AIM:',HEAD),
        p('To implement a battery-health monitoring application that uses measured discharge histories to forecast next-cycle State of Health (SOH), estimate remaining useful cycles, and identify unusual operating patterns. The project compares advanced machine-learning models with simple baselines and presents the results through a Streamlit interface.'),
        p('PROBLEM STATEMENT:',HEAD),
        p('Repeated use reduces a battery\'s available capacity. Looking at one voltage or temperature reading cannot explain how its condition has changed over time. BatteryTwin combines past capacity and sensor measurements to show degradation, forecast the next discharge cycle, and support exploratory maintenance planning. EV monitoring is the motivation; the implemented experiment uses laboratory single-cell data.'),
        p('DATASET AND TARGETS:',HEAD),
        p('The NASA battery-aging dataset supplies 636 measured discharge cycles from B0005, B0006, B0007 and B0018. Inputs include voltage, current, temperature, elapsed discharge time and measured capacity. SOH = (capacity / 2 Ah) x 100. End of life (EOL) is the first observed capacity at or below 1.4 Ah (70% rated capacity).'),
        p('ALGORITHM:',HEAD),
        *[p(f'{i}. {text}') for i,text in enumerate([
            'Extract and validate NASA discharge measurements.',
            'Create causal lag, rolling-capacity and sensor features from completed cycles.',
            'Train on B0005/B0007, validate on B0018 and test on B0006.',
            'Fit training-only preprocessing and PCA; construct battery-specific sequences.',
            'Train and tune models, compare common test targets, and explain errors with SHAP.',
            'Save artifacts and serve validated predictions through Streamlit.'
        ],1)],
        PageBreak(),p('IMPLEMENTATION',TITLE),
        p('1. Data processing and feature engineering',HEAD),
        p('The loader converts actual MATLAB fields into cycle summaries. Validation rejects ambiguous duplicate identifiers and impossible readings. IQR outliers are reported and retained. Lag features include previous capacity and previous voltage/current/temperature summaries; rolling statistics summarize recent completed cycles. Median imputation and scaling are fitted on training batteries only.'),
        p('2. Modeling, tuning and explanation',HEAD),
        p('Linear Regression, Random Forest, PCA + Linear Regression, XGBoost, LSTM and GRU predict SOH. The sequence networks use Adam, early stopping, learning-rate scheduling and gradient clipping. Optuna runs 8 XGBoost trials and 4 LSTM trials. Random Forest, LSTM and a Gaussian process estimate RUL. Isolation Forest detects feature novelty; SHAP explains the selected SOH forest.'),
        p('3. Main implementation modules',HEAD)]
    rows=[['Module / file','Purpose'],
          ['src/data/loader.py','Extract measured discharge records'],
          ['src/data/feature_engineering.py','Build causal features and sequences'],
          ['scripts/train.py','Train, tune, evaluate and save models'],
          ['scripts/evaluate.py','External baseline and error analysis'],
          ['api/schemas.py / api/services.py','Validate inputs and run saved models'],
          ['streamlit_app.py','Interactive monitoring and prediction UI'],
          ['Dockerfile','Package Streamlit and fitted artifacts']]
    table=Table([[p(x,SMALL) for x in row] for row in rows],colWidths=[222,WIDTH-110-222],hAlign='LEFT')
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
                              ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
    story.extend([table,p('4. Saved-model prediction flow',HEAD),
        p('The Streamlit application shares the existing validated service layer. It loads models through a cached resource and uses the supplied completed-cycle history for inference. Training remains an offline operation.'),
        Preformatted('request = HistoryRequest.model_validate(payload)\nservice = BatteryService(ROOT / "models")\nsoh = service.predict_soh(request)\nrul = service.predict_rul(request)\nanomaly = service.detect_anomaly(request)',CODE),
        PageBreak(),p('OUTPUT AND APPLICATION FEATURES',TITLE),
        p('Streamlit provides Dashboard, Predictions, Charge Tracking, Life Planning, Analytics, Model Performance, and About &amp; Requirements views. The user selects a battery and completed cycle, edits measurements or uploads a validated JSON history, then inspects saved-model predictions and charts.'),
        p('OUTPUT 1: MEASURED HEALTH HISTORY',HEAD),
        *figure('soh.png','Figure 1. Measured SOH across the four NASA cells; capacity is referenced to 2 Ah.',200),
        p('OUTPUT 2: PREDICTED VERSUS MEASURED HEALTH',HEAD),
        *figure('prediction_actual.png','Figure 2. SOH model predictions on the same held-out B0006 target cycles.',200),
        p('IMPLEMENTED FEATURES:',HEAD),
        p('Health monitoring displays measured SOH separately from next-cycle predictions. RUL compares the forest, recurrent and Gaussian estimates. Local SHAP contributions explain forecast behavior. Analytical plots include PCA, correlations, optimization history, loss curves and health-category diagnostics.',SMALL),
        p('Charge Tracking estimates a derived discharge-relative charge proxy from voltage, current, temperature and integrated current; NASA does not contain measured SOC. Life Planning converts a fixed remaining-cycle estimate into usage days, without claiming validated lifetime improvement.',SMALL),
        PageBreak(),p('EVALUATION, EXECUTION AND RESULT',TITLE),
        p('EVALUATION:',HEAD),
        p('All primary SOH models use the same 160 held-out B0006 forecasts (cycles 9-168). MAE and RMSE measure SOH errors in percentage points and RUL errors in cycles. Model selection uses validation performance. The following values come from the executed experiment files.',SMALL)])
    rows=[['Model','Task','MAE','RMSE','R-squared']]
    for _,r in benchmark.iterrows(): rows.append([r.model,r.task.upper(),f'{r.mae:.3f}',f'{r.rmse:.3f}',f'{r.r2:.3f}'])
    table=Table(rows,colWidths=[176,50,72,72,WIDTH-110-370],hAlign='LEFT')
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
        ('FONTNAME',(0,0),(-1,0),'Times-Bold'),('FONTNAME',(0,1),(-1,-1),'Times-Roman'),('FONTSIZE',(0,0),(-1,-1),9.5),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([table,Spacer(1,8),
        p(f'The independently adapted two-lag linear baseline achieves MAE {external["local_adaptation"]["metrics"]["mae"]:.3f}. Persistence outperforms the learned SOH models in the primary benchmark. This result is retained honestly; no deep-learning superiority is claimed. Error analysis examines early-life, near-EOL, high-temperature and large-residual cases.',SMALL),
        p('EXECUTION AND VERIFICATION:',HEAD),
        Preformatted('.\\start-streamlit.ps1\n# Open http://127.0.0.1:8501\n.\\deploy-docker.ps1\n# Requires a working Docker Linux engine',CODE),
        p(f'The complete automated suite has {verification["automated_tests"]["tests"]} passing tests, including nine Streamlit view/form tests. The local application is verified. The Dockerfile packages a non-root Streamlit runtime on port 7860. Local container execution remains blocked by Docker Desktop startup failure. User-approved Hugging Face publication was rejected with HTTP 403 because the current credential lacks Space-creation permission; no live cloud deployment is claimed.',SMALL),
        p('RESULT:',HEAD),
        p('BatteryTwin was implemented and verified locally for next-cycle health forecasting, exploratory remaining-life estimation, novelty detection and visual analysis. Four laboratory cells cannot establish real EV pack safety. Anomalies have no physical-fault labels; Gaussian nominal 90% ranges cover only 26.25% of test observations. Larger independent datasets and calibrated uncertainty are required before operational maintenance decisions.',SMALL),
        p('REFERENCES:',HEAD),
        p('NASA Li-ion Battery Aging Datasets: catalog.data.gov/dataset/li-ion-battery-aging-datasets.<br/>Reference adaptation: github.com/ahmedmhb/AI-Based-Pedictive-Diagnosis-and-Lifetime-Optimization-for-EVs-Battery.<br/>Complete experiment evidence and literature sources are included in the project README and docs/references.json.',SMALL)])
    output=TEMP/'project-four-pages.pdf'
    doc=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=55,rightMargin=55,topMargin=59,bottomMargin=55)
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    if len(PdfReader(output).pages)!=4:
        raise ValueError('Project section must occupy exactly four pages; revise content/layout.')
    return output

def build():
    TEMP.mkdir(parents=True,exist_ok=True);OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    cover=TEMP/'cover.pdf'
    c=canvas.Canvas(str(cover),pagesize=A4)
    c.setLineWidth(.7);c.rect(24,24,WIDTH-48,HEIGHT-48)
    c.setFont('Times-Bold',14)
    c.drawCentredString(WIDTH/2,HEIGHT-111,'COIMBATORE INSTITUTE OF TECHNOLOGY')
    affiliation=Paragraph('(Government-Aided Autonomous Institution Affiliated to Anna University, Chennai)',
                          ParagraphStyle('Affiliation',fontName='Times-Roman',fontSize=12,leading=15,alignment=TA_CENTER))
    _,h=affiliation.wrap(470,60);affiliation.drawOn(c,(WIDTH-470)/2,HEIGHT-158)
    c.setFont('Times-Roman',12);c.drawCentredString(WIDTH/2,HEIGHT-190,'COIMBATORE 14')
    c.setFont('Times-Bold',12)
    for offset,label in [(246,'ADVANCED MACHINE LEARNING LAB - 19MAM56'),(272,'SUBMITTED TO'),
                         (300,'Ms.Hemashree.P'),(326,'Dr.K.Swathine')]:
        c.drawCentredString(WIDTH/2,HEIGHT-offset,label)
    with PILImage.open(COVER) as im:
        im.crop((234,399,405,573)).save(TEMP/'cit-logo.png')
    c.drawImage(str(TEMP/'cit-logo.png'),WIDTH/2-79,HEIGHT-526,width=158,height=161)
    left=325;y=HEIGHT-610
    c.setFont('Times-Bold',12);c.drawString(left,y,'SUBMITTED BY');y-=26
    c.setFont('Times-Roman',11)
    for line in ['Name: SriRam Sasi M','Reg No: 2403717674421052','Department: M.Sc. AIML',
                 'Date: 14 October 2026','Subject: Advanced Machine Learning Lab','Subject Code: 19MAM56']:
        c.drawString(left,y,line);y-=18
    c.showPage();c.save()
    project=make_project()
    writer=PdfWriter()
    writer.append(cover)
    writer.add_blank_page(width=WIDTH,height=HEIGHT)
    writer.append(SOURCE)
    writer.append(project)
    writer.add_metadata({'/Title':'Advanced Machine Learning Lab Record with BatteryTwin Project','/Author':'SriRam Sasi M',
                         '/Subject':'19MAM56 - Lab record and four-page BatteryTwin project report'})
    with OUTPUT.open('wb') as f: writer.write(f)
    original=PdfReader(SOURCE);final=PdfReader(OUTPUT)
    assert len(final.pages)==len(original.pages)+6
    assert final.pages[1].get_contents() is None
    assert not final.pages[1].extract_text().strip()
    assert 'Date: 14 October 2026' in final.pages[0].extract_text()
    assert 'ABSTRACT:' in final.pages[-4].extract_text()
    for i,page in enumerate(original.pages):
        preserved=final.pages[i+2]
        assert preserved.extract_text()==page.extract_text(),f'Text changed on original page {i+1}'
        assert preserved.get_contents().get_data()==page.get_contents().get_data(),f'Content changed on original page {i+1}'
    record={'output':str(OUTPUT),'total_pages':len(final.pages),'front_pages':1,'blank_second_page':True,'original_lab_pages':len(original.pages),
            'appended_project_pages':4,'project_physical_pages':[82,83,84,85],
            'original_page_content_streams_and_text':'unchanged','format':'single column, ordinary lab-record format'}
    (TEMP/'verification.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print(json.dumps(record,indent=2))

if __name__=='__main__': build()
