import pandas as pd
import numpy as np
import shap
import json
from sklearn.ensemble import IsolationForest

print("Loading data...")
df = pd.read_csv("data/anomalies.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])

feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'log_event_count']
X = df[feature_cols].values

# Friendly names for features (for natural language output)
feature_names = [
    'CPU/Load Pattern (PC1)',
    'Memory Pressure (PC2)',
    'System Load Spread (PC3)',
    'Network I/O Pattern (PC4)',
    'Disk/Misc Pattern (PC5)',
    'Log Event Burst'
]

# Retrain model (same params as detector.py)
print("Training Isolation Forest...")
model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
model.fit(X)

# SHAP explainer — use TreeExplainer for Isolation Forest
print("Running SHAP explainer...")
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

# shap_values shape: (n_samples, n_features)
# Higher absolute SHAP value = more responsible for anomaly

# Only explain anomalous rows
anomaly_idx = df[df['is_anomaly'] == 1].index.tolist()
print(f"Generating explanations for {len(anomaly_idx)} anomalies...")

explanations = []

for idx in anomaly_idx:
    row_shap = shap_values[idx]           # SHAP values for this row
    abs_shap = np.abs(row_shap)           # Absolute contribution
    total = abs_shap.sum()
    percentages = (abs_shap / total * 100) if total > 0 else abs_shap

    # Sort features by contribution
    ranked = sorted(
        zip(feature_names, percentages, row_shap),
        key=lambda x: x[1],
        reverse=True
    )

    # Build natural language explanation
    top1_name, top1_pct, top1_val = ranked[0]
    top2_name, top2_pct, top2_val = ranked[1]

    direction1 = "elevated" if top1_val > 0 else "anomalously low"
    direction2 = "elevated" if top2_val > 0 else "anomalously low"

    log_count = int(df.loc[idx, 'log_event_count'])
    timestamp = str(df.loc[idx, 'timestamp'])

    # Natural language summary
    nl_explanation = (
        f"Anomaly at {timestamp}: "
        f"{top1_name} was {direction1} ({top1_pct:.1f}% contribution), "
        f"combined with {top2_name} {direction2} ({top2_pct:.1f}%). "
        f"Log burst: {log_count} events/min."
    )

    explanations.append({
        "timestamp": timestamp,
        "anomaly_score": float(df.loc[idx, 'anomaly_score']),
        "log_event_count": log_count,
        "top_feature": top1_name,
        "top_feature_pct": round(float(top1_pct), 1),
        "second_feature": top2_name,
        "second_feature_pct": round(float(top2_pct), 1),
        "nl_explanation": nl_explanation,
        "all_contributions": {
            name: round(float(pct), 1)
            for name, pct, _ in ranked
        }
    })

# Save explanations
with open("data/explanations.json", "w") as f:
    json.dump(explanations, f, indent=2)

print(f"\n✅ Saved: data/explanations.json")
print(f"\n--- Sample Explanations ---\n")
for e in explanations[:3]:
    print(e['nl_explanation'])
    print()