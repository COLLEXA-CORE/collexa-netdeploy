import pandas as pd
from jinja2 import Template
from netmiko import ConnectHandler
from ncclient import manager
from cryptography.fernet import Fernet
import os
import json
import socket
import select
import threading
import paramiko
import glob
import re
import xml.etree.ElementTree as ET
import xml.dom.minidom

#
class CredentialManager:
    def __init__(self, key_file='secret.key', cred_file='creds.dat'):
        self.key_file = key_file
        self.cred_file = cred_file
        self._init_key()

    def _init_key(self):
        if not os.path.exists(self.key_file):
            with open(self.key_file, 'wb') as kf: kf.write(Fernet.generate_key())
        with open(self.key_file, 'rb') as kf: self.cipher = Fernet(kf.read())

    def save_credentials(self, section, username, password):
        try:
            existing = {}
            if os.path.exists(self.cred_file):
                try:
                    with open(self.cred_file, 'rb') as f:
                        existing = json.loads(self.cipher.decrypt(f.read()).decode())
                except: pass
            
            if "username" in existing: existing = {"main": existing}
            existing[section] = {"username": username, "password": password}

            with open(self.cred_file, 'wb') as f:
                f.write(self.cipher.encrypt(json.dumps(existing).encode()))
        except Exception as e: print(f"Save Error: {e}")

    def load_credentials(self, section):
        if not os.path.exists(self.cred_file): return None, None
        try:
            with open(self.cred_file, 'rb') as f:
                data = json.loads(self.cipher.decrypt(f.read()).decode())
            if "username" in data: data = {"main": data}
            return data.get(section, {}).get('username'), data.get(section, {}).get('password')
        except: return None, None

class TunnelManager:
    def __init__(self, host, port, user, password):
        self.host, self.port, self.user, self.password = host, int(port), user, password
        self.client = None
        self._local_binds = []

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.host, self.port, self.user, self.password, timeout=10)
            self.transport = self.client.get_transport()
            return True, "Jump Host Connected"
        except Exception as e: return False, str(e)

    def start_forwarding(self, target_host, target_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        local_port = sock.getsockname()[1]
        sock.listen(1)
        threading.Thread(target=self._forwarder, args=(sock, target_host, target_port), daemon=True).start()
        self._local_binds.append(sock)
        return local_port

    def _forwarder(self, local_sock, target_host, target_port):
        try:
            client, _ = local_sock.accept()
            remote = self.transport.open_channel("direct-tcpip", (target_host, target_port), client.getpeername())
            if remote is None: client.close(); return
            while True:
                r, _, _ = select.select([client, remote], [], [], 1.0)
                if client in r:
                    d = client.recv(1024); 
                    if not d: break
                    remote.send(d)
                if remote in r:
                    d = remote.recv(1024); 
                    if not d: break
                    client.send(d)
            client.close(); remote.close()
        except: pass

    def close(self):
        for s in self._local_binds: s.close()
        if self.client: self.client.close()

class NetworkRunner:
    @staticmethod
    def render_config(template_path, context):
        with open(template_path, 'r') as f: return Template(f.read()).render(**context)

    @staticmethod
    def push_ssh(device_info, commands):
        try:
            device_info.setdefault('global_delay_factor', 4)
            net_connect = ConnectHandler(**device_info)
            if isinstance(commands, str): commands = commands.splitlines()
            output = net_connect.send_config_set(commands, read_timeout=90)
            net_connect.disconnect()
            return True, output
        except Exception as e: return False, str(e)

    @staticmethod
    def push_netconf(device_info, xml_config):
        try:
            with manager.connect(**device_info, hostkey_verify=False, device_params={'name':'default'}) as m:
                return True, str(m.edit_config(target='running', config=xml_config))
        except Exception as e: return False, str(e)

    @staticmethod
    def retrieve_ssh(device_info, command, format_type):
        try:
            device_info.setdefault('global_delay_factor', 4)
            net_connect = ConnectHandler(**device_info)
            raw_output = net_connect.send_command(command, read_timeout=90)
            net_connect.disconnect()
            
            final_output = raw_output
            if format_type == "JSON":
                try: final_output = json.dumps(json.loads(raw_output), indent=4)
                except: final_output = json.dumps({"raw_output": raw_output}, indent=4)
            elif format_type == "XML":
                try: final_output = xml.dom.minidom.parseString(raw_output).toprettyxml()
                except: final_output = f"<output>\n{raw_output}\n</output>"
            return True, final_output
        except Exception as e: return False, str(e)

class ReportGenerator:
    @staticmethod
    def generate_excel_report(format_type, regex_excel_path=None):
        try:
            if not os.path.exists("results"): return False, "No results folder found."
            data_rows = []
            
            if format_type == "JSON":
                files = glob.glob("results/*.json")
                for f in files:
                    try:
                        with open(f, 'r') as jf:
                            d = json.load(jf)
                            if isinstance(d, dict): 
                                d['Device_IP'] = os.path.basename(f).replace('.json','')
                                data_rows.append(d)
                    except: pass
            elif format_type == "XML":
                files = glob.glob("results/*.xml")
                for f in files:
                    try:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        row = {'Device_IP': os.path.basename(f).replace('.xml','')}
                        for child in root:
                            if len(child) == 0: row[child.tag] = child.text
                        data_rows.append(row)
                    except: pass
            elif format_type == "Text":
                if not regex_excel_path: return False, "Regex file missing."
                regex_df = pd.read_excel(regex_excel_path)
                patterns = dict(zip(regex_df['Column'], regex_df['Regex']))
                files = glob.glob("results/*.txt")
                for f in files:
                    with open(f, 'r') as tf:
                        content = tf.read()
                        row = {'Device_IP': os.path.basename(f).replace('.txt','')}
                        for col, pat in patterns.items():
                            match = re.search(pat, content, re.MULTILINE)
                            row[col] = match.group(1) if match and match.groups() else (match.group(0) if match else "N/A")
                        data_rows.append(row)

            if not data_rows: return False, "No data extracted."
            df = pd.json_normalize(data_rows)
            out = f"Final_Report_{format_type}.xlsx"
            df.to_excel(out, index=False)
            return True, out
        except Exception as e: return False, str(e)