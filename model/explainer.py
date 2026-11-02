"""
SHAP Explanation Module — AIOps Sentinel
-----------------------------------------
Uses SHAP TreeExplainer to attribute each anomaly
to its contributing features. Generates natural
language explanations and remediation steps for
human auditors.

Output: data/explanations.json
"""

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

feature_names = [
    'CPU/Load Pattern (PC1)',
    'Memory Pressure (PC2)',
    'System Load Spread (PC3)',
    'Network I/O Pattern (PC4)',
    'Disk/Misc Pattern (PC5)',
    'Log Event Burst'
]

# Retrain model
print("Training Isolation Forest...")
model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
model.fit(X)

# SHAP explainer
print("Running SHAP explainer...")
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

# ── Remediation logic ─────────────────────────────────────
def get_remediation(top_feature, log_count, anomaly_score):
    remediations = {
        'CPU/Load Pattern (PC1)': [
            "Identify top CPU-consuming processes using 'top' or 'htop'",
            "Check for runaway threads or infinite loops in application logs",
            "Consider horizontal scaling — add more instances to distribute load",
            "Review recent deployments for performance regressions"
        ],
        'Memory Pressure (PC2)': [
            "Check for memory leaks using heap profiler",
            "Review application memory limits and increase if necessary",
            "Restart affected services to release accumulated memory",
            "Analyze object retention patterns in application code"
        ],
        'System Load Spread (PC3)': [
            "Review load balancer configuration for uneven distribution",
            "Check CPU scheduling and process priority settings",
            "Investigate I/O wait times — possible disk bottleneck",
            "Consider rebalancing workload across available nodes"
        ],
        'Network I/O Pattern (PC4)': [
            "Check for unusual outbound connections or data exfiltration",
            "Review network bandwidth usage per service",
            "Inspect firewall logs for blocked or rejected connections",
            "Consider rate limiting on high-traffic endpoints"
        ],
        'Disk/Misc Pattern (PC5)': [
            "Check disk usage and clean up logs or temp files",
            "Review I/O wait — consider SSD upgrade or RAID configuration",
            "Check for disk errors using 'fsck' or 'smartctl'",
            "Archive or rotate old log files to free disk space"
        ],
        'Log Event Burst': [
            "Investigate root cause of log spike — check error rates",
            "Review application error handling for excessive logging",
            "Check for cascading failures triggering repeated error logs",
            "Implement log sampling or rate limiting for verbose services"
        ]
    }

    steps = remediations.get(top_feature, ["Investigate system metrics manually"])

    if anomaly_score < -0.08:
        urgency = "🔴 CRITICAL — Immediate action required"
    elif anomaly_score < -0.04:
        urgency = "🟠 HIGH — Investigate within 15 minutes"
    else:
        urgency = "🟡 MEDIUM — Monitor and investigate within 1 hour"

    return {"urgency": urgency, "steps": steps}

# ── Generate explanations ─────────────────────────────────
anomaly_idx = df[df['is_anomaly'] == 1].index.tolist()
print(f"Generating explanations for {len(anomaly_idx)} anomalies...")

explanations = []

for idx in anomaly_idx:
    row_shap    = shap_values[idx]
    abs_shap    = np.abs(row_shap)
    total       = abs_shap.sum()
    percentages = (abs_shap / total * 100) if total > 0 else abs_shap

    ranked = sorted(
        zip(feature_names, percentages, row_shap),
        key=lambda x: x[1],
        reverse=True
    )

    top1_name, top1_pct, top1_val = ranked[0]
    top2_name, top2_pct, top2_val = ranked[1]

    direction1 = "elevated" if top1_val > 0 else "anomalously low"
    direction2 = "elevated" if top2_val > 0 else "anomalously low"

    log_count     = int(df.loc[idx, 'log_event_count'])
    timestamp     = str(df.loc[idx, 'timestamp'])
    anomaly_score = float(df.loc[idx, 'anomaly_score'])

    nl_explanation = (
        f"Anomaly at {timestamp}: "
        f"{top1_name} was {direction1} ({top1_pct:.1f}% contribution), "
        f"combined with {top2_name} {direction2} ({top2_pct:.1f}%). "
        f"Log burst: {log_count} events/min."
    )

    remediation = get_remediation(top1_name, log_count, anomaly_score)

    explanations.append({
        "timestamp":          timestamp,
        "anomaly_score":      anomaly_score,
        "log_event_count":    log_count,
        "top_feature":        top1_name,
        "top_feature_pct":    round(float(top1_pct), 1),
        "second_feature":     top2_name,
        "second_feature_pct": round(float(top2_pct), 1),
        "nl_explanation":     nl_explanation,
        "remediation":        remediation,
        "all_contributions":  {
            name: round(float(pct), 1)
            for name, pct, _ in ranked
        }
    })

with open("data/explanations.json", "w") as f:
    json.dump(explanations, f, indent=2)

print(f"\n✅ Saved: data/explanations.json")
print(f"\n--- Sample Explanations ---\n")
for e in explanations[:3]:
    print(e['nl_explanation'])
    print(f"  Urgency: {e['remediation']['urgency']}")
    print(f"  Fix: {e['remediation']['steps'][0]}")
    print()