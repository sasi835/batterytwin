"""Generate reproducible EDA and error-analysis figures from measured data/results."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.data.feature_engineering import FEATURES
from src.utils.config import ROOT

PLOTS = ROOT/'artifacts/plots'

def save(name: str, title: str, xlabel: str, ylabel: str):
    plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel)
    plt.grid(alpha=.18); plt.tight_layout()
    plt.savefig(PLOTS/f'{name}.png',dpi=160,bbox_inches='tight'); plt.close()

def eda(cycles, features, pca, transformed):
    plt.rcParams.update({'figure.figsize':(7,4),'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    for column,name,label in [('capacity_ah','capacity','Capacity (Ah)'),('soh','soh','SOH (% rated capacity)'),
                              ('temperature_mean','temperature','Temperature (C)'),('voltage_mean','voltage','Voltage (V)')]:
        for battery,group in cycles.groupby('battery_id'):
            y = group.capacity_ah/2*100 if column=='soh' else group[column]
            plt.plot(group.cycle,y,label=battery)
        plt.legend(); save(name,f'{label} across discharge cycles','Discharge cycle',label)
    for battery,group in cycles.groupby('battery_id'):
        plt.plot(group.cycle,100*(1-group.capacity_ah/group.capacity_ah.iloc[0]),label=battery)
    plt.legend(); save('degradation_comparison','Capacity fade relative to first observed discharge','Discharge cycle','Capacity fade (%)')
    plt.figure(figsize=(10,8)); plt.imshow(features[FEATURES].corr(),vmin=-1,vmax=1,cmap='RdBu_r'); plt.colorbar(label='Pearson correlation')
    plt.xticks(range(len(FEATURES)),FEATURES,rotation=90,fontsize=7); plt.yticks(range(len(FEATURES)),FEATURES,fontsize=7)
    save('correlation','Causal forecasting feature correlations','','')
    fig,axes=plt.subplots(2,3,figsize=(10,6))
    for ax,column in zip(axes.flat,FEATURES[:6]):
        ax.hist(features[column],bins=25,color='#168b83'); ax.set_title(column,fontsize=9)
    fig.tight_layout(); fig.savefig(PLOTS/'feature_distributions.png',dpi=160); plt.close(fig)
    projected=pca.transform(transformed)
    for battery in features.battery_id.unique():
        mask=features.battery_id==battery
        plt.scatter(projected[mask,0],projected[mask,1],s=12,label=battery,alpha=.7)
    plt.legend(); save('pca_projection','PCA projection (fitted on training batteries only)','PC1','PC2')
    plt.plot(np.arange(1,len(pca.explained_variance_ratio_)+1),np.cumsum(pca.explained_variance_ratio_),marker='o')
    plt.axhline(.95,color='orange',ls='--'); save('pca_variance','Cumulative PCA explained variance','Components','Explained variance')

def result_plots(predictions, history, optimization, anomaly_scores):
    for name,group in predictions[predictions.task=='soh'].groupby('model'):
        plt.scatter(group.actual,group.predicted,s=9,alpha=.5,label=name)
    plt.plot([50,105],[50,105],'k--'); plt.legend(fontsize=7); save('prediction_actual','Held-out B0006: prediction versus observation','Actual SOH (%)','Predicted SOH (%)')
    for name,group in predictions[predictions.task=='soh'].groupby('model'):
        plt.hist(group.predicted-group.actual,bins=24,alpha=.4,label=name)
    plt.legend(fontsize=7); save('residual_distribution','Held-out SOH prediction errors','Error (percentage points)','Count')
    group=predictions[(predictions.task=='soh')&(predictions.model=='Random Forest')]
    plt.scatter(group.cycle,group.predicted-group.actual,s=15,c=group.actual,cmap='viridis'); plt.colorbar(label='Actual SOH (%)')
    save('residual_cycle','Random Forest errors across battery life','Cycle','Residual (percentage points)')
    for name,group in predictions[predictions.task=='rul'].groupby('model'):
        plt.plot(group.cycle,group.predicted,label=name)
    if len(group):
        plt.plot(group.cycle,group.actual,'k--',label='Observed target')
    plt.legend(fontsize=7); save('rul_prediction','Held-out B0006 RUL forecast','Forecast cycle','Remaining cycles to first 70% crossing')
    for name,records in history.items():
        plt.plot([r['epoch'] for r in records],[r['validation_loss'] for r in records],label=f'{name} validation')
        plt.plot([r['epoch'] for r in records],[r['train_loss'] for r in records],ls='--',label=f'{name} train')
    plt.legend(fontsize=7); save('training_loss','Recurrent model optimization','Epoch','Standardized MSE')
    for name,group in optimization.groupby('study'):
        plt.plot(group.number,group.value,marker='o',label=name)
    plt.legend(); save('optimization_history','Optuna validation objectives','Trial','Validation MAE')
    for name,scores in anomaly_scores.items():
        plt.hist(scores,bins=25,alpha=.5,label=name)
    plt.legend(); save('anomaly_scores','Distribution novelty (no physical fault labels)','Isolation Forest anomaly score','Cycles')
