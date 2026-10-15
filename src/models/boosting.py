from xgboost import XGBRegressor
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

def boosting_model(params: dict, seed: int):
    return make_pipeline(SimpleImputer(strategy='median'),XGBRegressor(**params,random_state=seed,n_jobs=2,objective='reg:squarederror'))
