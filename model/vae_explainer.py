"""
VAE-LSTM SHAP Explainer — AIOps Sentinel
------------------------------------------
Uses perturbation-based feature attribution on the
trained VAE-LSTM. Measures how much each feature
contributes to reconstruction error by zeroing out
one feature at a time and measuring error change.

Output: data/vae_explanations.json
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import json

SEQ_LEN    = 10
INPUT_DIM  = 6
HIDDEN_DIM = 32
LATENT_DIM = 8

class VAE_LSTM(nn.Module):
    def __init__(self):
        super(VAE_LSTM, self).__init__()
        self.lstm_enc  = nn.LSTM(INPUT_DIM, HIDDEN_DIM, batch_first=True, num_layers=1)
        self.fc_mu     = nn.Linear(HIDDEN_DIM, LATENT_DIM)
        self.fc_logvar = nn.Linear(HIDDEN_DIM, LATENT_DIM)
        self.fc_decode = nn.Linear(LATENT_DIM, HIDDEN_DIM)
        self.lstm_dec  = nn.LSTM(HIDDEN_DIM, INPUT_DIM, batch_first=True, num_layers=1)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        _, (h_n, _) = self.lstm_enc(x)
        h      = h_n.squeeze(0)
        mu     = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        z      = self.reparameterize(mu, logvar)
        z_exp  = self.fc_decode(z).unsqueeze(1).repeat(1, SEQ_LEN, 1)
        recon, _ = self.lstm_dec(z_exp)
        return recon, mu, logvar

def reconstruction_error(model, x_tensor):
    with torch.no_grad():
        recon, _, _ = model(x_tensor)
        error = ((recon - x_tensor) ** 2).mean().item()
    return error

def perturbation_attribution(model, sequence, baseline_error):
    """
    Zero out each feature one at a time.
    Larger error increase = more responsible for anomaly.
    """
    attributions = []
    for feat_idx in range(INPUT_DIM):
        perturbed = sequence.clone()
        perturbed[:, :, feat_idx] = 0.0  # zero out feature
        perturbed_error = reconstruction_error(model, perturbed)
        attribution = abs(perturbed_error - baseline_error)
        attributions.append(attribution)
    return np.array(attributions)

# ── Load model ────────────────────────────────────────────
print("Loading VAE-LSTM model...")
model = VAE_LSTM()
model.load_state_dict(torch.load("model/vae_model.pth", map_location='cpu'))
model.eval()

# ── Load data ─────────────────────────────────────────────
print("Loading VAE anomalies...")
df = pd.read_csv("data/vae_anomalies.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])

feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'log_event_count']
feature_names = [
    'CPU/Load Pattern (PC1)',
    'Memory Pressure (PC2)',
    'System Load Spread (PC3)',
    'Network I/O Pattern (PC4)',
    'Disk/Misc Pattern (PC5)',
    'Log Event Burst'
]

X = df[feature_cols].fillna(0).values
X_min = X.min(axis=0)
X_max = X.max(axis=0)
X_norm = (X - X_min) / (X_max - X_min + 1e-8)

def create_sequences(data, seq_len):
    seqs = []
    for i in range(len(data) - seq_len):
        seqs.append(data[i:i + seq_len])
    return np.array(seqs)

seqs = create_sequences(X_norm, SEQ_LEN)
tensor_seqs = torch.FloatTensor(seqs)

# Get anomaly indices aligned to sequences
df_scored = df.iloc[SEQ_LEN:].reset_index(drop=True)
anomaly_indices = df_scored[df_scored['vae_is_anomaly'] == 1].index.tolist()
print(f"Explaining {len(anomaly_indices)} VAE-LSTM anomalies...")

explanations = []

for idx in anomaly_indices:
    if idx >= len(tensor_seqs):
        continue

    sample         = tensor_seqs[idx:idx+1]
    baseline_err   = reconstruction_error(model, sample)
    attributions   = perturbation_attribution(model, sample, baseline_err)

    total = attributions.sum()
    pcts  = (attributions / total * 100) if total > 0 else attributions

    ranked = sorted(
        zip(feature_names, pcts),
        key=lambda x: x[1],
        reverse=True
    )

    top1 = ranked[0]
    top2 = ranked[1]

    row       = df_scored.iloc[idx]
    timestamp = str(row['timestamp'])
    vae_error = float(row['vae_error'])
    log_count = int(row['log_event_count'])

    nl_explanation = (
        f"Temporal anomaly at {timestamp}: "
        f"{top1[0]} showed abnormal pattern ({top1[1]:.1f}% contribution), "
        f"combined with {top2[0]} ({top2[1]:.1f}%). "
        f"Reconstruction error: {vae_error:.5f}. "
        f"Log activity: {log_count} events/min."
    )

    explanations.append({
        "timestamp":          timestamp,
        "vae_error":          vae_error,
        "log_event_count":    log_count,
        "top_feature":        top1[0],
        "top_feature_pct":    round(float(top1[1]), 1),
        "second_feature":     top2[0],
        "second_feature_pct": round(float(top2[1]), 1),
        "nl_explanation":     nl_explanation,
        "all_contributions":  {
            name: round(float(pct), 1)
            for name, pct in ranked
        }
    })

with open("data/vae_explanations.json", "w") as f:
    json.dump(explanations, f, indent=2)

print(f"\n✅ Saved: data/vae_explanations.json")
print(f"\n--- Sample VAE-LSTM Explanations ---\n")
for e in explanations[:3]:
    print(e['nl_explanation'])
    print()