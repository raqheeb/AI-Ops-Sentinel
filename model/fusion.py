"""
Model Fusion Module — AIOps Sentinel

Combines Isolation Forest and VAE-LSTM detections
into a unified anomaly classification system.

Classification logic:
  Critical  → flagged by BOTH models  (high confidence)
  Temporal  → VAE-LSTM only           (temporal pattern break)
  Point     → Isolation Forest only   (sudden spike)
  Normal    → neither model flagged

Output: data/fused_anomalies.csv
"""

import pandas as pd

print("Loading model outputs...")
iso = pd.read_csv("data/anomalies.csv")
vae = pd.read_csv("data/vae_anomalies.csv")

iso['timestamp'] = pd.to_datetime(iso['timestamp'])
vae['timestamp'] = pd.to_datetime(vae['timestamp'])

# Merge both on timestamp
merged = pd.merge(
    iso[['timestamp', 'anomaly_score', 'log_event_count', 'PC1', 'PC2', 'is_anomaly']],
    vae[['timestamp', 'vae_error', 'vae_is_anomaly']],
    on='timestamp',
    how='inner'
)

# Classification logic
def classify(row):
    iso_flag = row['is_anomaly'] == 1
    vae_flag = row['vae_is_anomaly'] == 1
    if iso_flag and vae_flag:
        return 'Critical'
    elif vae_flag:
        return 'Temporal'
    elif iso_flag:
        return 'Point'
    else:
        return 'Normal'

merged['anomaly_class'] = merged.apply(classify, axis=1)

# Severity score — weighted combination
merged['severity_score'] = (
    merged['anomaly_score'].abs() * 0.5 +
    merged['vae_error'] * 0.5
)

# Save
merged.to_csv("data/fused_anomalies.csv", index=False)

# Summary
print("\n--- Fusion Results ---")
counts = merged['anomaly_class'].value_counts()
for cls in ['Critical', 'Temporal', 'Point', 'Normal']:
    count = counts.get(cls, 0)
    print(f"  {cls:10} → {count} windows")

print(f"\nTotal windows: {len(merged)}")
print("\nTop Critical anomalies:")
critical = merged[merged['anomaly_class'] == 'Critical'].sort_values(
    'severity_score', ascending=False
).head(5)
print(critical[['timestamp', 'severity_score', 'log_event_count']].to_string(index=False))
print("\n✅ Saved: data/fused_anomalies.csv")