"""Chronological LSTM training; export strictly held-out predictions."""
import argparse, csv
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1, 32, batch_first=True)
        self.head = nn.Linear(32, 1)
    def forward(self, x):
        y, _ = self.lstm(x)
        return self.head(y[:, -1]).squeeze(-1)

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--input', default='data/bars.csv')
    a.add_argument('--output', default='data/signals.csv')
    a.add_argument('--epochs', type=int, default=10)
    args = a.parse_args()
    torch.manual_seed(42)
    torch.set_num_threads(2)
    rows = list(csv.DictReader(open(args.input)))
    ts = np.array([int(r['timestamp']) for r in rows])
    close = np.array([float(r['close']) for r in rows])
    if len(close)<300 or not np.isfinite(close).all() or (close<=0).any():
        raise ValueError('Need at least 300 finite positive prices')
    if not (np.diff(ts)==60000).all():
        raise ValueError('Expected contiguous 1-minute bars; repair gaps first')
    ret = np.diff(np.log(close))
    split = int(len(close)*0.7)
    mean, std = ret[:split-1].mean(), max(ret[:split-1].std(),1e-8)
    scaled = (ret-mean)/std
    lookback = 32
    # At close[i], inputs end at return close[i-1] -> close[i].
    idx = np.arange(lookback, len(close)-1)
    x = torch.tensor(np.stack([scaled[i-lookback:i] for i in idx]), dtype=torch.float32).unsqueeze(-1)
    y = torch.tensor((ret[idx]>0).astype(np.float32))
    train = idx < split-1  # every training target is before the holdout boundary
    loader = DataLoader(TensorDataset(x[train], y[train]), batch_size=256, shuffle=True)
    model = Model()
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    for epoch in range(args.epochs):
        model.train()
        for bx, by in loader:
            opt.zero_grad(); loss = nn.functional.binary_cross_entropy_with_logits(model(bx),by)
            loss.backward(); opt.step()
        print(f'epoch={epoch+1} loss={loss.item():.6f}')
    model.eval()
    with torch.no_grad():
        prob = torch.cat([model(b).sigmoid() for b in x.split(1024)]).numpy()
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    with open(args.output,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['timestamp','close','signal'])
        for i,p in zip(idx,prob):
            if i>=split:
                w.writerow([ts[i],close[i],int(p>0.55)])
    torch.save({'state_dict':model.state_dict(),'mean':mean,'std':std,'lookback':lookback},'data/model.pt')

if __name__=='__main__': main()
