import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder

print("Loading processed data...")

# Load metrics
metrics = pd.read_csv("data/metrics_processed.csv")
metrics['timestamp'] = pd.to_datetime(metrics['timestamp'])

# Load logs — resample to 1-minute bins, count events per template per minute
logs = pd.read_csv("data/logs_processed.csv")
logs['timestamp'] = pd.to_datetime(logs['timestamp'])

# Count log events per minute
logs['minute'] = logs['timestamp'].dt.floor('1min')
log_counts = logs.groupby('minute')['event_id'].count().reset_index()
log_counts.columns = ['timestamp', 'log_event_count']

# Resample metrics to 1-minute bins
metrics['minute'] = metrics['timestamp'].dt.floor('1min')
metrics_resampled = metrics.groupby('minute')[['PC1','PC2','PC3','PC4','PC5']].mean().reset_index()
metrics_resampled.columns = ['timestamp', 'PC1', 'PC2', 'PC3', 'PC4', 'PC5']

# Merge metrics + log counts on timestamp
combined = pd.merge(metrics_resampled, log_counts, on='timestamp', how='inner')
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
preds = model.predict(X)         # -1 = anomaly, 1 = normal
scores = model.decision_function(X)  # lower = more anomalous

combined['anomaly'] = preds
combined['anomaly_score'] = scores
combined['is_anomaly'] = (preds == -1).astype(int)

# Save results
combined.to_csv("data/anomalies.csv", index=False)

# Summary
anomaly_count = (preds == -1).sum()
total = len(preds)
print(f"\n✅ Detection complete.")
print(f"Total time windows: {total}")
print(f"Anomalies flagged: {anomaly_count} ({anomaly_count/total*100:.1f}%)")
print(f"\nTop 5 anomalous moments:")
top = combined[combined['is_anomaly']==1].sort_values('anomaly_score').head(5)
print(top[['timestamp', 'anomaly_score', 'log_event_count', 'PC1']].to_string(index=False))