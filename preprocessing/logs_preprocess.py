import pandas as pd
from drain3 import TemplateMiner

# Time window
START = pd.Timestamp("2019-11-19 18:38:39")
END   = pd.Timestamp("2019-11-20 02:30:00")
print("Loading logs...")
logs = pd.read_csv("data/sequential_data/logs/logs_aggregated_sequential.csv")

# Parse timestamp
logs['timestamp'] = pd.to_datetime(logs['Timestamp'], errors='coerce')

# Filter to experiment window
logs = logs[(logs['timestamp'] >= START) & (logs['timestamp'] <= END)]
print(f"Rows after time filter: {len(logs)}")

# Drop rows Payload = empty
logs = logs.dropna(subset=['Payload'])
print(f"Rows after dropping empty payloads: {len(logs)}")

# Run Drain3 log templating on Payload column
print("\nRunning Drain3 log templating...")
miner = TemplateMiner()
templates = []

for i, payload in enumerate(logs['Payload'].astype(str)):
    result = miner.add_log_message(payload)
    templates.append(result['template_mined'])
    if i % 10000 == 0:
        print(f"  Processed {i}/{len(logs)} logs...")
logs['event_template'] = templates
logs['event_id'] = pd.factorize(logs['event_template'])[0]

# Save output
out = logs[['timestamp', 'Hostname', 'log_level', 'event_template', 'event_id', 'http_status']]
out.to_csv("data/logs_processed.csv", index=False)
print(f"\n✅ Saved: data/logs_processed.csv")
print(f"Unique log templates found: {logs['event_id'].nunique()}")
print(f"\nSample templates:")
print(logs['event_template'].value_counts().head(5))