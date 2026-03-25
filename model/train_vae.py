import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
from vae_lstm import VAELSTM

# Load data
df = pd.read_csv("../data/metrics_processed.csv")
feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5']
X = df[feature_cols].values

# Create sequences of length 10
SEQ_LEN = 10
sequences = []
for i in range(len(X) - SEQ_LEN):
    sequences.append(X[i:i+SEQ_LEN])
X_seq = np.array(sequences, dtype=np.float32)

# Train only on normal windows (no anomaly)
anomalies = pd.read_csv("../data/anomalies.csv")
anomaly_times = set(anomalies[anomalies['is_anomaly'] == 1]['timestamp'].values)
normal_mask = ~df['timestamp'].isin(anomaly_times)
normal_idx = [i for i in range(len(X_seq)) if normal_mask.iloc[i]]
X_train = X_seq[normal_idx]
print(f"Training on {len(X_train)} normal sequences")

# DataLoader
tensor = torch.tensor(X_train)
loader = DataLoader(TensorDataset(tensor), batch_size=32, shuffle=True)

# Model
model = VAELSTM(input_dim=5)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# Loss
def vae_loss(recon, x, mu, logvar):
    recon_loss = nn.MSELoss()(recon, x)
    kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + 0.001 * kl_loss

# Train
EPOCHS = 30
for epoch in range(EPOCHS):
    total_loss = 0
    for (batch,) in loader:
        optimizer.zero_grad()
        recon, mu, logvar = model(batch)
        loss = vae_loss(recon, batch, mu, logvar)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    if (epoch+1) % 5 == 0:
        print(f"Epoch {epoch+1}/{EPOCHS} — Loss: {total_loss/len(loader):.4f}")

# Save model
torch.save(model.state_dict(), "vae_lstm.pth")
print("Model saved.")