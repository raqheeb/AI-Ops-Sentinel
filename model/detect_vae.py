import torch
import pandas as pd
import numpy as np
from vae_lstm import VAELSTM

df = pd.read_csv("../data/metrics_processed.csv")
feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5']
X = df[feature_cols].values

SEQ_LEN = 10
sequences, timestamps = [], []
for i in range(len(X) - SEQ_LEN):
    sequences.append(X[i:i+SEQ_LEN])
    timestamps.append(df['timestamp'].iloc[i+SEQ_LEN])

X_seq = torch.tensor(np.array(sequences, dtype=np.float32))

# Load model
model = VAELSTM(input_dim=5)
model.load_state_dict(torch.load("vae_lstm.pth"))
model.eval()

# Reconstruction error = anomaly score
with torch.no_grad():
    recon, _, _ = model(X_seq)
    errors = ((recon - X_seq) ** 2).mean(dim=(1, 2)).numpy()

# Threshold = mean + 16*std
threshold = errors.mean() + 16 * errors.std()
preds = (errors > threshold).astype(int)

results = pd.DataFrame({
    'timestamp': timestamps,
    'reconstruction_error': errors,
    'is_anomaly_vae': preds
})
results.to_csv("../data/vae_anomalies.csv", index=False)
print(f"VAE anomalies detected: {preds.sum()} / {len(preds)}")