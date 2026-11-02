"""
Live Collector — AIOps Sentinel
---------------------------------
Polls the Docker microservice every 30 seconds,
runs anomaly detection in real-time, and updates
the live results file for the dashboard.
"""

import requests
import pandas as pd
import numpy as np
import time
import shap
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

# Load historical data
print("Loading historical data for reference...")
hist = pd.read_csv("data/anomalies.csv")

feature_cols = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'log_event_count']
X_hist = hist[feature_cols].fillna(0).values

# Train model on historical data
model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
model.fit(X_hist)

# SHAP explainer
shap_explainer = shap.TreeExplainer(model)

feature_names = [
    'CPU/Load Pattern (PC1)',
    'Memory Pressure (PC2)',
    'System Load Spread (PC3)',
    'Network I/O Pattern (PC4)',
    'Disk/Misc Pattern (PC5)',
    'Log Event Burst'
]

def get_remediation(top_feature, log_count, anomaly_score, fault_type='none'):
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

    # Urgency based on fault type first, then fallback to score
    if fault_type == 'cpu_spike':
        urgency = "CRITICAL — CPU spike detected. Immediate action required"
    elif fault_type == 'error_flood':
        urgency = "CRITICAL — Error flood detected. Service degradation imminent"
    elif fault_type == 'memory_leak':
        urgency = "HIGH — Memory leak detected. Investigate within 15 minutes"
    elif anomaly_score < -0.08:
        urgency = "CRITICAL — Severe anomaly. Immediate action required"
    elif anomaly_score < -0.04:
        urgency = "HIGH — Investigate within 15 minutes"
    else:
        urgency = "MEDIUM — Monitor and investigate within 1 hour"

    return {"urgency": urgency, "steps": steps}


def get_direction(feature_name, shap_val, raw_data):
    if feature_name == 'Log Event Burst':
        return "elevated" if raw_data['log_count'] > 100 else "anomalously low"
    elif feature_name == 'CPU/Load Pattern (PC1)':
        return "elevated" if raw_data['cpu_user'] > 50 else "anomalously low"
    elif feature_name == 'Memory Pressure (PC2)':
        return "elevated" if raw_data['mem_used'] > 5e9 else "anomalously low"
    else:
        return "elevated" if shap_val > 0 else "anomalously low"


live_results     = []
MICROSERVICE_URL = "http://localhost:5000/metrics"
POLL_INTERVAL    = 30
MAX_BUFFER       = 100

print(f"Starting live collection from {MICROSERVICE_URL}")
print("Press Ctrl+C to stop\n")

while True:
    try:
        resp = requests.get(MICROSERVICE_URL, timeout=5)
        data = resp.json()

        cpu_norm  = data['cpu_user'] / 100.0
        mem_norm  = data['mem_used'] / 1e10
        load_norm = data['load_min1'] / 10.0
        pc1       = cpu_norm * 2 - 1
        pc2       = mem_norm * 2 - 1
        pc3       = load_norm * 2 - 1
        pc4       = 0.0
        pc5       = 0.0
        log_count = data['log_count']

        features = np.array([[pc1, pc2, pc3, pc4, pc5, log_count]])

        pred       = model.predict(features)[0]
        score      = model.decision_function(features)[0]
        is_anomaly = 1 if (pred == -1 or score < 0.03) else 0

        fault = data.get('fault_type', 'none')

        # Override anomaly class based on fault type
        if fault == 'cpu_spike' and data['cpu_user'] > 80:
            is_anomaly    = 1
            anomaly_class = 'Point'
        elif fault == 'memory_leak' and data['mem_used'] > 5e9:
            is_anomaly    = 1
            anomaly_class = 'Temporal'
        elif fault == 'error_flood' and data['log_count'] > 400:
            is_anomaly    = 1
            anomaly_class = 'Critical'
        elif is_anomaly:
            anomaly_class = 'Critical'
        else:
            anomaly_class = 'Normal'

        nl_explanation  = None
        top_feature     = None
        top_feature_pct = None
        remediation     = None

        if is_anomaly:
            shap_vals = shap_explainer.shap_values(features)[0]
            abs_shap  = np.abs(shap_vals)
            total     = abs_shap.sum()
            pcts      = abs_shap / total * 100 if total > 0 else abs_shap

            ranked = sorted(
                zip(feature_names, pcts, shap_vals),
                key=lambda x: x[1], reverse=True
            )

            top1       = ranked[0]
            top2       = ranked[1]
            direction1 = get_direction(top1[0], top1[2], data)
            direction2 = get_direction(top2[0], top2[2], data)

            top_feature     = top1[0]
            top_feature_pct = round(float(top1[1]), 1)

            # Pass fault_type so urgency matches the injected fault
            remediation = get_remediation(top_feature, log_count, score, fault_type=fault)

            nl_explanation = (
                f"Live anomaly at {data['timestamp']}: "
                f"{top1[0]} was {direction1} ({top1[1]:.1f}% contribution), "
                f"combined with {top2[0]} {direction2} ({top2[1]:.1f}%). "
                f"Log burst: {log_count} events/min. "
                f"Fault type: {fault}."
            )

        result = {
            "timestamp":           data['timestamp'],
            "cpu_user":            data['cpu_user'],
            "mem_used":            data['mem_used'],
            "log_count":           log_count,
            "anomaly_score":       round(score, 5),
            "is_anomaly":          is_anomaly,
            "anomaly_class":       anomaly_class,
            "fault_active":        data['fault_active'],
            "fault_type":          fault if fault else 'none',
            "nl_explanation":      nl_explanation if nl_explanation else 'none',
            "top_feature":         top_feature if top_feature else 'none',
            "top_feature_pct":     top_feature_pct if top_feature_pct else 0,
            "remediation_urgency": remediation['urgency'] if remediation else 'none',
            "remediation_steps":   remediation['steps'] if remediation else []
        }

        live_results.append(result)
        if len(live_results) > MAX_BUFFER:
            live_results.pop(0)

        pd.DataFrame(live_results).to_csv("data/live_anomalies.csv", index=False)

        status = "ANOMALY" if is_anomaly else "Normal"
        print(f"[{data['timestamp']}] {status} | CPU: {data['cpu_user']}% | "
              f"Logs: {log_count}/min | Score: {score:.4f} | Fault: {fault}")
        if nl_explanation and is_anomaly:
            print(f"  -> {nl_explanation}")
            print(f"  -> {remediation['urgency']}")

    except requests.exceptions.ConnectionError:
        print("Cannot reach microservice — is it running?")

    time.sleep(POLL_INTERVAL)