"""Report tangible rubric evidence and unresolved publication requirements; no mark claims."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.utils.config import ROOT

def audit():
    groups=[
        ('Specialized dataset and preprocessing',['data/raw/manifest.json','artifacts/results/source_schema.json','artifacts/results/data_quality.json','src/data/feature_engineering.py']),
        ('Dimensionality reduction',['artifacts/results/pca.json','artifacts/plots/pca_projection.png']),
        ('At least five advanced plots',['artifacts/plots/shap_summary.png','artifacts/plots/pca_projection.png','artifacts/plots/training_loss.png','artifacts/plots/health_confusion_matrix.png','artifacts/plots/eol_precision_recall.png']),
        ('Advanced models, tuning and tracking',['models/xgboost.pkl','models/lstm_model.pt','models/gru_model.pt','artifacts/best_params.json','artifacts/logs/experiments.jsonl']),
        ('External comparison and error analysis',['artifacts/results/external_benchmark.json','artifacts/results/error_slices.csv','docs/REFERENCE_COMPARISON.md']),
        ('Validated local inference and UI',['api/main.py','api/schemas.py','frontend/dist/index.html','tests/test_api.py','tests/test_reference_extensions.py']),
        ('Streamlit interface and Docker Space packaging',['streamlit_app.py','tests/test_streamlit.py','requirements-streamlit.txt','scripts/prepare_space.py','scripts/publish_space.py']),
        ('Reference GRU charge and Gaussian RUL adaptations',['models/soc_gru.pt','models/rul_gpr.pkl','artifacts/results/soc_benchmark.json','artifacts/results/gaussian_rul.json']),
        ('IEEE-style report, max 10 pages',['output/pdf/BatteryTwin_IEEE_Report.pdf']),
        ('Configuration and packaged source',['requirements.txt','configs/config.yaml','Dockerfile','scripts/package_project.py']),
    ]
    items=[]
    for label,paths in groups:
        missing=[p for p in paths if not (ROOT/p).exists()]
        items.append({'requirement':label,'status':'Evidence present' if not missing else 'Missing evidence',
                      'evidence':paths,'missing':missing})
    items.extend([
        {'requirement':'Docker execution','status':'Pending: engine unavailable','evidence':['Dockerfile','docker-compose.yml'],'missing':['Successful image build and container health check']},
        {'requirement':'Public GitHub and cloud hosting','status':'Pending: Hugging Face write permission; GitHub target not supplied','evidence':['docs/DEPLOYMENT.md','artifacts/results/huggingface_deployment.json'],'missing':['Verified public repository URL','Verified live application URL']},
        {'requirement':'Author and roll number','status':'Pending: student details required','evidence':['output/pdf/BatteryTwin_IEEE_Report.pdf'],'missing':['Author identity for final submission']},
    ])
    result={'scope':'Evidence inventory, not an award of marks. Public hosting and container execution are not claimed.',
            'plot_count':len(list((ROOT/'artifacts/plots').glob('*.png'))),'items':items}
    from pypdf import PdfReader
    if (ROOT/'output/pdf/BatteryTwin_IEEE_Report.pdf').exists():
        reader=PdfReader(ROOT/'output/pdf/BatteryTwin_IEEE_Report.pdf')
        result['report_pages']=len(reader.pages)
        result['report_within_page_limit']=len(reader.pages)<=10
        text=reader.pages[0].extract_text()
        abstract=text.split('Abstract',1)[1].split('Index Terms',1)[0]
        result['abstract_words']=len(abstract.split())
        result['abstract_within_word_limit']=result['abstract_words']<=200
    (ROOT/'artifacts/results/requirements_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(f'Requirements audited: {len(items)} items, {result["plot_count"]} plots; publication pending.')
    return result

if __name__=='__main__':
    audit()
