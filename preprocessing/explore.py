import pandas as pd

#Logs
logs = pd.read_csv("data/sequential_data/logs/logs_aggregated_sequential.csv")
print("=== LOGS ===")
print("Shape:", logs.shape)
print("Columns:", logs.columns.tolist())
print("First row:\n", logs.head(1).to_string())
print()

#Metrics
metrics = pd.read_csv("data/sequential_data/metrics/wally113_metrics.csv")
print("=== METRICS (wally113) ===")
print("Shape:", metrics.shape)
print("Columns:", metrics.columns.tolist())
print("First row:\n", metrics.head(1).to_string())