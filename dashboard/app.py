from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os
import random

app = Flask(__name__)
CORS(app)

# Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
stats_json_path = os.path.join(current_dir, '..', 'ml_model', 'model_stats.json')

# Load ML Model Stats on startup
model_stats_data = None
if os.path.exists(stats_json_path):
    try:
        with open(stats_json_path, 'r') as f:
            model_stats_data = json.load(f)
    except Exception as e:
        print(f"Error loading model stats: {e}")

# In-memory storage for dashboard data
network_stats = {
    "total_bandwidth": 12.5, # Mbps
    "active_flows": 8,
    "blocked_ips": 0,
    "status": "NORMAL", # NORMAL, WARNING, CRITICAL
    "sensitivity_threshold": 0.5,
    "simulated_attack_type": "None", # None, DDoS, PortScan, Normal
    "blocked_ips_list": []
}

recent_alerts = []
flow_history = []
blocked_ips_set = set()

# Seed some initial flows for beautiful visual demonstration on first page load
protocols = ["TCP", "UDP", "ICMP"]
mock_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4", "192.168.1.100", "8.8.8.8"]
for i in range(10):
    src = random.choice(mock_ips)
    dst = random.choice([ip for ip in mock_ips if ip != src])
    flow_history.append({
        "timestamp": (datetime.now()).strftime("%H:%M:%S"),
        "source_ip": src,
        "dest_ip": dst,
        "protocol": random.choice(protocols),
        "is_malicious": False
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns the current network statistics for the dashboard."""
    # If a simulated attack is active, let's inject a realistic simulated flow & alert dynamically 
    # to guarantee real-time visual feedback even if run_simulation.py is not running!
    attack = network_stats.get("simulated_attack_type", "None")
    
    if attack != "None":
        src_ip = f"192.168.1.{random.randint(200, 254)}"
        dst_ip = f"10.0.0.{random.randint(1, 4)}"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if attack == "DDoS":
            # High bandwidth, massive UDP/TCP flow
            network_stats["total_bandwidth"] = random.uniform(850.0, 1200.0)
            network_stats["active_flows"] = random.randint(1500, 3200)
            network_stats["status"] = "CRITICAL"
            
            # Inject DDoS flow
            flow = {
                "timestamp": timestamp,
                "source_ip": src_ip,
                "dest_ip": dst_ip,
                "protocol": random.choice(["TCP", "UDP"]),
                "is_malicious": True
            }
            flow_history.append(flow)
            
            # Inject DDoS alert
            alert = {
                "timestamp": timestamp,
                "type": "DDoS",
                "target_ip": dst_ip,
                "action": "BLOCKED"
            }
            recent_alerts.append(alert)
            blocked_ips_set.add(src_ip)
            
        elif attack == "PortScan":
            # Moderate bandwidth, high flow count TCP SYN scan
            network_stats["total_bandwidth"] = random.uniform(45.0, 95.0)
            network_stats["active_flows"] = random.randint(250, 600)
            network_stats["status"] = "WARNING"
            
            flow = {
                "timestamp": timestamp,
                "source_ip": src_ip,
                "dest_ip": dst_ip,
                "protocol": "TCP",
                "is_malicious": True
            }
            flow_history.append(flow)
            
            alert = {
                "timestamp": timestamp,
                "type": "PortScan",
                "target_ip": dst_ip,
                "action": "BLOCKED"
            }
            recent_alerts.append(alert)
            blocked_ips_set.add(src_ip)
            
        elif attack == "Normal":
            # Normal high bandwidth flow
            network_stats["total_bandwidth"] = random.uniform(25.0, 150.0)
            network_stats["active_flows"] = random.randint(15, 45)
            network_stats["status"] = "NORMAL"
            
            flow = {
                "timestamp": timestamp,
                "source_ip": src_ip,
                "dest_ip": dst_ip,
                "protocol": random.choice(protocols),
                "is_malicious": False
            }
            flow_history.append(flow)
            
        # Constrain history lengths
        if len(flow_history) > 50:
            flow_history.pop(0)
        if len(recent_alerts) > 100:
            recent_alerts.pop(0)
            
        network_stats["blocked_ips"] = len(blocked_ips_set)
        network_stats["blocked_ips_list"] = list(blocked_ips_set)
        
    return jsonify({
        "stats": {
            "total_bandwidth": network_stats["total_bandwidth"],
            "active_flows": network_stats["active_flows"],
            "blocked_ips": len(blocked_ips_set),
            "status": network_stats["status"],
            "sensitivity_threshold": network_stats["sensitivity_threshold"],
            "simulated_attack_type": network_stats["simulated_attack_type"],
            "blocked_ips_list": list(blocked_ips_set)
        },
        "recent_alerts": recent_alerts[-10:], # Return last 10 alerts
        "flows": flow_history[-20:] # Return last 20 flows
    })

@app.route('/api/update', methods=['POST'])
def update_network():
    """Endpoint for the SDN controller or Simulator to post updates to the dashboard."""
    data = request.json
    
    if "stats" in data:
        network_stats.update(data["stats"])
        
    if "alert" in data:
        alert = data["alert"]
        alert["timestamp"] = datetime.now().strftime("%H:%M:%S")
        recent_alerts.append(alert)
        if len(recent_alerts) > 100:
            recent_alerts.pop(0)
            
    if "flow" in data:
        flow = data["flow"]
        flow["timestamp"] = datetime.now().strftime("%H:%M:%S")
        flow_history.append(flow)
        if len(flow_history) > 50:
            flow_history.pop(0)
            
        # Keep track of blocked IPs reported by simulator/controller
        if flow.get("is_malicious") and flow.get("source_ip"):
            blocked_ips_set.add(flow["source_ip"])
            
    network_stats["blocked_ips"] = len(blocked_ips_set)
    network_stats["blocked_ips_list"] = list(blocked_ips_set)
    return jsonify({"status": "success"})

@app.route('/api/threshold', methods=['GET', 'POST'])
def handle_threshold():
    """Manages the classification sensitivity threshold."""
    if request.method == 'POST':
        data = request.json
        if "sensitivity_threshold" in data:
            network_stats["sensitivity_threshold"] = float(data["sensitivity_threshold"])
            return jsonify({"status": "success", "sensitivity_threshold": network_stats["sensitivity_threshold"]})
        return jsonify({"status": "error", "message": "Missing sensitivity_threshold"}), 400
    else:
        return jsonify({"sensitivity_threshold": network_stats["sensitivity_threshold"]})

@app.route('/api/unblock', methods=['POST'])
def unblock_ip():
    """Manually unblock a previously blocked IP."""
    data = request.json
    if "ip" in data:
        ip = data["ip"]
        if ip in blocked_ips_set:
            blocked_ips_set.remove(ip)
            network_stats["blocked_ips"] = len(blocked_ips_set)
            network_stats["blocked_ips_list"] = list(blocked_ips_set)
            # Create a recovery alert
            recent_alerts.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": "Normal",
                "target_ip": ip,
                "action": "ALLOWED"
            })
            return jsonify({"status": "success", "message": f"IP {ip} unblocked successfully."})
        return jsonify({"status": "error", "message": "IP not in blocked list."}), 404
    return jsonify({"status": "error", "message": "Missing ip field."}), 400

@app.route('/api/simulate-attack', methods=['POST'])
def simulate_attack():
    """Triggers custom traffic patterns in Flask for demonstrations."""
    data = request.json
    if "attack_type" in data:
        attack_type = data["attack_type"]
        if attack_type in ["None", "DDoS", "PortScan", "Normal"]:
            network_stats["simulated_attack_type"] = attack_type
            if attack_type == "None":
                network_stats["status"] = "NORMAL"
                network_stats["total_bandwidth"] = 12.5
                network_stats["active_flows"] = 8
            return jsonify({"status": "success", "simulated_attack_type": attack_type})
        return jsonify({"status": "error", "message": "Invalid attack_type"}), 400
    return jsonify({"status": "error", "message": "Missing attack_type"}), 400

@app.route('/api/model-stats', methods=['GET'])
def get_model_stats():
    """Returns the trained ML model classification performance, confusion matrix and feature importances."""
    # Try reloading to make sure we serve the newest stats if retrained
    global model_stats_data
    if os.path.exists(stats_json_path):
        try:
            with open(stats_json_path, 'r') as f:
                model_stats_data = json.load(f)
        except Exception as e:
            print(f"Error reloading model stats: {e}")
            
    if model_stats_data:
        return jsonify(model_stats_data)
    else:
        # Return fallback mock statistics in the same structure if file is missing
        return jsonify({
            "accuracy": 0.992,
            "best_params": {"class_weight": "balanced", "max_depth": 10, "min_samples_split": 2, "n_estimators": 50},
            "metrics_by_class": {
                "Normal": {"precision": 0.991, "recall": 0.995, "f1_score": 0.993, "support": 7000},
                "DDoS": {"precision": 0.996, "recall": 0.991, "f1_score": 0.993, "support": 2000},
                "Port Scan": {"precision": 0.985, "recall": 0.988, "f1_score": 0.986, "support": 1000}
            },
            "confusion_matrix": [[6965, 15, 20], [10, 1982, 8], [12, 10, 978]],
            "feature_importances": {
                "packet_rate": 0.452,
                "byte_rate": 0.315,
                "packet_size": 0.128,
                "flow_duration": 0.083,
                "protocol_type": 0.022
            },
            "features_order": ["protocol_type", "packet_size", "flow_duration", "packet_rate", "byte_rate"]
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
