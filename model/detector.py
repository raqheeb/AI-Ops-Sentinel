"""
Anomaly Detection Module — AIOps Sentinel
------------------------------------------
Merges PCA-reduced metrics with log event counts
into 1-minute time windows. Trains Isolation Forest
as baseline anomaly detector. Flags time windows
with reconstruction scores below threshold.

Output: data/anomalies.csv
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

print("Loading processed data...")

# Load metrics
metrics = pd.read_csv("data/metrics_processed.csv")
metrics['timestamp'] = pd.to_datetime(metrics['timestamp'])

# Load logs
logs = pd.read_csv("data/logs_processed.csv")
logs['timestamp'] = pd.to_datetime(logs['timestamp'])

# Count log events per minute
logs['minute'] = logs['timestamp'].dt.floor('1min')
log_counts = logs.groupby('minute')['event_id'].count().reset_index()
log_counts.columns = ['timestamp', 'log_event_count']

# Track dominant host per minute
metrics['minute'] = metrics['timestamp'].dt.floor('1min')
host_per_minute = metrics.groupby('minute')['host'].agg(
    lambda x: x.value_counts().index[0]
).reset_index()
host_per_minute.columns = ['timestamp', 'host']

# Resample metrics to 1-minute bins
metrics_resampled = metrics.groupby('minute')[['PC1','PC2','PC3','PC4','PC5']].mean().reset_index()
metrics_resampled.columns = ['timestamp', 'PC1', 'PC2', 'PC3', 'PC4', 'PC5']

# Merge host into metrics
metrics_resampled = pd.merge(metrics_resampled, host_per_minute, on='timestamp', how='left')

# Merge metrics + log counts
combined = pd.merge(metrics_resampled, log_counts, on='timestamp', how='inner')
combined['host'] = combined['host'].fillna('wally113')
combined = combined.fillna(0)
print(f"Combined shape after merging: {combined.shape}")

# Feature matrix
feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'log_event_count']
X = combined[feature_cols].values

# Train Isolation Forest
print("Training Isolation Forest...")
model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
model.fit(X)

# Predict
preds  = model.predict(X)
scores = model.decision_function(X)

combined['anomaly']      = preds
combined['anomaly_score'] = scores
combined['is_anomaly']   = (preds == -1).astype(int)

# Save results
combined.to_csv("data/anomalies.csv", index=False)

# Summary
anomaly_count = (preds == -1).sum()
total         = len(preds)
print(f"\n✅ Detection complete.")
print(f"Total time windows: {total}")
print(f"Anomalies flagged: {anomaly_count} ({anomaly_count/total*100:.1f}%)")
print(f"\nHost distribution in anomalies:")
print(combined[combined['is_anomaly']==1]['host'].value_counts())
print(f"\nTop 5 anomalous moments:")
top = combined[combined['is_anomaly']==1].sort_values('anomaly_score').head(5)
print(top[['timestamp', 'anomaly_score', 'log_event_count', 'PC1', 'host']].to_string(index=False))