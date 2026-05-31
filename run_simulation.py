import time
import json
import random
import requests
import joblib
import pandas as pd
import os
import threading

# Configuration
DASHBOARD_API = 'http://127.0.0.1:5000/api/update'
DASHBOARD_STATS_API = 'http://127.0.0.1:5000/api/stats'
SIMULATION_DELAY_MIN = 0.2
SIMULATION_DELAY_MAX = 0.8

# Mock IP addresses
INTERNAL_NET = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5']
EXTERNAL_NET = [f"{random.randint(11, 250)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}" for _ in range(20)]

class NetworkSimulator:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, 'ml_model', 'synthetic_network_traffic.csv')
        model_path = os.path.join(current_dir, 'ml_model', 'rf_model.pkl')
        scaler_path = os.path.join(current_dir, 'ml_model', 'scaler.pkl')
        
        print("Loading dataset and ML models...")
        try:
            self.df = pd.read_csv(data_path)
            self.X = self.df.drop('label', axis=1)
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            print("Loaded successfully!")
        except Exception as e:
            print(f"Failed to load required files: {e}")
            print("Please run the scripts in /ml_model/ first.")
            exit(1)
            
        self.blocked_ips = set()
        self.sensitivity_threshold = 0.5
        self.simulated_attack_type = "None"
        self.running = False
        
    def sync_with_dashboard(self):
        """Periodically syncs blocked IPs and sensitivity threshold from the dashboard."""
        try:
            response = requests.get(DASHBOARD_STATS_API, timeout=0.5)
            if response.status_code == 200:
                data = response.json()
                stats = data.get("stats", {})
                
                # Sync dynamic sensitivity threshold
                self.sensitivity_threshold = float(stats.get("sensitivity_threshold", 0.5))
                
                # Sync dynamic active simulated attack type
                self.simulated_attack_type = stats.get("simulated_attack_type", "None")
                
                # Sync blocked list (allows manual unblocking to propagate immediately)
                blocked_list = stats.get("blocked_ips_list", [])
                self.blocked_ips = set(blocked_list)
        except Exception as e:
            # Silence connection warnings if flask isn't running yet
            pass

    def generate_flow(self):
        # Sync stats and threshold state
        self.sync_with_dashboard()
        
        # Determine target label based on active simulated attack on dashboard
        if self.simulated_attack_type == "DDoS":
            target_labels = [1]
        elif self.simulated_attack_type == "PortScan":
            target_labels = [2]
        elif self.simulated_attack_type == "Normal":
            target_labels = [0]
        else:
            target_labels = [0, 1, 2] # standard mix
            
        # Select appropriate traffic row from dataset
        matching_rows = self.df[self.df['label'].isin(target_labels)]
        if len(matching_rows) == 0:
            matching_rows = self.df
            
        idx = random.choice(matching_rows.index)
        features = self.X.iloc[[idx]]
        true_label = self.df.iloc[idx]['label']
        
        # Predict using dynamic probability-based sensitivity threshold
        scaled_features = self.scaler.transform(features)
        
        # Perform soft probability predictions
        probs = self.model.predict_proba(scaled_features)[0] # [p_normal, p_ddos, p_portscan]
        p_normal = probs[0]
        p_malicious = 1.0 - p_normal
        
        # If sensitivity is high (e.g. 0.9), a low malicious probability (e.g. 0.1) triggers an alert
        # Alert if p_malicious > (1.0 - sensitivity_threshold)
        trigger_boundary = 1.0 - self.sensitivity_threshold
        
        is_anom = p_malicious >= trigger_boundary
        
        if is_anom:
            # Predict specific malicious class based on higher probability
            prediction = 1 if probs[1] >= probs[2] else 2
        else:
            prediction = 0
            
        protocol_enc = int(features['protocol_type'].values[0])
        pkt_size = int(features['packet_size'].values[0])
        
        # Pick IP addresses
        if true_label == 0:
            src_ip = random.choice(EXTERNAL_NET + INTERNAL_NET)
            dst_ip = random.choice(INTERNAL_NET)
        else:
            src_ip = random.choice(EXTERNAL_NET)
            dst_ip = random.choice(INTERNAL_NET)
            
        # Ensure we don't repeat mock flows from blocked IPs
        if src_ip in self.blocked_ips:
            return None
            
        return {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'proto_enc': protocol_enc,
            'pkt_size': pkt_size,
            'is_anom': is_anom,
            'prediction': prediction
        }

    def start(self):
        self.running = True
        print(f"Starting network simulator. Transmitting telemetry to {DASHBOARD_API}...")
        print("Dynamic sensitivity and manual IP unblocking synchronization active.")
        
        bandwidth_sum = 0
        flows_count = 0
        
        while self.running:
            flow_info = self.generate_flow()
            
            if flow_info:
                payload = {}
                protocol_str = "TCP" if flow_info['proto_enc'] == 0 else ("UDP" if flow_info['proto_enc'] == 1 else "ICMP")
                
                payload['flow'] = {
                    "source_ip": flow_info['src_ip'],
                    "dest_ip": flow_info['dst_ip'],
                    "protocol": protocol_str,
                    "is_malicious": bool(flow_info['is_anom'])
                }
                
                if flow_info['is_anom']:
                    attack_type = "Normal"
                    if flow_info['prediction'] == 1: attack_type = "DDoS"
                    elif flow_info['prediction'] == 2: attack_type = "PortScan"
                    
                    self.blocked_ips.add(flow_info['src_ip'])
                    print(f"[THREAT IDENTIFIED] Model flagged {attack_type} from {flow_info['src_ip']}. Flow blocked.")
                    
                    payload['alert'] = {
                        "type": attack_type,
                        "target_ip": flow_info['dst_ip'],
                        "action": "BLOCKED"
                    }
                
                # Aggregate stats
                bandwidth_sum += (flow_info['pkt_size'] * 8 / 1000000.0)
                flows_count += 1
                
                payload['stats'] = {
                    "total_bandwidth": bandwidth_sum * (10 / max(1, flows_count)), 
                    "active_flows": max(5, random.randint(flows_count, flows_count + 15)),
                    "blocked_ips": len(self.blocked_ips)
                }
                
                try:
                    requests.post(DASHBOARD_API, json=payload, timeout=0.2)
                except requests.exceptions.RequestException:
                    pass
            
            time.sleep(random.uniform(SIMULATION_DELAY_MIN, SIMULATION_DELAY_MAX))

if __name__ == "__main__":
    sim = NetworkSimulator()
    try:
        sim.start()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
