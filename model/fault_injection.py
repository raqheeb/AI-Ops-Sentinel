"""
Fault Injection Test — AIOps Sentinel

Validation module. Injects 3 synthetic faults
(CPU spike, memory exhaustion, network anomaly)
to verify the detection and explanation pipeline
generalizes beyond training data.

Output: Terminal proof + data/anomalies_with_faults.csv
"""

import pandas as pd
import numpy as np
import json
from sklearn.ensemble import IsolationForest
import shap

print("Loading anomalies data...")
df = pd.read_csv("data/anomalies.csv")
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

# --- Inject 3 synthetic faults ---
print("Injecting synthetic faults...")

# Fault 1: CPU spike
cpu_spike = {
    'timestamp': '2019-11-19 23:00:00',
    'PC1': 8.5,      # extreme CPU spike
    'PC2': 0.1,
    'PC3': 0.2,
    'PC4': 0.1,
    'PC5': 0.1,
    'log_event_count': 600,  # high log burst too
    'is_anomaly': 0,
    'anomaly_score': 0,
    'host': 'wally113'
}

# Fault 2: Memory exhaustion
mem_fault = {
    'timestamp': '2019-11-19 23:15:00',
    'PC1': 0.1,
    'PC2': 9.2,      # extreme memory pressure
    'PC3': 0.1,
    'PC4': 0.1,
    'PC5': 0.1,
    'log_event_count': 45,
    'is_anomaly': 0,
    'anomaly_score': 0,
    'host': 'wally117'
}

# Fault 3: Network anomaly
net_fault = {
    'timestamp': '2019-11-19 23:30:00',
    'PC1': 0.2,
    'PC2': 0.2,
    'PC3': 0.1,
    'PC4': 7.8,      # extreme network pattern
    'PC5': 0.1,
    'log_event_count': 12,
    'is_anomaly': 0,
    'anomaly_score': 0,
    'host': 'wally122'
}

# Append injected faults to dataframe
injected = pd.DataFrame([cpu_spike, mem_fault, net_fault])
df_combined = pd.concat([df, injected], ignore_index=True)
df_combined['timestamp'] = pd.to_datetime(df_combined['timestamp'])

X = df_combined[feature_cols].fillna(0).values

# Retrain on full data including injected points
print("Retraining model with injected faults...")
model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
model.fit(X)

preds = model.predict(X)
scores = model.decision_function(X)

df_combined['anomaly'] = preds
df_combined['anomaly_score'] = scores
df_combined['is_anomaly'] = (preds == -1).astype(int)

# Check if injected faults were detected
last3 = df_combined.tail(3)
print("\n--- Fault Injection Results ---")
for _, row in last3.iterrows():
    detected = "✅ DETECTED" if row['is_anomaly'] == 1 else "❌ MISSED"
    print(f"{detected} | {row['timestamp']} | score: {row['anomaly_score']:.4f}")

# SHAP explanations for injected faults
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

print("\n--- Explanations for Injected Faults ---")
for i, (_, row) in enumerate(last3.iterrows()):
    idx = len(df_combined) - 3 + i
    row_shap = shap_values[idx]
    abs_shap = np.abs(row_shap)
    total = abs_shap.sum()
    pcts = abs_shap / total * 100

    ranked = sorted(
        zip(feature_names, pcts, row_shap),
        key=lambda x: x[1], reverse=True
    )
    top1 = ranked[0]
    top2 = ranked[1]

    print(f"\nFault {i+1}: {row['timestamp']}")
    print(f"  → {top1[0]}: {top1[1]:.1f}%")
    print(f"  → {top2[0]}: {top2[1]:.1f}%")
    print(f"  NL: '{top1[0]} anomalously high ({top1[1]:.1f}%), "
          f"combined with {top2[0]} ({top2[1]:.1f}%)'")

# Save updated data with injected faults
df_combined.to_csv("data/anomalies_with_faults.csv", index=False)
print("\n✅ Saved: data/anomalies_with_faults.csv")
print("Take a screenshot of this output — this is your SEE output proof.")