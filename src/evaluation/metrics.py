import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def regression_metrics(actual, predicted) -> dict:
    actual,predicted = np.asarray(actual),np.asarray(predicted)
    nonzero = np.abs(actual)>1e-8
    return {'mae':float(mean_absolute_error(actual,predicted)), 'rmse':float(np.sqrt(mean_squared_error(actual,predicted))),
            'r2':float(r2_score(actual,predicted)),
            'mape':float(np.mean(np.abs((actual[nonzero]-predicted[nonzero])/actual[nonzero]))*100) if nonzero.any() else None}
