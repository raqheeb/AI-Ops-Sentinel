"""
FastAPI Inference Server — AIOps Sentinel
------------------------------------------
Serves anomaly detection results and SHAP explanations
via REST API. Endpoints:
  GET /summary             — system health overview
  GET /anomalies           — Isolation Forest anomaly list
  GET /timeline            — full time series data
  GET /vae-anomalies       — VAE-LSTM anomaly list
  GET /compare             — model agreement comparison
  GET /explanations        — SHAP fault explanations
  GET /explanations/latest — worst anomaly explanation
  GET /vae-explanations    — VAE-LSTM explanations
  GET /live                — live collector results
  GET /live/anomalies      — live anomalies only
  GET /inject/{fault_type} — inject fault into microservice
  GET /recover             — recover microservice
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json as json_lib
import ast
import requests

app = FastAPI(title="AIOps Sentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ── Data loaders ──────────────────────────────────────────

def load_anomalies():
    df = pd.read_csv("data/anomalies.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def load_vae():
    df = pd.read_csv("data/vae_anomalies.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# ── Endpoints ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "AIOps Sentinel is running"}

@app.get("/summary")
def get_summary():
    iso_df = load_anomalies()
    vae_df = load_vae()
    total     = len(iso_df)
    iso_count = int(iso_df['is_anomaly'].sum())
    vae_count = int(vae_df['vae_is_anomaly'].sum())
    return {
        "total_windows":          total,
        "anomalies_detected":     iso_count,
        "vae_anomalies_detected": vae_count,
        "anomaly_rate":           round(iso_count / total * 100, 1),
        "health_score":           round((1 - iso_count / total) * 100, 1),
        "worst_anomaly_time":     str(iso_df.loc[iso_df['anomaly_score'].idxmin(), 'timestamp']),
        "model":                  "Isolation Forest + VAE-LSTM"
    }

@app.get("/anomalies")
def get_anomalies():
    df = load_anomalies()
    anomalies = df[df['is_anomaly'] == 1].copy()
    anomalies['timestamp'] = anomalies['timestamp'].astype(str)
    if 'host' not in anomalies.columns:
        anomalies['host'] = 'wally113'
    return anomalies[['timestamp', 'anomaly_score', 'log_event_count', 'PC1', 'PC2', 'host']].to_dict(orient="records")

@app.get("/timeline")
def get_timeline():
    df = load_anomalies()
    df['timestamp'] = df['timestamp'].astype(str)
    return df[['timestamp', 'anomaly_score', 'log_event_count', 'is_anomaly']].to_dict(orient="records")

@app.get("/vae-anomalies")
def get_vae_anomalies():
    df = load_vae()
    anomalies = df[df['vae_is_anomaly'] == 1].copy()
    anomalies['timestamp'] = anomalies['timestamp'].astype(str)
    return anomalies[['timestamp', 'vae_error', 'log_event_count']].to_dict(orient="records")

@app.get("/compare")
def compare_models():
    iso = load_anomalies()
    vae = load_vae()
    iso_times = set(iso[iso['is_anomaly'] == 1]['timestamp'].astype(str))
    vae_times = set(vae[vae['vae_is_anomaly'] == 1]['timestamp'].astype(str))
    both     = iso_times & vae_times
    iso_only = iso_times - vae_times
    vae_only = vae_times - iso_times
    return {
        "isolation_forest_total": len(iso_times),
        "vae_lstm_total":         len(vae_times),
        "agreed_anomalies":       len(both),
        "isolation_forest_only":  len(iso_only),
        "vae_lstm_only":          len(vae_only),
        "agreement_rate":         round(len(both) / max(len(iso_times), len(vae_times)) * 100, 1)
    }

@app.get("/explanations")
def get_explanations():
    with open("data/explanations.json", "r") as f:
        return json_lib.load(f)

@app.get("/explanations/latest")
def get_latest_explanation():
    with open("data/explanations.json", "r") as f:
        data = json_lib.load(f)
    return min(data, key=lambda x: x['anomaly_score'])

@app.get("/vae-explanations")
def get_vae_explanations():
    with open("data/vae_explanations.json", "r") as f:
        return json_lib.load(f)

@app.get("/live")
def get_live():
    try:
        df = pd.read_csv("data/live_anomalies.csv")
        df['timestamp']     = df['timestamp'].astype(str)
        df['fault_type']    = df['fault_type'].fillna('none').astype(str)
        df['anomaly_class'] = df['anomaly_class'].fillna('Normal').astype(str)
        df['nl_explanation']      = df['nl_explanation'].fillna('none').astype(str)
        df['remediation_urgency'] = df['remediation_urgency'].fillna('none').astype(str)

        # Parse remediation_steps from string back to list
        def parse_steps(val):
            if not val or val in ('none', '[]', 'nan'):
                return []
            if isinstance(val, list):
                return val
            try:
                return ast.literal_eval(str(val))
            except:
                return []

        df['remediation_steps'] = df['remediation_steps'].apply(parse_steps)
        return df.tail(50).to_dict(orient="records")
    except FileNotFoundError:
        return []

@app.get("/live/anomalies")
def get_live_anomalies():
    try:
        df = pd.read_csv("data/live_anomalies.csv")
        df['timestamp'] = df['timestamp'].astype(str)
        return df[df['is_anomaly'] == 1].to_dict(orient="records")
    except FileNotFoundError:
        return []

@app.get("/inject/{fault_type}")
def inject_fault(fault_type: str):
    try:
        resp = requests.get(f"http://localhost:5000/inject/{fault_type}", timeout=5)
        return resp.json()
    except:
        return {"error": "microservice unreachable"}

@app.get("/recover")
def recover_system():
    try:
        resp = requests.get("http://localhost:5000/recover", timeout=5)
        return resp.json()
    except:
        return {"error": "microservice unreachable"}