"""Write lightweight notebooks that call the shared production pipeline."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def markdown(text):
    return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}

def code(text):
    return {'cell_type':'code','metadata':{},'source':text.splitlines(keepends=True),'outputs':[],'execution_count':None}

init="from pathlib import Path\nimport sys\nROOT = Path.cwd()\nif ROOT.name == 'notebooks':\n    ROOT = ROOT.parent\nsys.path.insert(0,str(ROOT))\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
notebooks={
    '01_eda.ipynb':[markdown('# BatteryTwin: dataset inspection and EDA\nReal NASA discharge cycles; run download_data.py and prepare_data.py first.'),code(init),
       code("cycles = pd.read_csv(ROOT/'data/processed/cycles.csv')\ncycles.groupby('battery_id').agg(cycles=('cycle','size'),first_capacity=('capacity_ah','first'),last_capacity=('capacity_ah','last'))"),
       code("for battery, group in cycles.groupby('battery_id'):\n    plt.plot(group.cycle,group.capacity_ah,label=battery)\nplt.xlabel('Discharge cycle'); plt.ylabel('Capacity (Ah)'); plt.legend(); plt.show()"),
       code("cycles.select_dtypes('number').describe().T"),markdown('See artifacts/plots for PCA, correlation, distributions, explainability and experiment figures.')],
    '02_preprocessing.ipynb':[markdown('# BatteryTwin: causal preprocessing\nFeatures for target cycle t use only completed cycles through t-1.'),code(init),
       code("from src.data.loader import load_cycles\nfrom src.data.preprocessing import validate_cycles,split_batteries\nfrom src.data.feature_engineering import engineer,FEATURES\nfrom src.utils.config import load_config\nconfig = load_config()\ncycles, report = validate_cycles(load_cycles())\nfeatures = engineer(cycles,config)\nreport"),
       code("parts = split_batteries(features,config)\n{k: {'rows':len(v),'batteries':list(v.battery_id.unique())} for k,v in parts.items()}"),
       code("features[['battery_id','cycle','lag_capacity_ah','soh','rul','eol_observed']].head(12)"),
       markdown('B0007 is right-censored for the 70% rated-capacity threshold. Do not fill unknown RUL labels or randomly mix its cycles into other battery partitions.')],
    '03_model_experiments.ipynb':[markdown('# BatteryTwin: actual experiment results\nExecute scripts/train.py and scripts/evaluate.py before opening this notebook.'),code(init),
       code("benchmark = pd.read_csv(ROOT/'artifacts/results/benchmark.csv')\nbenchmark"),
       code("import json\njson.loads((ROOT/'artifacts/results/external_benchmark.json').read_text())"),
       code("predictions = pd.read_csv(ROOT/'artifacts/results/test_predictions.csv')\nfor model, group in predictions[predictions.task=='soh'].groupby('model'):\n    plt.scatter(group.actual,group.predicted,s=8,alpha=.4,label=model)\nplt.plot([50,105],[50,105],'k--'); plt.legend(fontsize=7)\nplt.xlabel('Actual SOH (%)'); plt.ylabel('Predicted SOH (%)'); plt.show()"),
       code("pd.read_csv(ROOT/'artifacts/results/error_slices.csv')"),markdown('Persistence outperforms the advanced SOH models in the main benchmark. Do not claim sequence superiority, fault accuracy, calibrated uncertainty, or a public deployment without evidence.')]
}
for name,cells in notebooks.items():
    notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'nbformat':4,'nbformat_minor':5}
    (ROOT/'notebooks'/name).write_text(json.dumps(notebook,indent=2),encoding='utf8')
print('Created three exploration notebooks.')
