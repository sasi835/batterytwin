import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

def fit_anomaly(train, validation, config: dict) -> tuple:
    """Unsupervised distribution novelty, calibrated on an unseen validation battery."""
    model = make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),IsolationForest(n_estimators=200,random_state=config['seed'],n_jobs=2))
    model.fit(train)
    scores = -model.score_samples(validation)
    thresholds = {name:float(np.percentile(scores,config['anomaly'][f'{name}_percentile'])) for name in ['warning','anomalous']}
    return model, thresholds
