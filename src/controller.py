import threading
from .models import CredentialManager, TunnelManager, NetworkRunner, ReportGenerator
import pandas as pd
import os

VENDOR_MAP = {
    "Cisco IOS": "cisco_ios", "Cisco XR": "cisco_xr", "Cisco NX-OS": "cisco_nxos",
    "Juniper Junos": "juniper_junos", "Nokia SR OS": "nokia_sros", "Huawei VRP": "huawei"
}

class AppController:
    def __init__(self, view_log_callback):
        self.log = view_log_callback
        self.cred_mgr = CredentialManager()

    def load_creds(self):
        return {
            'main': self.cred_mgr.load_credentials('main'),
            'jump': self.cred_mgr.load_credentials('jump')
        }

    def save_creds(self, section, u, p):
        self.cred_mgr.save_credentials(section, u, p)

    def run_task(self, params):
        threading.Thread(target=self._execute, args=(params,), daemon=True).start()

    def _execute(self, p):
        self.log(f"--- STARTING {p['mode'].upper()} ---")
        tunnel = None
        
        # 1. Jump Host
        if p['use_jump']:
            self.log(f"Connecting to Jump Host {p['jh_ip']}...")
            tunnel = TunnelManager(p['jh_ip'], p['jh_port'], p['jh_user'], p['jh_pass'])
            ok, msg = tunnel.connect()
            if not ok:
                self.log(f"Jump Error: {msg}")
                return
            self.log("Jump Host Connected.")

        # 2. Process Devices
        try:
            df = pd.read_excel(p['excel'])
            df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
            
            for _, row in df.iterrows():
                row_data = row.to_dict()
                host = row_data.get('ip') or row_data.get('host')
                if not host: continue
                
                # Tunnel Setup
                c_host, c_port = host, int(row_data.get('port', 22))
                if tunnel:
                    try:
                        self.log(f"Tunneling to {host}...")
                        c_port = tunnel.start_forwarding(host, c_port)
                        c_host = "127.0.0.1"
                    except Exception as e:
                        self.log(f"Tunnel Error {host}: {e}"); continue
                
                # Execution
                self.log(f"Processing {host}...")
                dtype = row_data.get('device_type', VENDOR_MAP.get(p['vendor'], 'cisco_ios'))
                
                # SSH / NETCONF Logic
                if p['protocol'] == "SSH":
                    dev = {'device_type': dtype, 'host': c_host, 'username': p['user'], 'password': p['pass'], 'port': c_port}
                    if p['mode'] == 'retrieve':
                        ok, res = NetworkRunner.retrieve_ssh(dev, p['cmd'], p['format'])
                        if ok:
                            ext = "json" if p['format']=="JSON" else "xml" if p['format']=="XML" else "txt"
                            if not os.path.exists("results"): os.makedirs("results")
                            with open(f"results/{host}.{ext}", "w") as f: f.write(res)
                            self.log(f"  > SAVED: {host}.{ext}")
                        else: self.log(f"  > FAIL: {res}")
                    else:
                        cfg = NetworkRunner.render_config(p['template'], row_data)
                        ok, res = NetworkRunner.push_ssh(dev, cfg)
                        self.log(f"  > {'SUCCESS' if ok else 'FAIL'}: {res}")
                
                elif p['protocol'] == "NETCONF":
                    # (Similar Netconf Logic)
                    dev = {'host': c_host, 'username': p['user'], 'password': p['pass'], 'port': c_port}
                    cfg = NetworkRunner.render_config(p['template'], row_data)
                    ok, res = NetworkRunner.push_netconf(dev, cfg)
                    self.log(f"  > NETCONF: {res}")

            # 3. Report
            if p['mode'] == 'retrieve' and p['auto_convert']:
                self.log("Generating Report...")
                ok, msg = ReportGenerator.generate_excel_report(p['format'], p['regex_file'])
                self.log(f"REPORT: {msg}")

        except Exception as e: self.log(f"CRITICAL: {e}")
        finally:
            if tunnel: tunnel.close()
            self.log("--- DONE ---")