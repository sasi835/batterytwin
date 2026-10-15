"""Configurable recurrent regressors with train-only scaling and early stopping."""
import copy
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

class SequenceRegressor(nn.Module):
    def __init__(self, features: int, hidden_size: int = 32, layers: int = 1, dropout: float = .15, kind: str = 'LSTM'):
        super().__init__()
        cell = nn.LSTM if kind=='LSTM' else nn.GRU
        self.rnn = cell(features,hidden_size,layers,batch_first=True,dropout=dropout if layers>1 else 0)
        self.head = nn.Sequential(nn.Dropout(dropout),nn.Linear(hidden_size,16),nn.ReLU(),nn.Linear(16,1))
    def forward(self, x):
        sequence,_ = self.rnn(x)
        return self.head(sequence[:,-1]).squeeze(-1)

def fit_sequence(train_x, train_y, val_x, val_y, params: dict, seed: int, kind: str = 'LSTM') -> tuple:
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    target_mean,target_scale = float(np.mean(train_y)),float(max(np.std(train_y),1))
    model = SequenceRegressor(train_x.shape[-1],params['hidden_size'],params['layers'],params['dropout'],kind)
    optimizer = torch.optim.Adam(model.parameters(),lr=params['learning_rate'])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer,patience=5,factor=.5)
    loss_fn = nn.MSELoss()
    dataset = TensorDataset(torch.tensor(train_x),torch.tensor((train_y-target_mean)/target_scale))
    loader = DataLoader(dataset,batch_size=params['batch_size'],shuffle=True,generator=torch.Generator().manual_seed(seed))
    vx,vy = torch.tensor(val_x),torch.tensor((val_y-target_mean)/target_scale)
    best,wait,state,history = float('inf'),0,None,[]
    for epoch in range(params['epochs']):
        model.train()
        total = 0.
        for x,y in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(x),y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),5)
            optimizer.step()
            total += loss.item()*len(x)
        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(vx),vy).item()
        scheduler.step(val_loss)
        history.append({'epoch':epoch+1,'train_loss':total/len(dataset),'validation_loss':val_loss})
        if val_loss<best-1e-6:
            best,state,wait = val_loss,copy.deepcopy(model.state_dict()),0
        else:
            wait += 1
        if wait>=params['patience']:
            break
    model.load_state_dict(state)
    model.eval()
    metadata = {'features':train_x.shape[-1],'hidden_size':params['hidden_size'],'layers':params['layers'],
                'dropout':params['dropout'],'kind':kind,'target_mean':target_mean,'target_scale':target_scale}
    return model,metadata,history

def predict_sequence(model, x, metadata: dict) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model(torch.tensor(x,dtype=torch.float32)).numpy()*metadata['target_scale']+metadata['target_mean']
