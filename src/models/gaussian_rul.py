"""Independent Gaussian-process RUL adaptation inspired by the supplied EV reference."""
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

GPR_FEATURES = ['cycle','lag_capacity_ah','rolling_capacity_mean','capacity_change','lag_temperature_mean']

def fit_gaussian_rul(frame, seed: int):
    """Use observed threshold-crossing targets only; no generated Wiener ground truth."""
    kernel = ConstantKernel(1.,(1e-2,1e2))*Matern(length_scale=np.ones(len(GPR_FEATURES)),nu=2.5,
                   length_scale_bounds=(.1,100.))+WhiteKernel(noise_level=.03,noise_level_bounds=(1e-4,1.))
    model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),
        GaussianProcessRegressor(kernel=kernel,normalize_y=True,n_restarts_optimizer=1,random_state=seed))
    observed=frame.dropna(subset=['rul'])
    model.fit(observed[GPR_FEATURES],observed.rul)
    return model

def gaussian_prediction(model, frame) -> tuple[np.ndarray,np.ndarray]:
    """Posterior predictive mean/std; a model-conditional range, not calibrated coverage."""
    mean,std=model[-1].predict(model[:-1].transform(frame[GPR_FEATURES]),return_std=True)
    return np.maximum(0,mean),std
