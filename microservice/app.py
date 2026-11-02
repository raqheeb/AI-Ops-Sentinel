from flask import Flask, jsonify
import random
import time
import threading

app = Flask(__name__)

# Shared state — can be modified by injector
state = {
    "fault_active": False,
    "fault_type": None,
    "start_time": time.time()
}

def get_metrics():
    """Generate realistic metrics — spikes when fault is active"""
    base_cpu    = random.uniform(10, 30)
    base_mem    = random.uniform(40, 60)
    base_load   = random.uniform(0.5, 1.5)
    log_count   = random.randint(20, 80)

    if state["fault_active"]:
        if state["fault_type"] == "cpu_spike":
            base_cpu  = random.uniform(85, 99)
            log_count = random.randint(400, 600)
        elif state["fault_type"] == "memory_leak":
            base_mem  = random.uniform(88, 99)
            log_count = random.randint(50, 100)
        elif state["fault_type"] == "error_flood":
            log_count = random.randint(500, 700)
            base_cpu  = random.uniform(60, 80)

    return {
        "timestamp":    time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_user":     round(base_cpu, 2),
        "mem_used":     round(base_mem * 1e8, 0),
        "load_min1":    round(base_load, 2),
        "load_min5":    round(base_load * 0.9, 2),
        "load_min15":   round(base_load * 0.8, 2),
        "log_count":    log_count,
        "fault_active": state["fault_active"],
        "fault_type":   state["fault_type"]
    }

@app.route("/metrics")
def metrics():
    return jsonify(get_metrics())

@app.route("/health")
def health():
    return jsonify({"status": "running", "uptime": round(time.time() - state["start_time"], 1)})

@app.route("/inject/<fault_type>")
def inject(fault_type):
    if fault_type in ["cpu_spike", "memory_leak", "error_flood"]:
        state["fault_active"] = True
        state["fault_type"]   = fault_type
        return jsonify({"status": "fault injected", "type": fault_type})
    return jsonify({"error": "unknown fault type"}), 400

@app.route("/recover")
def recover():
    state["fault_active"] = False
    state["fault_type"]   = None
    return jsonify({"status": "system recovered"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)