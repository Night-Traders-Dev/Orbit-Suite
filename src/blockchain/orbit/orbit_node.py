import time, datetime
import requests
import threading
import json
import os
import random
from flask import Flask, request, jsonify
from config.configutil import TXConfig, NodeConfig, OrbitDB
from core.ioutil import load_nodes, save_nodes, fetch_chain, save_chain
from blockchain.blockutil import validate_block
from blockchain.orbitutil import get_node_for_user

FETCH_INTERVAL = 30
NODE_LEDGER = "data/orbit_chain.node"
EXPLORER = "https://45b2-173-187-247-149.ngrok-free.app"
#"http://127.0.0.1:7000"

orbit_db = OrbitDB()

app = Flask(__name__)

class OrbitNode:
    def __init__(self, address):
        self.address = address
        self.port = 5000 + random.randint(0, 999)
        self.node_id = "Node" + str(random.randint(0, 999))
        self.running = True
        self.nodes = load_nodes()
        self.register_node()
        self.NodeRegistry = {}
        self.heartbeat_interval = 20  # seconds
        self.heartbeat_thread = None

    def format_node(self, node_id, ip, port, last_seen):
        self.NodeRegistry = {
            "node": {
                "id": node_id,
                "address": ip,
                "port": port,
                "quorum_slice": [],
                "trust_score": 1.0,
                "uptime_score": 1.0,
                "last_seen": time.time()
            }
        }
        return self.NodeRegistry

    def register_node(self):
        new_node = self.format_node(self.node_id, self.address, self.port, time.time())
        save_nodes(new_node)
        return new_node

    def fetch_latest_chain(self):
        try:
            return fetch_chain()
        except Exception as e:
            print(f"Error fetching chain: {e}")
            return []

    def update_chain(self):
        new_chain = self.fetch_latest_chain()
        if new_chain and len(new_chain) > len(new_chain):
            print(f"New chain received. Updating local ledger ({len(new_chain)} blocks).")
            self.chain = new_chain
            save_chain(self.chain, owner_id=self.node_id, chain_file=NODE_LEDGER)

    def validate_incoming_block(self, block):
        if validate_block(block, self.chain):
            self.chain.append(block)
            save_chain(self.chain, owner_id=self.node_id, chain_file=NODE_LEDGER)
            print(f"Accepted new block: {block['index']}")
            return True
        else:
            print("Invalid block received.")
            return False

    def broadcast_block_to_peers(self, block):
        for node_id, node_data in self.nodes.items():
            if node_id == self.node_id:
                continue
            url = node_data.get("url")
            try:
                res = requests.post(f"{url}/receive_block", json=block, timeout=3)
                if res.status_code == 200:
                    print(f"Block sent to {node_id}")
            except Exception as e:
                print(f"Failed to send block to {node_id}: {e}")

    def start_receiver_server(self, new_node_port):
        app = Flask(__name__)
        @app.route("/receive_block", methods=["POST"])
        def receive_block():
            block = request.get_json()
            if self.validate_incoming_block(block):
                return jsonify({"status": "accepted"}), 200
            return jsonify({"status": "rejected"}), 400

        threading.Thread(
            target=app.run,
            kwargs={"port": new_node_port, "debug": False, "use_reloader": False}
        ).start()

    def heartbeat_loop(self, new_node, new_node_id):
        while self.running:
            try:
                response = requests.post(
                    f"{EXPLORER}/node_ping",
                    json=new_node,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"[HEARTBEAT] Node {new_node_id} heartbeat sent.")
                else:
                    print(f"[HEARTBEAT] Failed (status {response.status_code})")
            except Exception as e:
                print(f"[HEARTBEAT] Exception: {e}")
            time.sleep(self.heartbeat_interval)

    def start_heartbeat_thread(self, new_node, new_node_id):
        self.heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            args=(new_node, new_node_id),
            daemon=True
        )
        self.heartbeat_thread.start()

    def run(self):
        print(f"Starting Orbit Node for {self.address} ({self.node_id})")
        new_node = self.register_node()
        new_node_id = new_node["node"]["id"]
        new_node_port = new_node["node"]["port"]
        self.start_receiver_server(new_node_port)
        self.start_heartbeat_thread(new_node, new_node_id)

        while self.running:
            self.update_chain()
            time.sleep(FETCH_INTERVAL)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start a standalone Orbit Blockchain Node")
    parser.add_argument("--address", required=True, help="User address to associate with this node")
    args = parser.parse_args()

    node = OrbitNode(args.address)
    try:
        node.run()
    except KeyboardInterrupt:
        print("Stopping node...")
        node.stop()
