import time
import requests
import joblib
import pandas as pd
import os
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, icmp

class MLIntrusionDetectionController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MLIntrusionDetectionController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        
        # Load ML Model and Scaler
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, '..', 'ml_model', 'rf_model.pkl')
        scaler_path = os.path.join(current_dir, '..', 'ml_model', 'scaler.pkl')
        
        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.logger.info("Successfully loaded ML Model.")
        except Exception as e:
            self.logger.error(f"Failed to load ML Model: {e}")
            self.model = None

        self.DASHBOARD_API = 'http://127.0.0.1:5000/api/update'
        
        # Traffic tracking
        self.flow_stats = {}
        self.blocked_ips = set()
        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Table-miss flow entry (send everything to controller)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    def block_ip(self, datapath, ip):
        """Install a drop rule for a malicious IP"""
        if ip in self.blocked_ips:
            return
            
        self.blocked_ips.add(ip)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=ip)
        # Empty actions == DROP
        actions = []
        self.add_flow(datapath, 100, match, actions)
        self.logger.warning(f"BLOCKED IP: {ip}")

    def unblock_ip(self, datapath, ip):
        """Remove the drop rule for a previously blocked IP"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=ip)
        # Use OFPFC_DELETE to remove matching flows
        mod = parser.OFPFlowMod(
            datapath=datapath, 
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY, 
            out_group=ofproto.OFPG_ANY,
            match=match
        )
        datapath.send_msg(mod)
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
        self.logger.info(f"UNBLOCKED IP: {ip}")

    def update_dashboard(self, packet_info, is_anom, pred_class):
        """Send asynchronous update to Flask dashboard"""
        payload = {}
        
        protocol_str = "TCP" if packet_info['proto'] == 0 else ("UDP" if packet_info['proto'] == 1 else "ICMP")
        
        payload['flow'] = {
            "source_ip": packet_info['src_ip'],
            "dest_ip": packet_info['dst_ip'],
            "protocol": protocol_str,
            "is_malicious": is_anom
        }
        
        if is_anom:
            attack_type = "Normal"
            if pred_class == 1: attack_type = "DDoS"
            elif pred_class == 2: attack_type = "PortScan"
            
            payload['alert'] = {
                "type": attack_type,
                "target_ip": packet_info['dst_ip'],
                "action": "BLOCKED"
            }
            
        payload['stats'] = {
            "total_bandwidth": packet_info['pkt_size'] * 8 / 1000000.0, # Approximate Mbps context
            "active_flows": max(10, len(self.mac_to_port)*2), 
            "blocked_ips": len(self.blocked_ips)
        }
        
        try:
            requests.post(self.DASHBOARD_API, json=payload, timeout=0.1)
        except:
            pass # Ignore dashboard connection errors

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated")
            
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        if eth.ethertype == 0x0800: # IPv4
            ip_pkt = pkt.get_protocols(ipv4.ipv4)[0]
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            
            # Dynamic rate-limited sync from dashboard (every 3 seconds)
            now_time = time.time()
            if not hasattr(self, 'last_sync_time') or now_time - self.last_sync_time > 3.0:
                self.last_sync_time = now_time
                try:
                    # Fetch stats from flask
                    response = requests.get('http://127.0.0.1:5000/api/stats', timeout=0.1)
                    if response.status_code == 200:
                        data = response.json()
                        flask_blocked = set(data.get("stats", {}).get("blocked_ips_list", []))
                        self.sensitivity_threshold = float(data.get("stats", {}).get("sensitivity_threshold", 0.5))
                        
                        # Unblock IPs that were removed from dashboard
                        ips_to_unblock = self.blocked_ips - flask_blocked
                        for ip in ips_to_unblock:
                            self.unblock_ip(datapath, ip)
                            
                        # Update local block list
                        self.blocked_ips = flask_blocked
                except Exception as e:
                    pass

            # Skip processing if IP is blocked
            if src_ip in self.blocked_ips:
                return

            proto_enc = 0 # Default TCP
            if pkt.get_protocols(udp.udp): proto_enc = 1
            elif pkt.get_protocols(icmp.icmp): proto_enc = 2
            
            pkt_size = len(msg.data)
            
            # Extract basic features for the ML model
            mock_rate = 50 
            mock_byte_rate = pkt_size * mock_rate
            mock_duration = 10.0
            
            features = pd.DataFrame([[proto_enc, pkt_size, mock_duration, mock_rate, mock_byte_rate]], 
                                   columns=['protocol_type', 'packet_size', 'flow_duration', 'packet_rate', 'byte_rate'])
            
            if self.model and self.scaler:
                scaled_features = self.scaler.transform(features)
                
                # Dynamic sensitivity logic in Ryu using predict_proba
                try:
                    probs = self.model.predict_proba(scaled_features)[0] # [p_normal, p_ddos, p_portscan]
                    p_normal = probs[0]
                    p_malicious = 1.0 - p_normal
                    
                    sensitivity = getattr(self, 'sensitivity_threshold', 0.5)
                    trigger_boundary = 1.0 - sensitivity
                    
                    is_anom = p_malicious >= trigger_boundary
                    
                    if is_anom:
                        prediction = 1 if probs[1] >= probs[2] else 2
                    else:
                        prediction = 0
                except Exception as e:
                    # Fall back to standard predict if predict_proba is not available or errors
                    prediction = self.model.predict(scaled_features)[0]
                    is_anom = prediction > 0
                
                packet_info = {
                    'src_ip': src_ip, 'dst_ip': dst_ip, 'proto': proto_enc, 'pkt_size': pkt_size
                }
                self.update_dashboard(packet_info, is_anom, prediction)
                
                if is_anom:
                    self.block_ip(datapath, src_ip)
                    return # Do not process this packet further
        
        # Standard Switch Forwarding Logic
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
