import pandas as pd
import numpy as np
import os

def generate_synthetic_data(num_samples=20000):
    """
    Generates high-quality synthetic network traffic data for training the IDS model.
    Features:
    - protocol_type: 0 (TCP), 1 (UDP), 2 (ICMP)
    - packet_size: bytes
    - flow_duration: milliseconds
    - packet_rate: packets per second
    - byte_rate: bytes per second
    
    Labels:
    - 0: Normal
    - 1: DDoS
    - 2: Port Scan
    """
    np.random.seed(42)
    
    data = []
    
    for i in range(num_samples):
        # We define a mixture of traffic types with class skew similar to real-world scenarios
        # 65% Normal, 20% DDoS, 15% Port Scan
        attack_type = np.random.choice([0, 1, 2], p=[0.65, 0.20, 0.15])
        
        if attack_type == 0:
            # --- Normal Traffic ---
            # Normal flows have realistic features: highly variable durations and sizes
            # High proportion of TCP (0), some UDP (1) and very few ICMP (2)
            protocol = np.random.choice([0, 1, 2], p=[0.75, 0.20, 0.05])
            
            # Log-normal distribution for packet sizes (very typical in real traffic)
            pkt_size = int(np.random.lognormal(mean=5.8, sigma=0.6))
            pkt_size = np.clip(pkt_size, 46, 1500) # Standard Ethernet MTU constraints
            
            duration = np.random.exponential(scale=1200) + 10.0 # mostly short but some very long flows
            pkt_rate = np.random.lognormal(mean=2.5, sigma=1.0) + 1.0 # typical lower rate
            byte_rate = pkt_rate * pkt_size
            label = 0
            
        elif attack_type == 1:
            # --- DDoS Traffic ---
            # DDoS (SYN/UDP Floods) is characterized by ultra-high packet rate, very short flow duration,
            # and extremely uniform packet sizes.
            protocol = np.random.choice([0, 1, 2], p=[0.45, 0.50, 0.05]) # high UDP & TCP
            
            # Very uniform packet sizes
            pkt_size = int(np.random.normal(700, 40)) 
            pkt_size = np.clip(pkt_size, 64, 1400)
            
            duration = np.random.uniform(1, 120) # extremely short burst durations
            # Massive packet rates (Poisson-like massive scale)
            pkt_rate = np.random.uniform(1500, 8000) 
            byte_rate = pkt_rate * pkt_size
            label = 1
            
        elif attack_type == 2:
            # --- Port Scan Traffic ---
            # Port scans are characterized by rapid TCP connection attempts to many ports.
            # Almost entirely TCP (0), small packet sizes (SYN packets are ~60 bytes), 
            # ultra-short flow durations, and moderate rates.
            protocol = 0 
            
            pkt_size = int(np.random.normal(60, 4)) # standard SYN packets
            pkt_size = np.clip(pkt_size, 40, 80)
            
            duration = np.random.uniform(0.5, 45) # very short response times
            pkt_rate = np.random.uniform(120, 800) # moderate speed scanning
            byte_rate = pkt_rate * pkt_size
            label = 2
            
        data.append([protocol, pkt_size, duration, pkt_rate, byte_rate, label])
        
    df = pd.DataFrame(data, columns=['protocol_type', 'packet_size', 'flow_duration', 'packet_rate', 'byte_rate', 'label'])
    
    # Save to CSV
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'synthetic_network_traffic.csv')
    df.to_csv(file_path, index=False)
    print(f"Generated {num_samples} high-quality samples and saved to {file_path}")
    
    return df

if __name__ == "__main__":
    generate_synthetic_data(20000)
