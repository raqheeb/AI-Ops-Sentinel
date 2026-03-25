import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import os

# All host files
hosts = ['wally113', 'wally117', 'wally122', 'wally123', 'wally124']
base_path = "data/sequential_data/metrics"

# Time window(IMPORTANT file)
START = pd.Timestamp("2019-11-19 18:38:39")
END   = pd.Timestamp("2019-11-20 02:30:00")

all_metrics = []

for host in hosts:
    path = os.path.join(base_path, f"{host}_metrics.csv")
    df = pd.read_csv(path)
    
    # Clean timestamp(emove CEST and parse)
    df['timestamp'] = df['now'].str.replace(' CEST', '', regex=False)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Filter to experiment window
    df = df[(df['timestamp'] >= START) & (df['timestamp'] <= END)]
    
    # Add hostname
    df['host'] = host
    all_metrics.append(df)
    print(f"{host}: {len(df)} rows after filtering")

# Combine hosts(all)
combined = pd.concat(all_metrics, ignore_index=True)
print(f"\nTotal combined rows: {len(combined)}")

# Select numeric columns only
numeric_cols = ['cpu.user', 'mem.used', 'load.cpucore', 'load.min1', 'load.min5', 'load.min15']
X = combined[numeric_cols].fillna(0)

# Normalize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# PCA — reduce to 5 components
pca = PCA(n_components=5)
X_pca = pca.fit_transform(X_scaled)
print(f"\nVariance explained by 5 components: {pca.explained_variance_ratio_.sum()*100:.1f}%")

# Save output
out = pd.DataFrame(X_pca, columns=[f'PC{i+1}' for i in range(5)])
out['timestamp'] = combined['timestamp'].values
out['host'] = combined['host'].values
out.to_csv("data/metrics_processed.csv", index=False)
print("\n✅ Saved: data/metrics_processed.csv")