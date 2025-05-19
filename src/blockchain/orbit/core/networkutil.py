# networkutil.py
import requests
import json

def ping_node(address):
    try:
        response = requests.get(f"http://{address}/ping", timeout=3)
        return response.status_code == 200
    except:
        return False

def send_block_to_node(address, block_data):
    try:
        res = requests.post(f"http://{address}/receive_block", json=block_data, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"Failed to send block to {address}: {e}")
        return False
