from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json as json_lib

app = FastAPI(title="AIOps Sentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

def load_anomalies():
    df = pd.read_csv("data/anomalies.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def load_vae():
    df = pd.read_csv("data/vae_anomalies.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

@app.get("/")
def root():
    return {"status": "AIOps Sentinel is running"}

@app.get("/anomalies")
def get_anomalies():
    df = load_anomalies()
    anomalies = df[df['is_anomaly'] == 1].copy()
    anomalies['timestamp'] = anomalies['timestamp'].astype(str)
    return anomalies[['timestamp', 'anomaly_score', 'log_event_count', 'PC1', 'PC2']].to_dict(orient="records")

@app.get("/timeline")
def get_timeline():
    df = load_anomalies()
    df['timestamp'] = df['timestamp'].astype(str)
    return df[['timestamp', 'anomaly_score', 'log_event_count', 'is_anomaly']].to_dict(orient="records")

@app.get("/summary")
def get_summary():
    iso_df = load_anomalies()
    vae_df = load_vae()
    total = len(iso_df)
    iso_count = int(iso_df['is_anomaly'].sum())
    vae_count = int(vae_df['is_anomaly_vae'].sum())
    return {
        "total_windows": total,
        "anomalies_detected": iso_count,
        "vae_anomalies_detected": vae_count,
        "anomaly_rate": round(iso_count / total * 100, 1),
        "health_score": round((1 - iso_count / total) * 100, 1),
        "worst_anomaly_time": str(iso_df.loc[iso_df['anomaly_score'].idxmin(), 'timestamp']),
        "model": "Isolation Forest + VAE-LSTM"
    }

@app.get("/vae_anomalies")
def get_vae_anomalies():
    df = load_vae()
    anomalies = df[df['is_anomaly_vae'] == 1].copy()
    anomalies['timestamp'] = anomalies['timestamp'].astype(str)
    return anomalies[['timestamp', 'reconstruction_error', 'is_anomaly_vae']].to_dict(orient="records")

@app.get("/vae_summary")
def get_vae_summary():
    df = load_vae()
    total = len(df)
    anomaly_count = int(df['is_anomaly_vae'].sum())
    return {
        "total_windows": total,
        "anomalies_detected": anomaly_count,
        "anomaly_rate": round(anomaly_count / total * 100, 1),
        "health_score": round((1 - anomaly_count / total) * 100, 1),
        "worst_anomaly_time": str(df.loc[df['reconstruction_error'].idxmax(), 'timestamp'])
    }

    import json as json_lib

@app.get("/explanations")
def get_explanations():
    with open("data/explanations.json", "r") as f:
        data = json_lib.load(f)
    return data

@app.get("/explanations/latest")
def get_latest_explanation():
    with open("data/explanations.json", "r") as f:
        data = json_lib.load(f)
    # Return worst anomaly explanation
    worst = min(data, key=lambda x: x['anomaly_score'])
    return worst