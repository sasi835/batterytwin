"""Durable JSONL/CSV fallback; optional MLflow integration."""
import csv
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from src.utils.config import ROOT

def versions() -> dict:
    result = {'python': platform.python_version(), 'platform': platform.platform()}
    for name in ['numpy','pandas','scipy','scikit-learn','torch','xgboost','shap','optuna','fastapi']:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = 'unavailable'
    return result

def log_run(name: str, params: dict, metrics: dict, artifact: str, experiment: str) -> None:
    record = {'timestamp': datetime.now(timezone.utc).isoformat(), 'model': name,
              'experiment': experiment, 'params': params, 'metrics': metrics, 'artifact': artifact,
              'dataset': json.loads((ROOT/'data/raw/manifest.json').read_text())}
    path = ROOT/'artifacts/logs/experiments.jsonl'
    with path.open('a', encoding='utf8') as stream:
        stream.write(json.dumps(record, default=str)+'\n')
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri((ROOT/'mlruns').as_uri())
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=name):
        mlflow.log_params(params)
        mlflow.log_metrics({k:v for k,v in metrics.items() if isinstance(v,(float,int))})
        mlflow.log_artifact(artifact)
