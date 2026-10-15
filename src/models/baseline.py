from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.decomposition import PCA

def baseline_models(seed: int) -> dict:
    return {'Linear Regression':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LinearRegression()),
            'Random Forest':make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(n_estimators=180,max_depth=8,random_state=seed,n_jobs=2)),
            'PCA + Linear':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),PCA(n_components=.95),LinearRegression())}
