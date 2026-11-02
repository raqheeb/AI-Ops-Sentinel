"""
VAE-LSTM Model — AIOps Sentinel

Core innovation module. A Variational Autoencoder
coupled with an LSTM encoder learns the 'normal'
temporal behavior of the system. Anomalies are
detected as high reconstruction error — Temporal
Coherence Disruption detection.

Output: data/vae_anomalies.csv, model/vae_model.pth
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset

#Reproducibility 
torch.manual_seed(42)
np.random.seed(42)

# Hyperparameters
SEQ_LEN     = 10    # look at 10 time steps at once
INPUT_DIM   = 6     # PC1-PC5 + log_event_count
HIDDEN_DIM  = 32    # LSTM hidden size
LATENT_DIM  = 8     # VAE latent space size
EPOCHS      = 50
BATCH_SIZE  = 32
LR          = 0.001
THRESHOLD_PERCENTILE = 95  # top 5% reconstruction errors = anomaly


#
# 
# Model Definition
class VAE_LSTM(nn.Module):
    def __init__(self):
        super(VAE_LSTM, self).__init__()

        # Encoder — LSTM reads the sequence
        self.lstm_enc = nn.LSTM(
            INPUT_DIM, HIDDEN_DIM,
            batch_first=True, num_layers=1
        )

        # VAE latent space — mean and log variance
        self.fc_mu     = nn.Linear(HIDDEN_DIM, LATENT_DIM)
        self.fc_logvar = nn.Linear(HIDDEN_DIM, LATENT_DIM)

        # Decoder — reconstructs the sequence
        self.fc_decode = nn.Linear(LATENT_DIM, HIDDEN_DIM)
        self.lstm_dec  = nn.LSTM(
            HIDDEN_DIM, INPUT_DIM,
            batch_first=True, num_layers=1
        )

    def reparameterize(self, mu, logvar):
        """Reparameterization trick — enables backprop through sampling"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Encode
        _, (h_n, _) = self.lstm_enc(x)
        h = h_n.squeeze(0)

        # Latent space
        mu     = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        z      = self.reparameterize(mu, logvar)

        # Decode — expand z across sequence length
        z_expanded = self.fc_decode(z)
        z_expanded = z_expanded.unsqueeze(1).repeat(1, SEQ_LEN, 1)
        recon, _   = self.lstm_dec(z_expanded)

        return recon, mu, logvar


#Loss Function 
def vae_loss(recon, original, mu, logvar):
    """Reconstruction loss + KL divergence"""
    recon_loss = nn.MSELoss()(recon, original)
    kl_loss    = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + 0.001 * kl_loss


#Data Preparation
def create_sequences(data, seq_len):
    """Slide a window of seq_len over the data"""
    sequences = []
    for i in range(len(data) - seq_len):
        sequences.append(data[i:i + seq_len])
    return np.array(sequences)


# Main Training 
print("Loading processed data...")
df = pd.read_csv("data/anomalies.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'log_event_count']
X = df[feature_cols].fillna(0).values

# Normalize to [0,1]
X_min = X.min(axis=0)
X_max = X.max(axis=0)
X_norm = (X - X_min) / (X_max - X_min + 1e-8)

# Use only "normal" windows for training (bottom 90% anomaly score)
threshold_train = np.percentile(df['anomaly_score'], 10)
normal_mask = df['anomaly_score'] >= threshold_train
X_normal = X_norm[normal_mask]
print(f"Training on {len(X_normal)} normal time windows")

# Create sequences
seqs = create_sequences(X_normal, SEQ_LEN)
print(f"Sequences created: {seqs.shape}")

# PyTorch dataset
tensor_seqs = torch.FloatTensor(seqs)
dataset     = TensorDataset(tensor_seqs)
loader      = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

# Train 
model     = VAE_LSTM()
optimizer = optim.Adam(model.parameters(), lr=LR)

print(f"\nTraining VAE-LSTM for {EPOCHS} epochs...")
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for (batch,) in loader:
        optimizer.zero_grad()
        recon, mu, logvar = model(batch)
        loss = vae_loss(recon, batch, mu, logvar)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    avg_loss = total_loss / len(loader)
    if (epoch + 1) % 10 == 0:
        print(f"  Epoch {epoch+1}/{EPOCHS} — Loss: {avg_loss:.6f}")

print("\nTraining complete.")

#Anomaly Scoring on Full Dataset 
print("Scoring full dataset...")
model.eval()

all_seqs   = create_sequences(X_norm, SEQ_LEN)
all_tensor = torch.FloatTensor(all_seqs)

reconstruction_errors = []
with torch.no_grad():
    for i in range(0, len(all_tensor), BATCH_SIZE):
        batch        = all_tensor[i:i+BATCH_SIZE]
        recon, _, _  = model(batch)
        errors       = ((recon - batch) ** 2).mean(dim=(1, 2))
        reconstruction_errors.extend(errors.numpy())

reconstruction_errors = np.array(reconstruction_errors)

# Threshold — top 5% = anomaly
threshold = np.percentile(reconstruction_errors, THRESHOLD_PERCENTILE)
vae_labels = (reconstruction_errors > threshold).astype(int)

print(f"Reconstruction error threshold: {threshold:.6f}")
print(f"VAE-LSTM anomalies detected: {vae_labels.sum()}")

# Align with original dataframe (sequences start at index SEQ_LEN)
df_scored = df.iloc[SEQ_LEN:].copy().reset_index(drop=True)
df_scored['vae_error']      = reconstruction_errors
df_scored['vae_is_anomaly'] = vae_labels

# Save
df_scored.to_csv("data/vae_anomalies.csv", index=False)
torch.save(model.state_dict(), "model/vae_model.pth")

print(f"\n✅ Saved: data/vae_anomalies.csv")
print(f"✅ Saved: model/vae_model.pth")

# Show top anomalies
print("\nTop 5 VAE-LSTM anomalous moments:")
top = df_scored[df_scored['vae_is_anomaly']==1].sort_values(
    'vae_error', ascending=False
).head(5)
print(top[['timestamp', 'vae_error', 'log_event_count']].to_string(index=False))