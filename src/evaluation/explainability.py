"""SHAP for the fitted forest; coefficient contributions for the fitted linear model."""
import numpy as np
import shap
import matplotlib.pyplot as plt
from src.data.feature_engineering import FEATURES

def tree_explanations(model, frame, folder):
    estimator = model.steps[-1][1]
    transformed = model[:-1].transform(frame)
    explainer = shap.TreeExplainer(estimator)
    values = explainer(transformed)
    values.feature_names = FEATURES
    importance = np.abs(values.values).mean(axis=0)
    shap.summary_plot(values.values,transformed,feature_names=FEATURES,show=False)
    plt.tight_layout(); plt.savefig(folder/'shap_summary.png',dpi=160,bbox_inches='tight'); plt.close()
    top = int(np.argmax(importance))
    shap.dependence_plot(top,values.values,transformed,feature_names=FEATURES,show=False)
    plt.tight_layout(); plt.savefig(folder/'shap_dependence.png',dpi=160,bbox_inches='tight'); plt.close()
    return {'features':FEATURES,'importance':importance.tolist(),'explained_model':'Random Forest'}

def local_explanation(model, frame) -> dict:
    transformed = model[:-1].transform(frame)
    estimator = model.steps[-1][1]
    if hasattr(estimator,'feature_importances_'):
        explained = shap.TreeExplainer(estimator)(transformed)
        values = explained.values[0]
        base = float(np.asarray(explained.base_values).reshape(-1)[0])
    elif hasattr(estimator,'coef_') and len(estimator.coef_)==len(FEATURES):
        values = transformed[0]*estimator.coef_
        base = float(estimator.intercept_)
    else:
        return {'method':'Not available for selected model','contributions':[]}
    return {'method':'SHAP' if hasattr(estimator,'feature_importances_') else 'Scaled coefficient contributions',
            'base_value':base,'contributions':sorted([{'feature':f,'contribution':float(v)} for f,v in zip(FEATURES,values)],key=lambda x:abs(x['contribution']),reverse=True)}
